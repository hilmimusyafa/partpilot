"""Business regressions against real, owned PostgreSQL 16 and fresh API processes."""
import sys
import json
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from isolated import Cluster

@pytest.fixture
def db():
    c = Cluster()
    with c.connection() as conn:
        migration = ROOT / 'backend/db/012_procurement_demo.sql'
        if migration.exists():
            conn.execute(migration.read_text(), prepare=False)
            conn.execute((ROOT/'backend/db/016_negotiation_policy.sql').read_text(), prepare=False)
    try:
        yield c
    finally:
        c.close()

def identified(c, qty='9', origin='SYN-WH-02', code='G2-BRG-017'):
    draft = c.draft(description='NTN 6200LLU', quantity=qty, warehouse_id=origin)
    candidate = c.sql('SELECT item_code,item_name,brand,description FROM erp.item WHERE item_code=%s', (code,))[0]
    c.sql("UPDATE pp.wo_identification_session SET state='identified',version=2,result=%s WHERE id=%s", (Jsonb({'identified_candidate':candidate}), draft['id']))
    return draft['id']

def start(c, **kwargs):
    sid=identified(c, **kwargs)
    r=c.api('POST','/api/v1/demo/sourcing-runs',{'session_id':sid,'expected_version':2},uuid.uuid4().hex)
    assert r['status']==201,r
    return r['body']

def advance(c, run):
    r=c.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/advance",{})
    assert r['status']==200,r
    return r['body']

def test_origin_sufficient_never_contacts_vendors_or_repairs(db):
    run=start(db,qty='1')
    assert run['status']=='fulfilled_source'
    out=advance(db,run)
    assert out['exchanges']==[]
    assert out['procurement_executed'] is False
    assert db.sql('SELECT count(*) n FROM pp.demo_outbox')[0]['n']==0

def test_all_vendor_outcomes_and_restart_safe_counteroffer(db):
    before=db.snapshot()
    run=start(db)
    out=advance(db,run)
    outcomes={v['vendor_id']:v['outcome'] for v in out['vendors']}
    assert outcomes['SIM-SHORT']=='insufficient_stock'
    assert outcomes['SIM-SILENT']=='no_response'
    assert outcomes['SIM-REFUSE']=='negotiation_refused'
    assert outcomes['SIM-REVISE']=='revised_quote'
    assert outcomes['SIM-ENOUGH']=='revised_quote'
    # Every API invocation uses a new Python process, including retries.
    with ThreadPoolExecutor(max_workers=3) as ex:
        repeated=list(ex.map(lambda _:advance(db,run),range(3)))
    counts=db.sql("SELECT vendor_id,count(*) n FROM pp.demo_outbox WHERE kind='price_counteroffer' GROUP BY vendor_id")
    assert counts and all(r['n']==1 for r in counts)
    assert {r['vendor_id'] for r in counts}=={'SIM-ENOUGH','SIM-REFUSE','SIM-REVISE'}
    assert all(v['id']==out['id'] for v in repeated)
    payloads=json.dumps(db.sql('SELECT payload FROM pp.demo_outbox'))
    assert not any(k in payloads for k in ['competitor','downtime','contribution','benchmark'])
    # Only workflow tables may change.
    after=db.snapshot()
    assert all(after[k]==v for k,v in before.items() if not k.startswith('pp.demo_'))

def test_wrong_identity_and_partial_sources_never_become_whole_source(db):
    run=start(db,qty='11')
    out=advance(db,run)
    assert all(x['status']!='sufficient' for x in out['availability']['alternatives'])
    assert next(v for v in out['vendors'] if v['vendor_id']=='SIM-SHORT')['eligible'] is False

def test_repeated_create_replays_same_run(db):
    sid=identified(db)
    body={'session_id':sid,'expected_version':2};key=uuid.uuid4().hex
    first=db.api('POST','/api/v1/demo/sourcing-runs',body,key)
    second=db.api('POST','/api/v1/demo/sourcing-runs',body,key)
    assert first['status']==second['status']==201
    assert first['body']['id']==second['body']['id']

