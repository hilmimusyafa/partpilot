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
ASSUMPTIONS={'summary':'Demo inspeksi sebelum shift: produksi berikutnya mulai 12 jam setelah WO dibuat. Kerugian produksi dihitung hanya saat jam produksi terjadwal; pemulihan sebelum shift tidak menyebabkan kehilangan output. Normal 100 unit/jam, terganggu 40; margin kontribusi Rp500.000/unit; 25% output hilang dapat dikejar. Instalasi 1 jam + restart 1 jam; pemulihan tambahan Rp250.000. Horizon 24 jam dari perbandingan. Semua jadwal/biaya ini asumsi dummy, bukan kondisi pabrik nyata.', 'source':'synthetic-AC-preshift-v2','normal_units_per_hour':100,'disrupted_units_per_hour':40,
             'selling_price_idr':3500000,'avoidable_variable_cost_idr':3000000,'recoverable_fraction':'0.25',
             'installation_hours':1,'restart_hours':1,'recovery_cost_idr':250000,'horizon_hours':24,
             'calendar':'demo next shift begins requested_at + 12h','shift_start_hours':12,'donor':'surplus beyond reserved stock; no additional donor loss assumed'}

def generation():
    return repo.query('SELECT generation FROM pp.demo_control WHERE singleton')[0]['generation']

@router.get('/config')
def config():
    return {'generation':generation(),'context':CONTEXT,'assumptions':ASSUMPTIONS,
      'warehouses':repo.query("SELECT d.warehouse_id AS id,d.name,d.address,d.simulated FROM pp.demo_warehouse_display d JOIN erp.warehouse w ON w.name=d.warehouse_id WHERE w.company='SYN-COMPANY-01' AND NOT w.disabled AND NOT w.is_group ORDER BY d.warehouse_id"),
      'scenarios':[
       {'id':'origin_stock','label':'1 · Stok sendiri','description':'Bearing conveyor merek NTN, lubang 10 mm, diameter luar 30 mm, lebar 9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'1','warehouse_id':'SYN-WH-01'},
       {'id':'transfer_alias','label':'2 · Nama berbeda di gudang 2','description':'Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'6','warehouse_id':'SYN-WH-01'},
       {'id':'vendor_purchase','label':'3 · Perbandingan vendor','description':'Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca.','quantity':'12','warehouse_id':'SYN-WH-01'},
       {'id':'clarification','label':'4 · Demo lengkap: tanya teknisi sampai pilih sumber','description':'Saat inspeksi sebelum shift, bearing conveyor terasa kasar saat diputar. Diameter luar 30 mm. Kode tidak terbaca.','quantity':'6','warehouse_id':'SYN-WH-01'}]}

@router.get('/orders')
def orders():
    rows=repo.query("SELECT s.id,r.id run_id,c.id comparison_id,d.option_id decision FROM pp.wo_identification_session s LEFT JOIN pp.demo_run r ON r.session_id=s.id LEFT JOIN LATERAL (SELECT id FROM pp.demo_comparison WHERE run_id=r.id ORDER BY created_at DESC LIMIT 1)c ON true LEFT JOIN pp.demo_decision d ON d.run_id=r.id WHERE s.company='SYN-COMPANY-01' ORDER BY s.created_at DESC LIMIT 100")
    return {'generation':generation(),'items':[dict(Session(**get_session(r['id'])).model_dump(mode='json'),run_id=r['run_id'],comparison_id=r['comparison_id'],decision={'option_id':r['decision']} if r['decision'] else None) for r in rows]}

@router.get('/orders/{session_id}')
def order(session_id:str):
    # Detail must remain accessible even when absent from the recent-100 list.
    rows=repo.query("SELECT s.id,r.id run_id,c.id comparison_id,d.option_id decision FROM pp.wo_identification_session s LEFT JOIN pp.demo_run r ON r.session_id=s.id LEFT JOIN LATERAL (SELECT id FROM pp.demo_comparison WHERE run_id=r.id ORDER BY created_at DESC LIMIT 1)c ON true LEFT JOIN pp.demo_decision d ON d.run_id=r.id WHERE s.company='SYN-COMPANY-01' AND s.id=%s",(session_id,))
    if not rows:raise repo.ProcurementError('session_not_found','WO tidak ditemukan. Demo mungkin sudah direset.',404)
    r=rows[0]
    return dict(Session(**get_session(r['id'])).model_dump(mode='json'),run_id=r['run_id'],comparison_id=r['comparison_id'],decision={'option_id':r['decision']} if r['decision'] else None)

class ResetInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    confirmation:str
    expected_generation:int

@router.post('/reset')
def reset(body:ResetInput,idempotency_key:str=KEY):
    return repo.query('SELECT pp.demo_reset(%s,%s,%s) AS result',(body.expected_generation,idempotency_key,body.confirmation))[0]['result']

def default_comparison(run):
    if run['identity'].get('unit_scope')=='complete_housed_unit':
        raise repo.ProcurementError('benchmark_acknowledgment_required','Buka demo conveyor makanan untuk meninjau sumber dan asumsi benchmark downtime.',422)
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
        shift_start=max(start,datetime.fromisoformat(run['requested_at'])+timedelta(hours=ASSUMPTIONS['shift_start_hours']))
        schedule=dict(future_from=start.isoformat(),horizon_end=(start+timedelta(hours=24)).isoformat(),calendar_source=ASSUMPTIONS['calendar'],parallel_assumption_version='v1',stages=stages,scheduled_impacted_windows=[dict(start=shift_start.isoformat(),end=(start+timedelta(hours=24)).isoformat())])
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
    if run['identity'].get('unit_scope')=='complete_housed_unit':
        raise repo.ProcurementError('benchmark_acknowledgment_required','Gunakan halaman demo conveyor makanan untuk mengonfirmasi benchmark downtime.',422)
    if run.get('transport')!='whatsapp' and any(v['outcome']=='pending' for v in run['vendors']):
        raise repo.ProcurementError('vendors_pending','Jalankan simulator sebelum membandingkan')
    return create_comparison(run_id,default_comparison(run),idempotency_key)
