"""Food conveyor demo: explicit technician/engineering gates and sourced economics."""
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, Header
from pydantic import BaseModel, ConfigDict, Field
from psycopg.types.json import Jsonb
from backend.procurement import repository as repo
from backend.procurement.models import CompareInput
from backend.procurement.benchmark import ReportedDowntimeBenchmark
from backend.procurement.comparison import sources, create_comparison, read_comparison
from backend.procurement.service import get_run
from backend.wo.repository import get_db_connection, create_draft, submit_draft, get_session
from backend.wo.models import DraftCreate, Session
from backend.maintenance.service import get_assessment

router=APIRouter(prefix='/api/v1/food-demo',tags=['Food conveyor evidence demo'])
KEY=Header(...,alias='Idempotency-Key',min_length=1,max_length=128,pattern=r'^[!-~]+$')
CONTEXT=dict(company_id='SYN-COMPANY-01',site_id='FOOD-SITE',production_line_id='FOOD-LINE',station_id='FOOD-STATION',machine_id='FOOD-CONVEYOR',warehouse_id='SYN-WH-01')


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)


class ConfirmWO(Strict):
    part_kind: Literal['exact','candidate']='exact'
    observed_part_code: str
    quantity: str=Field(pattern=r'^[1-9]\d{0,3}$')
    technician: str=Field(min_length=2,max_length=100)
    inspected_and_confirmed: Literal[True]


class Review(Strict):
    reviewer: str=Field(min_length=2,max_length=100)
    decision: Literal['approved','rejected']
    interface_load_speed_checked: bool
    temperature_duty_checked: bool
    hygiene_approved: bool
    notes: str=Field(min_length=10,max_length=2000)


@router.get('/config')
def config():
    return dict(context=CONTEXT,symptoms='Conveyor makanan terasa kasar dan bising setelah high-pressure washdown; ada jejak korosi di sekitar flange. Mesin dihentikan untuk inspeksi.',
        observed_part_code='RHP PSF20CR',quantity='2',inventory_source='synthetic:food-conveyor-v1',
        benchmark=ReportedDowntimeBenchmark().model_dump(),suggested_demo_currency_mapping='18000',
        currency_mapping_note='18000 IDR per unit dolar publikasi adalah asumsi simulasi, bukan kurs aktual atau identifikasi USD.',
        limitations=['Tidak memprediksi umur bearing atau waktu kegagalan.','Kasus OEM adalah preseden eksternal; bukan histori aset demo.','Part dan jumlah harus dikonfirmasi teknisi.'])


def assessment(aid):
    result=get_assessment(aid)
    if not result or result['status']!='completed':
        raise repo.ProcurementError('assessment_not_ready','Selesaikan analisis dan prasyarat terlebih dahulu',422)
    return result


@router.post('/assessments/{aid}/engineering-review',status_code=201)
def engineering_review(aid:str,body:Review):
    item=assessment(aid)
    if not item['result'].get('engineering_candidate'):
        raise repo.ProcurementError('candidate_not_supported','Assessment belum mendukung kandidat alternatif ini',422)
    checks={k:getattr(body,k) for k in ('interface_load_speed_checked','temperature_duty_checked','hygiene_approved')}
    if body.decision=='approved' and not all(checks.values()):
        raise repo.ProcurementError('engineering_checks_required','Seluruh pemeriksaan teknis dan higiene harus disetujui',422)
    from psycopg.rows import dict_row
    with get_db_connection() as conn:
        conn.execute('SELECT id FROM pp.maintenance_assessment WHERE id=%s FOR UPDATE',(aid,))
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute('INSERT INTO pp.maintenance_engineering_review(assessment_id,reviewer,decision,checks,notes) VALUES(%s,%s,%s,%s,%s) RETURNING *',
                (aid,body.reviewer,body.decision,Jsonb(checks),body.notes))
            return cur.fetchone()