def test_second_create_key_cannot_be_acknowledged_without_being_bound(db):
    sid=identified(db);body=dict(session_id=sid,expected_version=2)
    first=db.api('POST','/api/v1/demo/sourcing-runs',body,uuid.uuid4().hex)
    assert first['status']==201,first
    second=db.api('POST','/api/v1/demo/sourcing-runs',body,uuid.uuid4().hex)
    assert second['status']==409 and second['body']['error']['code']=='run_already_exists',second

def test_price_budget_is_enforced_inside_postgres(db):
    run=start(db);out=advance(db,run)
    existing=db.sql("SELECT * FROM pp.demo_outbox WHERE run_id=%s AND vendor_id='SIM-REVISE' AND kind='price_counteroffer'",(run['id'],))[0]
    with db.connection() as conn:
        same=conn.execute('SELECT pp.demo_enqueue(%s,%s,%s,%s)',(run['id'],'SIM-REVISE','price_counteroffer',Jsonb(existing['payload']))).fetchone()
        assert same
    wrong=dict(existing['payload'],target_unit_price='1')
    with pytest.raises(Exception,match='counteroffer|conflict'):
        db.sql('SELECT pp.demo_enqueue(%s,%s,%s,%s)',(run['id'],'SIM-REVISE','price_counteroffer',Jsonb(wrong)))

def comparison_input(run):
    from datetime import datetime,timezone,timedelta
    start=datetime.now(timezone.utc)
    def datum(value,unit):return dict(value=value,unit=unit,source='synthetic-test',assumption_version='v1')
    stages=[]
    for kind,begin,end in [('procurement',0,0),('dispatch',0,0),('transport',0,8),('installation',8,9),('restart',9,10)]:
        stages.append(dict(id=kind,kind=kind,start=(start+timedelta(hours=begin)).isoformat(),end=(start+timedelta(hours=end)).isoformat(),depends_on=[stages[-1]['id']] if stages else [],source='synthetic-test',assumption_version='v1'))
    schedule=dict(future_from=start.isoformat(),horizon_end=(start+timedelta(hours=24)).isoformat(),calendar_source='synthetic-test',parallel_assumption_version='v1',stages=stages,scheduled_impacted_windows=[dict(start=start.isoformat(),end=(start+timedelta(hours=24)).isoformat())])
    production=dict(output_unit='units',currency='IDR',currency_scale=2,
                    normal_output_per_hour=datum('100','units/h'),disrupted_output_per_hour=datum('40','units/h'),
                    recoverable_fraction=datum('0.25','fraction'),net_selling_price_per_unit=datum('50','IDR/units'),avoidable_variable_cost_per_unit=datum('20','IDR/units'))
    options=[dict(source_id=s,schedule=schedule,incremental_disruption_costs=[dict(cost_id='overtime',cost_type='recovery',amount=datum('1000','IDR'),evidence_ref='overtime',description='additional recovery')],donor_cost_status=dict(status='not_applicable',source='synthetic-test',assumption_version='v1'),costs_nonduplicated=True)
             for s in ['SYN-WH-01','SIM-ENOUGH','SIM-SHORT','SIM-REFUSE','SIM-REVISE','SIM-SILENT']]
    return dict(expected_version=run['version'],production=production,options=options)

