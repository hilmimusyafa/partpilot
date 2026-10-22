"""Dashboard read model and explicitly versioned synthetic recovery assumptions."""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict
from backend.wo.models import Session
from backend.wo.repository import get_session,get_db_connection
from backend.procurement import repository as repo
from backend.procurement.service import get_run
from backend.procurement.comparison import sources,create_comparison,read_comparison
from backend.procurement.models import CompareInput,EmptyInput
from .bootstrap import CONTEXT

router = APIRouter(prefix='/api/v1/demo')
KEY=Header(...,alias='Idempotency-Key',min_length=1,max_length=128,pattern=r'^[!-~]+$')
ASSUMPTIONS={'summary':'Simulasi lini AC: normal 100 unit/jam, terganggu 40 unit/jam. Margin kontribusi Rp500.000/unit (harga Rp3.500.000 dikurangi biaya variabel yang dapat dihindari Rp3.000.000); 25% output hilang dapat dikejar. Instalasi 1 jam + restart 1 jam; biaya pemulihan tambahan Rp250.000. Horizon 24 jam dengan shift kontinu. Gudang donor diasumsikan tidak kehilangan produksi dari stok yang tersedia di luar reservasi. Pajak penawaran demo Rp0; bukan tarif pajak aktual.', 'source':'synthetic-AC-assembly-v1','normal_units_per_hour':100,'disrupted_units_per_hour':40,
             'selling_price_idr':3500000,'avoidable_variable_cost_idr':3000000,'recoverable_fraction':'0.25',
             'installation_hours':1,'restart_hours':1,'recovery_cost_idr':250000,'horizon_hours':24,
             'calendar':'24h continuous demo shift','donor':'surplus beyond reserved stock; no additional donor loss assumed'}

def generation():
    return repo.query('SELECT generation FROM pp.demo_control WHERE singleton')[0]['generation']

@router.get('/config')
def config():
    return {'generation':generation(),'context':CONTEXT,'assumptions':ASSUMPTIONS,
      'warehouses':[{'id':f'SYN-WH-0{i}','name':f'Gudang {i}'+(' — aturan belum tersedia' if i>2 else '')} for i in range(1,6)],
      'scenarios':[
       {'id':'origin_stock','label':'1 · Stok sendiri','description':'Bearing conveyor merek NTN, lubang 10 mm, diameter luar 30 mm, lebar 9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'1','warehouse_id':'SYN-WH-01'},
       {'id':'transfer_alias','label':'2 · Nama berbeda di gudang 2','description':'Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'6','warehouse_id':'SYN-WH-01'},
       {'id':'vendor_purchase','label':'3 · Perbandingan vendor','description':'Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'12','warehouse_id':'SYN-WH-01'},
       {'id':'clarification','label':'4 · Identitas belum lengkap','description':'Bearing conveyor bunyi, perlu diganti','quantity':'1','warehouse_id':'SYN-WH-01'}]}

@router.get('/orders')
def orders():
    rows=repo.query("SELECT s.id,r.id run_id,c.id comparison_id,d.option_id decision FROM pp.wo_identification_session s LEFT JOIN pp.demo_run r ON r.session_id=s.id LEFT JOIN LATERAL (SELECT id FROM pp.demo_comparison WHERE run_id=r.id ORDER BY created_at DESC LIMIT 1)c ON true LEFT JOIN pp.demo_decision d ON d.run_id=r.id WHERE s.company='SYN-COMPANY-01' ORDER BY s.created_at DESC LIMIT 100")
    return {'generation':generation(),'items':[dict(Session(**get_session(r['id'])).model_dump(mode='json'),run_id=r['run_id'],comparison_id=r['comparison_id'],decision={'option_id':r['decision']} if r['decision'] else None) for r in rows]}

class ResetInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    confirmation:str
    expected_generation:int

@router.post('/reset')
def reset(body:ResetInput,idempotency_key:str=KEY):
    return repo.query('SELECT pp.demo_reset(%s,%s,%s) AS result',(body.expected_generation,idempotency_key,body.confirmation))[0]['result']

def default_comparison(run):
    start=datetime.now(timezone.utc)
    def datum(value,unit):return dict(value=str(value),unit=unit,source=ASSUMPTIONS['source'],assumption_version='v1')
    production=dict(output_unit='units',currency='IDR',currency_scale=2,
      normal_output_per_hour=datum(100,'units/h'),disrupted_output_per_hour=datum(40,'units/h'),
      recoverable_fraction=datum('0.25','fraction'),net_selling_price_per_unit=datum(3500000,'IDR/units'),
      avoidable_variable_cost_per_unit=datum(3000000,'IDR/units'))
    options=[]
    for source in sources(run):
        quote=source['quote']
        eta=max(start,datetime.fromisoformat(quote['delivered_eta'])) if quote else start+timedelta(hours=8)
        installed=eta+timedelta(hours=1);restored=installed+timedelta(hours=1)
        stages=[]
        for kind,begin,end in [('procurement',start,start),('dispatch',start,start),('transport',start,eta),('installation',eta,installed),('restart',installed,restored)]:
            stages.append(dict(id=kind,kind=kind,start=begin.isoformat(),end=end.isoformat(),depends_on=[stages[-1]['id']] if stages else [],source=ASSUMPTIONS['source'],assumption_version='v1'))
        schedule=dict(future_from=start.isoformat(),horizon_end=(start+timedelta(hours=24)).isoformat(),calendar_source=ASSUMPTIONS['calendar'],parallel_assumption_version='v1',stages=stages,scheduled_impacted_windows=[dict(start=start.isoformat(),end=(start+timedelta(hours=24)).isoformat())])
        options.append(dict(source_id=source['source_id'],schedule=schedule,costs_nonduplicated=True,
          donor_cost_status=dict(status='not_applicable',source=ASSUMPTIONS['donor'],assumption_version='v1'),
          incremental_disruption_costs=[dict(cost_id='recovery-labor',cost_type='recovery',amount=datum(250000,'IDR'),evidence_ref='demo-additional-labor-v1',description='Tenaga pemulihan tambahan simulasi; di luar biaya variabel yang dapat dihindari')]))
    return CompareInput.model_validate(dict(expected_version=run['version'],production=production,options=options))

@router.post('/sourcing-runs/{run_id}/prepare-comparison',status_code=201)
def prepare(run_id:str,body:EmptyInput,idempotency_key:str=KEY):
    # Freeze the generated schedule once per request key, including concurrent tabs.
    with get_db_connection() as lock:
        lock.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('demo-prepare:'+idempotency_key,))
        return prepare_locked(run_id,idempotency_key)

def prepare_locked(run_id,idempotency_key):
    old=repo.query('SELECT id,run_id FROM pp.demo_comparison WHERE request_key=%s',(idempotency_key,))
    if old:
        if old[0]['run_id']!=run_id:raise repo.ProcurementError('idempotency_conflict','Key already used')
        return read_comparison(old[0]['id'],initial=True)
    run=get_run(run_id)
    if run.get('transport')!='whatsapp' and any(v['outcome']=='pending' for v in run['vendors']):
        raise repo.ProcurementError('vendors_pending','Jalankan simulator sebelum membandingkan')
    return create_comparison(run_id,default_comparison(run),idempotency_key)