@router.post('/assessments/{aid}/work-orders',status_code=201)
def confirmed_work_order(aid:str,body:ConfirmWO,idempotency_key:str=KEY):
    from backend.wo.identity import candidate_identity
    item=assessment(aid)
    expected='PSF20CR' if body.part_kind=='exact' else 'PSF20/LP99'
    proposal=item['result'].get('exact_part_proposal' if body.part_kind=='exact' else 'engineering_candidate')
    cited={ref['evidence_id'] for ref in item['result'].get('evidence_refs',[])}
    if not proposal or proposal.get('identity',{}).get('full_designation')!=expected or 'catalog:'+expected not in cited:
        raise repo.ProcurementError('part_proposal_not_supported','Assessment belum mendukung part ini dengan katalog yang dibaca',422)
    identity=candidate_identity({'item_name':body.observed_part_code})
    if not identity or identity.get('full_designation')!=expected:
        raise repo.ProcurementError('confirmed_part_mismatch','Konfirmasikan kode unit lengkap yang dipilih',422)
    with get_db_connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('food-wo:'+aid,))
        generation=conn.execute('SELECT generation FROM pp.demo_control WHERE singleton').fetchone()[0]
        review_id=None
        if body.part_kind=='candidate':
            row=conn.execute('SELECT id,decision FROM pp.maintenance_engineering_review WHERE assessment_id=%s ORDER BY created_at DESC,id DESC LIMIT 1',(aid,)).fetchone()
            if not row or row[1]!='approved': raise repo.ProcurementError('engineering_approval_required','Kandidat belum disetujui engineering dan higiene',422)
            review_id=row[0]
        old=conn.execute('SELECT session_id FROM pp.maintenance_work_order WHERE assessment_id=%s AND generation=%s AND part_kind=%s',(aid,generation,body.part_kind)).fetchone()
        if old:
            existing=get_session(old[0])
            if existing and str(existing['quantity'])!=body.quantity:
                raise repo.ProcurementError('confirmation_conflict','Jumlah berbeda dari WO yang sudah dibuat',409)
            if existing and existing['state']=='draft':
                _,existing,_=submit_draft(existing['id'],existing['version'],f'food-submit:{existing["id"]}')
            return Session(**existing).model_dump(mode='json')
        symptoms=item['request']['symptoms']
        draft=DraftCreate(**CONTEXT,description=f'Ganti bearing unit flange lengkap RHP {expected}',quantity=body.quantity,urgency='High',
            notes=f'Konfirmasi teknisi: {body.technician}. Assessment {aid}. Gejala dan sumber tersedia di assessment. Diagnosis perlu inspeksi; fixture aset dan stok simulasi.').model_dump()
        _,created,_=create_draft(draft,f'food:{aid}:{generation}:{body.part_kind}')
        conn.execute('INSERT INTO pp.maintenance_work_order(assessment_id,session_id,generation,part_kind,confirmed_by,engineering_review_id) VALUES(%s,%s,%s,%s,%s,%s)',(aid,created['id'],generation,body.part_kind,body.technician,review_id))
    _,submitted,_=submit_draft(created['id'],created['version'],f'food-submit:{created["id"]}')
    return submitted


class BenchmarkInput(Strict):
    external_applicability_acknowledged: Literal[True]
    idr_per_published_currency_unit: str
    conversion_assumption_acknowledged: Literal[True]


def recovery_options(all_sources, start):
    """Use one continuous full-stop calendar covering every eligible recovery."""
    timings=[]
    end=start+timedelta(hours=48)
    for source in all_sources:
        q=source['quote']
        eta=max(start,datetime.fromisoformat(q['delivered_eta'])) if q and q.get('delivered_eta') else start+timedelta(hours=24)
        installed=eta+timedelta(hours=1);restored=installed+timedelta(hours=1)
        timings.append((source,eta,installed,restored))
        if not source['reasons'] and q and datetime.fromisoformat(q['valid_until'])>start:
            end=max(end,restored)
    options=[]
    for source,eta,installed,restored in timings:
        stages=[]
        for kind,a,b in [('procurement',start,start),('dispatch',start,start),('transport',start,eta),('installation',eta,installed),('restart',installed,restored)]:
            stages.append(dict(id=kind,kind=kind,start=a.isoformat(),end=b.isoformat(),depends_on=[stages[-1]['id']] if stages else [],source='synthetic:food-recovery',assumption_version='v1'))
        options.append(dict(source_id=source['source_id'],costs_nonduplicated=True,
            donor_cost_status=dict(status='not_applicable',source='synthetic:surplus beyond reservation; no donor production affected',assumption_version='v1'),
            schedule=dict(future_from=start.isoformat(),horizon_end=end.isoformat(),calendar_source='synthetic:continuous production; full stop',parallel_assumption_version='v1',stages=stages,scheduled_impacted_windows=[dict(start=start.isoformat(),end=end.isoformat())]),
            incremental_disruption_costs=[dict(cost_id='repair-labor',cost_type='recovery',amount=dict(value='250000',unit='IDR',source='synthetic:additional maintenance labor',assumption_version='v1'),evidence_ref='food-labor-v1',description='Asumsi tenaga perbaikan; bukan biaya $26/jam kasus OEM')]))
    return options


@router.post('/sourcing-runs/{rid}/comparison',status_code=201)
def benchmark_comparison(rid:str,body:BenchmarkInput,idempotency_key:str=KEY):
    with get_db_connection() as conn:
        conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('food-comparison:'+idempotency_key,))
        old=repo.query('SELECT id,run_id,request FROM pp.demo_comparison WHERE request_key=%s',(idempotency_key,))
        if old:
            prior=old[0]['request']['production']
            if old[0]['run_id']!=rid or any(prior.get(k)!=v for k,v in body.model_dump().items()):
                raise repo.ProcurementError('idempotency_conflict','Comparison key already used')
            return read_comparison(old[0]['id'])
        source=repo.query("SELECT facts,source_refs FROM pp.maintenance_evidence WHERE id='economics:NSK-SS-E-2054'")
        if not source or source[0]['facts']['reported']['production_loss_rate_per_hour']!='3332':
            raise repo.ProcurementError('benchmark_evidence_missing','Benchmark sumber belum terverifikasi di database',503)
        production=ReportedDowntimeBenchmark(**body.model_dump())
        run=get_run(rid)
        if run['identity'].get('unit_scope')!='complete_housed_unit': raise repo.ProcurementError('wrong_scenario','Benchmark ini khusus skenario conveyor makanan',422)
        options=recovery_options(sources(run),datetime.now(timezone.utc))
        return create_comparison(rid,CompareInput(expected_version=run['version'],production=production,options=options),idempotency_key)