def test_comparison_ranks_complete_options_but_manager_decides(db):
    run=advance(db,start(db));payload=comparison_input(run)
    key=uuid.uuid4().hex
    first=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,key)
    assert first['status']==201,first
    comparison=first['body']; eligible=comparison['eligible_complete_options']
    assert eligible[0]['source_id']=='SIM-REVISE'
    # Frozen initial total1,620,000 ->90%=1,458,000; REVISE target131444/pc.
    # This separately supplied comparison adds13,500 lost contribution +1,000 recovery.
    assert eligible[0]['economics']['future_relevant_option_total']=='1222496.00'
    assert {'SIM-SHORT','SIM-SILENT'}<={o['source_id'] for o in comparison['unrankable_options']}
    assert db.sql('SELECT * FROM pp.demo_decision')==[]
    fresh=db.api('GET',f"/api/v1/demo/comparisons/{comparison['id']}")
    assert fresh['body']['eligible_complete_options']==eligible
    choice={'expected_version':1,'option_id':eligible[0]['option_id'],'acknowledgment':'demo_only'}
    decision_key=uuid.uuid4().hex
    chosen=db.api('POST',f"/api/v1/demo/comparisons/{comparison['id']}/decision",choice,decision_key)
    assert chosen['status']==201 and chosen['body']['procurement_executed'] is False,chosen
    replay=db.api('POST',f"/api/v1/demo/comparisons/{comparison['id']}/decision",choice,decision_key)
    assert replay['body']==chosen['body']

def test_incomplete_cost_is_not_zero_and_cannot_be_selected(db):
    run=advance(db,start(db));payload=comparison_input(run)
    payload['production']['normal_output_per_hour']['value']=None
    response=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,uuid.uuid4().hex)
    assert response['status']==201,response
    assert response['body']['eligible_complete_options']==[]
    cid=response['body']['id']
    rejected=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',dict(expected_version=1,option_id='vendor:SIM-REVISE',acknowledgment='demo_only'),uuid.uuid4().hex)
    assert rejected['status']==409

def test_reservation_or_purchase_never_happens_on_selection(db):
    run=advance(db,start(db));before=db.snapshot()
    comparison=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",comparison_input(run),uuid.uuid4().hex)
    assert comparison['status']==201,comparison
    response=db.api('POST',f"/api/v1/demo/comparisons/{comparison['body']['id']}/decision",dict(expected_version=1,option_id='warehouse:SYN-WH-01',acknowledgment='demo_only'),uuid.uuid4().hex)
    assert response['status']==201,response
    after=db.snapshot()
    assert all(after[k]==v for k,v in before.items() if not k.startswith('pp.demo_'))

def test_crash_after_counteroffer_reservation_replays_same_event(db):
    from backend.procurement import service
    from backend.procurement.simulator import DemoSimulator
    import os
    run=start(db)
    old=os.environ.get('TEST_DATABASE_URL');os.environ['TEST_DATABASE_URL']=db.dsn
    class CrashOnce:
        def send(self,event):
            if event['kind']=='price_counteroffer':raise RuntimeError('simulated crash after committed reservation')
            return DemoSimulator().send(event)
    try:
        with pytest.raises(RuntimeError,match='simulated crash'):service.advance(run['id'],CrashOnce())
    finally:
        if old is None:os.environ.pop('TEST_DATABASE_URL',None)
        else:os.environ['TEST_DATABASE_URL']=old
    reserved=db.sql("SELECT id,payload FROM pp.demo_outbox WHERE kind='price_counteroffer'")[0]
    out=advance(db,run)
    same=db.sql('SELECT id,payload,response FROM pp.demo_outbox WHERE id=%s',(reserved['id'],))[0]
    assert same['payload']==reserved['payload'] and same['response'] is not None
    assert max(v['counteroffers_used'] for v in out['vendors'])==1

