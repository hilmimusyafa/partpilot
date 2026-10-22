import sys, json, uuid
from pathlib import Path
import pytest
from psycopg.types.json import Jsonb
sys.path.insert(0,str(Path(__file__).resolve().parent))
from isolated import Cluster

@pytest.fixture
def db():
    c=Cluster()
    try:yield c
    finally:c.close()

def test_review_conflict_is_readable_after_restart(db):
    d=db.draft()
    db.sql("UPDATE pp.wo_identification_session SET state='needs_review',result=%s WHERE id=%s",(Jsonb({'conflicts':['category unknown']}),d['id']))
    response=db.api('GET',f"/api/v1/work-orders/{d['id']}")
    assert response['status']==200,response
    assert response['body']['conflicts']==[{'message':'category unknown'}]

def test_null_quantity_survives_draft_and_cannot_submit(db):
    d=db.draft(quantity=None)
    assert d['quantity'] is None
    r=db.api('POST',f"/api/v1/work-orders/{d['id']}/submit",dict(expected_version=1),uuid.uuid4().hex)
    assert r['status']==422,r

@pytest.mark.parametrize('confirmed',['9','2'])
def test_quantity_conflict_becomes_question_not_worker_crash(db,monkeypatch,confirmed):
    from backend.wo import gateway,worker
    monkeypatch.setenv('TEST_DATABASE_URL',db.dsn)
    d=db.draft('bearing NTN 6200LLU qty 2',quantity='9')
    response=db.api('POST',f"/api/v1/work-orders/{d['id']}/submit",dict(expected_version=1),uuid.uuid4().hex)
    assert response['status']==202,response
    facts=[dict(key=k,value=v,source='description',evidence=[dict(source_field='description',raw_substring=v,normalized_value=v)])
           for k,v in [('brand','NTN'),('base','6200'),('suffix','LLU'),('quantity','2')]]
    monkeypatch.setattr(gateway,'call_gateway_completion',lambda *args,**kw:dict(status='ok',content=json.dumps({'facts':facts}),model='controlled-test'))
    worker.process_job(worker.claim_next_job('quantity-test'))
    response=db.api('GET',f"/api/v1/work-orders/{d['id']}")
    assert response['status']==200,response
    assert response['body']['state']=='awaiting_clarification',response
    assert response['body']['quantity']=='9'
    current=response['body'];question=current['result']['questions'][0]
    answer=db.api('POST',f"/api/v1/work-orders/{d['id']}/answers",
                  dict(expected_version=current['version'],answers=[dict(question_id=question['id'],answer=confirmed)]),uuid.uuid4().hex)
    assert answer['status']==202,answer
    worker.process_job(worker.claim_next_job('quantity-confirmed'))
    current=db.api('GET',f"/api/v1/work-orders/{d['id']}")['body']
    assert current['state']=='identified',current
    assert current['quantity']==confirmed
    assert db.row(d['id'])['raw_submission']['quantity']=='9'

@pytest.mark.parametrize('failure',['timeout','outage'])
def test_gateway_failure_has_durable_backoff_then_bounded_failure(db,monkeypatch,failure):
    from backend.wo import gateway,worker
    monkeypatch.setenv('TEST_DATABASE_URL',db.dsn)
    d=db.draft()
    submitted=db.api('POST',f"/api/v1/work-orders/{d['id']}/submit",dict(expected_version=1),uuid.uuid4().hex)
    assert submitted['status']==202,submitted
    calls=[]
    def fail(*args,**kwargs):
        calls.append(failure)
        return dict(status='error',error=failure,retriable=True,model='controlled-test')
    monkeypatch.setattr(gateway,'call_gateway_completion',fail)
    worker.process_job(worker.claim_next_job('failure-first'))
    assert db.row(d['id'])['state']=='queued'
    assert worker.claim_next_job('early-retry') is None
    db.sql("UPDATE pp.wo_identification_job SET available_at=now()-interval '1 second' WHERE session_id=%s",(d['id'],))
    worker.process_job(worker.claim_next_job('failure-second'))
    current=db.api('GET',f"/api/v1/work-orders/{d['id']}")['body']
    assert current['state']=='failed' and not current['result'].get('identified_candidate')
    assert current['error']['retriable'] is True
    assert len(calls)==2 and worker.claim_next_job('third-retry') is None

@pytest.mark.live_gateway
def test_actual_gateway_drives_persisted_wo_and_procurement(db):
    """LIVE integration. Missing credentials or gateway failure is a failure, not a skip."""
    from datetime import datetime,timezone
    import time
    d=db.draft('bearing NTN 6200LLU',quantity='9',warehouse_id='SYN-WH-02')
    response=db.api('POST',f"/api/v1/work-orders/{d['id']}/submit",dict(expected_version=1),uuid.uuid4().hex)
    assert response['status']==202,response
    seen=[]
    for attempt in range(2):
        observed=db.worker('live');seen+=observed['observations']
        current=db.api('GET',f"/api/v1/work-orders/{d['id']}")
        assert current['status']==200,current
        if current['body']['state'] not in ('queued','processing'):break
        time.sleep(5.1)
    assert current['body']['state']=='identified',current
    assert current['body']['identified_item_code']=='G2-BRG-017'
    assert seen and any(o['status']=='ok' and o['response_sha256'] for o in seen)
    db.sql((Path(__file__).resolve().parents[2]/'backend/db/012_procurement_demo.sql').read_text())
    run=db.api('POST','/api/v1/demo/sourcing-runs',dict(session_id=d['id'],expected_version=current['body']['version']),uuid.uuid4().hex)
    assert run['status']==201,run
    sourcing=db.api('POST',f"/api/v1/demo/sourcing-runs/{run['body']['id']}/advance",{})
    assert sourcing['status']==200,sourcing
    assert sourcing['body']['identity']=={'brand':'NTN','base':'6200','suffix':'LLU'}
    assert next(v for v in sourcing['body']['vendors'] if v['vendor_id']=='SIM-REVISE')['counteroffers_used']==1
