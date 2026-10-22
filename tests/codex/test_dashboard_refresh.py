"""Owned database regressions for live dashboard revisions; no real messages."""
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from test_whatsapp import wa
from test_demo_console import demo

@pytest.mark.parametrize('status',['partial','needs_review'])
def test_nonquote_reply_invalidates_dashboard_revision(wa,status):
    from test_whatsapp_review import arrange_quoted_conversation,compare_real_quote
    from backend.whatsapp.repository import call
    from backend.procurement.service import get_run
    rid,cid,fields=arrange_quoted_conversation(wa)
    comparison=compare_real_quote(wa,rid)
    before=get_run(rid)
    c=wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(cid,))[0]
    assert call('wa_apply',cid,c['version'],fields,status,None,[])
    after=get_run(rid)
    assert after['version']>before['version'], 'Partial/review vendor updates must invalidate automatic comparison'
    assert not after['vendors'][0]['eligible']
    with pytest.raises(Exception,match='quote_changed'):
        wa.sql('SELECT pp.demo_choose(%s,1,%s,%s)',(comparison['id'],'vendor:WA-DEMO-1',uuid.uuid4().hex))
    assert not wa.sql('SELECT * FROM pp.demo_decision')
    assert not wa.sql('SELECT * FROM pp.demo_purchase_order')

def test_exhausted_extraction_invalidates_dashboard_revision(wa):
    from test_whatsapp_review import arrange_quoted_conversation
    from backend.whatsapp.repository import call
    from backend.procurement.service import get_run
    rid,cid,_=arrange_quoted_conversation(wa)
    mid=call('wa_inbound','refresh-'+uuid.uuid4().hex,'628123456789','owned test',datetime.now(timezone.utc))
    before=get_run(rid)
    assert wa.sql('SELECT pp.wa_parse_attempt(%s) result',(mid,))[0]['result']
    assert call('wa_parse_attempt',mid)
    assert not call('wa_parse_attempt',mid)
    after=get_run(rid)
    assert after['version']>before['version']
    assert after['vendors'][0]['outcome']=='needs_review'

def test_closed_conversation_exhaustion_cannot_reopen_it(wa):
    from test_whatsapp_review import arrange_quoted_conversation
    from backend.whatsapp.repository import call
    rid,cid,_=arrange_quoted_conversation(wa)
    mid=call('wa_inbound','closed-'+uuid.uuid4().hex,'628123456789','owned test',datetime.now(timezone.utc))
    assert call('wa_parse_attempt',mid) and call('wa_parse_attempt',mid)
    wa.sql("UPDATE pp.wa_conversation SET status='closed' WHERE id=%s",(cid,))
    before=wa.sql('SELECT version FROM pp.demo_run WHERE id=%s',(rid,))[0]['version']
    assert not call('wa_parse_attempt',mid)
    assert wa.sql('SELECT status FROM pp.wa_conversation WHERE id=%s',(cid,))[0]['status']=='closed'
    assert wa.sql('SELECT version FROM pp.demo_run WHERE id=%s',(rid,))[0]['version']==before

def test_direct_manager_order_returns_latest_state_and_scoped_404(demo):
    c,client=demo
    from test_procurement import start,advance
    run=advance(c,start(c))
    sid=c.sql('SELECT session_id FROM pp.demo_run WHERE id=%s',(run['id'],))[0]['session_id']
    url='/api/v1/demo/orders/'+sid
    direct=client.get(url)
    assert direct.status_code==200,direct.text
    assert direct.json()['id']==sid and direct.json()['run_id']==run['id']
    comp=client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison",json={},headers={'Idempotency-Key':uuid.uuid4().hex})
    assert comp.status_code==201,comp.text
    assert client.get(url).json()['comparison_id']==comp.json()['id']
    assert client.get('/api/v1/demo/orders/missing').status_code==404
    assert client.get(url,auth=('demo','incorrect')).status_code==401
    # Owned fixture inserts101 newer sessions; target must remain reachable directly.
    c.sql("INSERT INTO pp.wo_identification_session SELECT (jsonb_populate_record(NULL::pp.wo_identification_session,to_jsonb(s)||jsonb_build_object('id',gen_random_uuid()::text,'created_at',now()+interval '1 minute'))).* FROM pp.wo_identification_session s CROSS JOIN generate_series(1,101) WHERE s.id=%s",(sid,))
    assert sid not in {item['id'] for item in client.get('/api/v1/demo/orders').json()['items']}
    assert client.get(url).json()['id']==sid
    c.sql("INSERT INTO erp.company(name) VALUES('foreign-read-test')")
    c.sql("UPDATE pp.wo_identification_session SET company='foreign-read-test' WHERE id=%s",(sid,))
    assert client.get(url).status_code==404