def test_manager_rejects_changed_stock_and_changed_quote(db):
    run=advance(db,start(db))
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",comparison_input(run),uuid.uuid4().hex)
    assert compared['status']==201,compared
    cid=compared['body']['id']
    db.sql("UPDATE erp.bin SET reserved_qty=actual_qty WHERE warehouse='SYN-WH-01'")
    body=dict(expected_version=1,option_id='warehouse:SYN-WH-01',acknowledgment='demo_only')
    r=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',body,uuid.uuid4().hex)
    assert r['status']==409 and r['body']['error']['code']=='stock_changed',r
    db.sql("UPDATE pp.demo_outbox SET response=jsonb_set(response,'{quote,unit_price}','\"999999\"'::jsonb) WHERE run_id=%s AND vendor_id='SIM-REVISE' AND kind='price_counteroffer'",(run['id'],))
    body['option_id']='vendor:SIM-REVISE'
    r=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',body,uuid.uuid4().hex)
    assert r['status']==409 and r['body']['error']['code']=='quote_changed',r
    assert not db.sql('SELECT * FROM pp.demo_decision')

def test_comparison_replay_is_identical_and_cannot_override_price(db):
    run=advance(db,start(db));payload=comparison_input(run);key=uuid.uuid4().hex
    first=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,key)
    second=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,key)
    assert first['status']==second['status']==201
    assert first['body']==second['body']
    payload['options'][0]['unit_price']='0'
    r=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,uuid.uuid4().hex)
    assert r['status']==422,r

def test_created_run_replay_does_not_turn_into_mutating_current_read(db):
    sid=identified(db);key=uuid.uuid4().hex;payload=dict(session_id=sid,expected_version=2)
    first=db.api('POST','/api/v1/demo/sourcing-runs',payload,key)
    advance(db,first['body'])
    second=db.api('POST','/api/v1/demo/sourcing-runs',payload,key)
    assert second['body']==first['body']

def test_comparison_and_decision_audit_are_immutable(db):
    run=advance(db,start(db))
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",comparison_input(run),uuid.uuid4().hex)
    assert compared['status']==201,compared
    with pytest.raises(Exception,match='immutable'):
        db.sql("UPDATE pp.demo_comparison SET snapshot='{}'::jsonb WHERE id=%s",(compared['body']['id'],))
    with pytest.raises(Exception,match='immutable'):
        db.sql('DELETE FROM pp.demo_audit WHERE run_id=%s',(run['id'],))

def test_refused_counteroffer_keeps_initial_quote_selectable(db):
    run=advance(db,start(db))
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",comparison_input(run),uuid.uuid4().hex)
    assert compared['status']==201,compared
    cid=compared['body']['id']
    response=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',
                    dict(expected_version=1,option_id='vendor:SIM-REFUSE',acknowledgment='demo_only'),uuid.uuid4().hex)
    assert response['status']==201,response
    assert response['body']['procurement_executed'] is False

def test_database_rejects_missing_source_identity_and_quantity(db):
    sid=identified(db)
    with pytest.raises(Exception,match='invalid_source_snapshot'):
        db.sql('SELECT pp.demo_start(%s,2,%s,%s)',(sid,uuid.uuid4().hex,Jsonb({'status':'sourcing'})))

def test_outbound_requires_original_request_and_expiry(db):
    run=start(db)
    payload={k:run[k] for k in ('identity','quantity','destination_warehouse_id')}
    payload['currency']='IDR'
    with pytest.raises(Exception,match='unsafe_outbound_payload'):
        db.sql('SELECT pp.demo_enqueue(%s,%s,%s,%s)',(run['id'],'SIM-ENOUGH','rfq',Jsonb(payload)))

def test_warehouse_identity_change_blocks_selection(db):
    run=advance(db,start(db))
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",comparison_input(run),uuid.uuid4().hex)
    assert compared['status']==201,compared
    cid=compared['body']['id']
    opt=next(o for o in compared['body']['eligible_complete_options'] if o['source_id']=='SYN-WH-01')
    db.sql("UPDATE erp.item SET brand='SKF' WHERE item_code=%s",(opt['item_code'],))
    response=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',
                    dict(expected_version=1,option_id=opt['option_id'],acknowledgment='demo_only'),uuid.uuid4().hex)
    assert response['status']==409,response
    assert not db.sql('SELECT * FROM pp.demo_decision')

