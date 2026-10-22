import sys
import uuid
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).parent))
from isolated import Cluster

@pytest.fixture
def demo(monkeypatch):
    c = Cluster()
    monkeypatch.setenv('DATABASE_URL', c.dsn)
    monkeypatch.setenv('TEST_DATABASE_URL', c.dsn)
    monkeypatch.setenv('PARTPILOT_DEMO_PASSWORD', 'test-only-secret')
    from backend.demo.bootstrap import install_demo
    # Test harness owns this isolated cluster; never enable on a shared database.
    with c.connection() as conn:
        conn.execute("DELETE FROM erp.company WHERE name LIKE 'foreign-%'")
        install_demo(conn, allow_test_database=True)
    from backend.demo.app import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        client.auth = ('demo', 'test-only-secret')
        client.headers['X-PartPilot-Request'] = 'demo'
        client.headers['X-PartPilot-Generation'] = '1'
        yield c, client
    c.close()

def test_demo_auth_and_request_boundary(demo):
    _, client = demo
    assert client.get('/api/v1/demo/config', auth=('demo', 'wrong')).status_code == 401
    assert client.get('/api/v1/health', auth=None).status_code == 200
    config = client.get('/api/v1/demo/config').json()
    assert len(config['warehouses']) == 5
    assert len(config['scenarios']) >= 4
    assert client.post('/api/v1/demo/reset', json={'confirmation':'RESET DEMO','expected_generation':1},
                       headers={'Origin':'https://evil.example','Idempotency-Key':uuid.uuid4().hex}).status_code == 403

def test_reset_is_repeatable_atomic_and_archived(demo):
    c, client = demo
    config = client.get('/api/v1/demo/config').json()
    c.draft()
    before = c.sql('SELECT item_code,warehouse,actual_qty,reserved_qty FROM erp.bin ORDER BY item_code')
    c.sql("UPDATE erp.bin SET actual_qty=0,reserved_qty=0 WHERE item_code='SYN-WH01-NTN-6200LLU'")
    key = uuid.uuid4().hex
    body = {'confirmation':'RESET DEMO','expected_generation':config['generation']}
    first = client.post('/api/v1/demo/reset', json=body, headers={'Idempotency-Key':key})
    assert first.status_code == 200, first.text
    assert first.json()['generation'] == config['generation'] + 1
    assert client.get('/api/v1/demo/orders').json()['items'] == []
    assert len(c.sql('SELECT * FROM pp.demo_reset_audit')) == 1
    assert c.sql('SELECT item_code,warehouse,actual_qty,reserved_qty FROM erp.bin ORDER BY item_code') == before
    assert client.post('/api/v1/demo/reset',json=body,headers={'Idempotency-Key':key}).json() == first.json()
    assert client.post('/api/v1/demo/reset',json=body,headers={'Idempotency-Key':'different'}).status_code == 409
    body['expected_generation'] = first.json()['generation']
    assert client.post('/api/v1/demo/reset',json=body,headers={'Idempotency-Key':uuid.uuid4().hex}).status_code == 200

def test_reset_rejects_active_worker_and_disabled_database(demo):
    c, client = demo
    draft = c.draft()
    c.sql("INSERT INTO pp.wo_identification_job(session_id,input_revision,status,lease_until) VALUES(%s,1,'running',now()+interval '2 minutes')", (draft['id'],))
    body = {'confirmation':'RESET DEMO','expected_generation':1}
    assert client.post('/api/v1/demo/reset',json=body,headers={'Idempotency-Key':uuid.uuid4().hex}).status_code == 409
    assert c.row(draft['id'])
    c.sql('UPDATE pp.demo_control SET reset_enabled=false')
    with pytest.raises(Exception,match='reset_disabled'):
        c.sql("SELECT pp.demo_reset(1,'direct-call','RESET DEMO')")