def test_unknown_donor_cost_is_unrankable(db):
    run=advance(db,start(db));payload=comparison_input(run)
    payload['options'][0]['donor_cost_status']['status']='unknown'
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,uuid.uuid4().hex)
    assert compared['status']==201,compared
    assert 'SYN-WH-01' not in [o['source_id'] for o in compared['body']['eligible_complete_options']]

def test_database_rejects_forged_partial_comparison(db):
    from copy import deepcopy
    run=advance(db,start(db));payload=comparison_input(run)
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,uuid.uuid4().hex)
    assert compared['status']==201,compared
    frozen=db.sql('SELECT snapshot FROM pp.demo_comparison WHERE id=%s',(compared['body']['id'],))[0]['snapshot']
    forged=deepcopy(frozen);forged['eligible_complete_options'][0]['quantity']='1'
    with pytest.raises(Exception,match='invalid_comparison'):
        db.sql('SELECT pp.demo_compare(%s,%s,%s,%s,%s)',(run['id'],run['version'],uuid.uuid4().hex,Jsonb(payload),Jsonb(forged)))

def test_unknown_warehouses_and_box_units_are_not_confirmed_absence_or_pieces(db):
    db.sql("UPDATE erp.item SET stock_uom='Box' WHERE item_code='SYN-WH01-NTN-6200LLU'")
    run=start(db)
    scopes={s['warehouse_id']:s for s in run['availability']['alternatives']}
    assert scopes['SYN-WH-01']['status']=='identity_insufficient'
    # The five demo notes are now known; this base fixture has no WH03-05 records.
    assert all(scopes[f'SYN-WH-0{n}']['status']=='not_found' for n in (3,4,5))
    from backend.wo.availability import evaluate_scope
    from decimal import Decimal
    unknown=evaluate_scope('SYN-WH-99',Decimal('6'),{'brand':'NTN','base':'6200','suffix':'LLU'})
    assert unknown.status=='knowledge_unavailable'
    assert run['availability']['complete'] is False

def test_source_box_unit_cannot_become_a_vendor_order_in_pieces(db):
    sid=identified(db)
    db.sql("UPDATE erp.item SET stock_uom='Box' WHERE item_code='G2-BRG-017'")
    response=db.api('POST','/api/v1/demo/sourcing-runs',dict(session_id=sid,expected_version=2),uuid.uuid4().hex)
    assert response['status']==409 and response['body']['error']['code']=='unsupported_source_unit',response
    assert not db.sql('SELECT * FROM pp.demo_run')

def test_expired_historical_option_cannot_be_selected(db):
    from copy import deepcopy
    run=advance(db,start(db));payload=comparison_input(run)
    compared=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['id']}/comparisons",payload,uuid.uuid4().hex)
    assert compared['status']==201,compared
    original=db.sql('SELECT snapshot FROM pp.demo_comparison WHERE id=%s',(compared['body']['id'],))[0]['snapshot']
    # An explicitly arranged historical fixture, not an edit to an immutable
    # record. No sleeps or production-clock changes are required.
    historical=deepcopy(original)
    for option in historical['eligible_complete_options']:option['valid_until']='2000-01-01T00:00:00Z'
    cid=db.sql('INSERT INTO pp.demo_comparison(run_id,request_key,request,snapshot) VALUES(%s,%s,%s,%s) RETURNING id',
               (run['id'],uuid.uuid4().hex,Jsonb(payload),Jsonb(historical)))[0]['id']
    response=db.api('POST',f'/api/v1/demo/comparisons/{cid}/decision',
                    dict(expected_version=1,option_id='vendor:SIM-REVISE',acknowledgment='demo_only'),uuid.uuid4().hex)
    assert response['status']==409 and response['body']['error']['code']=='option_ineligible_or_expired',response
    assert not db.sql('SELECT * FROM pp.demo_decision')