def test_realistic_comparison_and_persisted_manager_list(demo):
    c, client = demo
    from test_procurement import start, advance
    run = advance(c, start(c))
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison", json={}, headers={'Idempotency-Key':'prepared-once'})
    assert response.status_code == 201, response.text
    comparison = response.json()
    assert comparison['eligible_complete_options']
    assert comparison['production']['net_selling_price_per_unit']['value'] == '3500000'
    second = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison",json={},headers={'Idempotency-Key':'prepared-once'})
    assert second.json()['id'] == comparison['id']
    orders = client.get('/api/v1/demo/orders').json()['items']
    assert orders[0]['run_id'] == run['id']
    assert orders[0]['comparison_id'] == comparison['id']
    option_id = comparison['eligible_complete_options'][0]['option_id']
    chosen = client.post(f"/api/v1/demo/comparisons/{comparison['id']}/decision",json={
        'expected_version':1,'option_id':option_id,'acknowledgment':'demo_only'},headers={'Idempotency-Key':'chosen-once'})
    assert chosen.status_code == 201, chosen.text
    assert client.get('/api/v1/demo/orders').json()['items'][0]['decision'] == {'option_id':option_id}

def test_stale_create_cannot_recreate_archived_work_after_reset(demo):
    _,client=demo
    config=client.get('/api/v1/demo/config').json()
    body=dict(config['context'],warehouse_id='SYN-WH-01',description='NTN 6200LLU',quantity='1')
    key=uuid.uuid4().hex
    first=client.post('/api/v1/work-orders',json=body,headers={'Idempotency-Key':key})
    assert first.status_code==201,first.text
    reset=client.post('/api/v1/demo/reset',json={'confirmation':'RESET DEMO','expected_generation':1},headers={'Idempotency-Key':'reset-old-create'})
    assert reset.status_code==200,reset.text
    stale=client.post('/api/v1/work-orders',json=body,headers={'Idempotency-Key':key})
    assert stale.status_code==409
    assert stale.json()['error']['code']=='generation_conflict'
    assert client.get('/api/v1/demo/orders').json()['items']==[]

def test_concurrent_comparison_requests_replay_identical_result(demo):
    from concurrent.futures import ThreadPoolExecutor
    c,client=demo
    from test_procurement import start,advance
    run=advance(c,start(c))
    def create(_):
        return client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison",json={},headers={'Idempotency-Key':'concurrent-prepare'})
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(create,range(3)))
    assert [r.status_code for r in results]==[201,201,201],[r.text for r in results]
    assert len({r.json()['id'] for r in results})==1

def test_orders_read_is_consistent_when_another_tab_resets(demo,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    import time
    from backend.demo import console
    c,client=demo
    c.draft()
    reached=Event();release=Event()
    original=console.get_session
    def slow_read(sid):
        reached.set()
        assert release.wait(5)
        return original(sid)
    monkeypatch.setattr(console,'get_session',slow_read)
    with ThreadPoolExecutor(max_workers=2) as pool:
        read=pool.submit(client.get,'/api/v1/demo/orders')
        assert reached.wait(5)
        reset=pool.submit(client.post,'/api/v1/demo/reset',json={'confirmation':'RESET DEMO','expected_generation':1},headers={'Idempotency-Key':'reset-during-read'})
        time.sleep(.2)
        waited=not reset.done()
        release.set()
        # A reset must wait for the complete read, not erase IDs midway.
        assert waited
        assert read.result().status_code==200
        assert reset.result().status_code==200

def test_deployment_timeout_is_bounded_and_recorded(demo,monkeypatch):
    from backend.wo import gateway,worker
    c,client=demo
    monkeypatch.setenv('PARTPILOT_GATEWAY_TIMEOUT_SECONDS','60')
    seen=[]
    def failed_call(*args,**kw):
        seen.append(kw['timeout'])
        return {'status':'error','error':'controlled timeout','retriable':False}
    monkeypatch.setattr(gateway,'call_gateway_completion',failed_call)
    s=c.draft()
    r=client.post(f"/api/v1/work-orders/{s['id']}/submit",json={'expected_version':s['version']},headers={'Idempotency-Key':'timeout-test'})
    assert r.status_code==202,r.text
    job=worker.claim_next_job('timeout-test')
    worker.process_job(job)
    assert seen==[60]
    event=c.sql("SELECT payload FROM pp.wo_identification_event WHERE session_id=%s AND event_type='result_applied'",(s['id'],))[-1]
    assert event['payload']['timeout']==60
    monkeypatch.setenv('PARTPILOT_GATEWAY_TIMEOUT_SECONDS','91')
    with pytest.raises(ValueError):gateway.runtime_timeout()
