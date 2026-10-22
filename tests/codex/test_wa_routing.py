"""Synthetic inbound routing; never contact external WhatsApp."""
from datetime import datetime, timezone, timedelta
import sys,uuid
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parent))
from test_whatsapp import wa

def active(wa):
    from test_procurement import start
    from backend.whatsapp.repository import call
    run=start(wa)
    c=call('wa_start',run['id'],'WA-DEMO-1')
    # Reproduce existing history flag without mutating another run.
    wa.sql("UPDATE pp.wa_conversation SET snapshot=snapshot||'{\"requires_reply_reference\":true}'::jsonb WHERE id=%s",(c['id'],))
    rfq=call('wa_enqueue',c['id'],'rfq','Synthetic RFQ',{})
    call('wa_delivery',rfq['id'],'sending',None)
    call('wa_delivery',rfq['id'],'sent','routing-rfq')
    return run,c

def test_plain_reply_after_previous_demo_is_received_and_invalidates_run(wa):
    from backend.whatsapp.repository import call
    run,c=active(wa)
    before=wa.sql('SELECT version FROM pp.demo_run WHERE id=%s',(run['id'],))[0]['version']
    mid=call('wa_inbound','new-plain','628123456789','stok kosong',datetime.now(timezone.utc))
    message=wa.sql('SELECT * FROM pp.wa_message WHERE id=%s',(mid,))[0]
    assert message['conversation_id']==c['id']
    assert message['status']=='received'
    assert wa.sql('SELECT version FROM pp.demo_run WHERE id=%s',(run['id'],))[0]['version']>before
    again=call('wa_inbound','new-plain','628123456789','stok kosong',datetime.now(timezone.utc))
    assert again==mid

@pytest.mark.parametrize('text,quoted,old',[
 ('stok kosong','old-rfq',False),('stok kosong PP-deadbeef',None,False),
 ('stok kosong',None,True)])
def test_explicit_wrong_reference_and_old_timestamp_remain_unmatched(wa,text,quoted,old):
    from backend.whatsapp.repository import call
    _,c=active(wa)
    at=datetime.fromisoformat(c['created_at'])-timedelta(minutes=5) if old else datetime.now(timezone.utc)
    mid=call('wa_inbound',uuid.uuid4().hex,'628123456789',text,at,quoted)
    message=wa.sql('SELECT * FROM pp.wa_message WHERE id=%s',(mid,))[0]
    assert message['conversation_id'] is None and message['status']=='unmatched'
    assert message['payload'].get('routing_reason')

def test_explicit_current_reply_and_no_stock_worker_complete_without_llm(wa,monkeypatch):
    from backend.whatsapp.repository import call
    from backend.whatsapp import worker,extraction
    from backend.procurement.service import get_run
    run,c=active(wa)
    mid=call('wa_inbound','current-reference','628123456789','Stok kosong',datetime.now(timezone.utc),'routing-rfq')
    wa.sql("UPDATE pp.wa_message SET created_at=now()-interval '10 seconds' WHERE id=%s",(mid,))
    def never(*a,**k):raise AssertionError('No LLM needed for explicit no-stock')
    monkeypatch.setattr(extraction,'call_gateway_completion',never)
    worker.process_conversation(wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(c['id'],))[0])
    view=get_run(run['id'])
    assert view['vendors'][0]['outcome']=='no_stock'
    assert not view['vendors'][0]['eligible']
    assert not wa.sql("SELECT * FROM pp.wa_message WHERE kind='price_counteroffer'")


@pytest.mark.parametrize('answer',['Harga per pcs (Rp) : 120000','Tidak bisa nego'])
def test_full_form_reaches_one_negotiation_and_answer_publishes_quote(wa,monkeypatch,answer):
    from backend.whatsapp.repository import call
    from backend.whatsapp import worker,extraction
    from backend.procurement.service import get_run
    from backend.whatsapp.service import next_message
    run,c=active(wa)
    values=dict(identity='NTN 6200LLU',qty_available='20',unit_price='150000',shipping_amount='25000',tax_amount='0',processing_hours='2',delivered_eta='4 jam',valid_until='23 jam')
    body='\n'.join(extraction.LABELS[k]+' : '+v for k,v in values.items())
    def never(*a,**k):raise AssertionError('Canonical form needs no gateway')
    monkeypatch.setattr(extraction,'call_gateway_completion',never)
    def receive(text,ref):
        mid=call('wa_inbound',uuid.uuid4().hex,'628123456789',text,datetime.now(timezone.utc),ref)
        wa.sql("UPDATE pp.wa_message SET created_at=now()-interval '10 seconds' WHERE id=%s",(mid,))
        worker.process_conversation(wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(c['id'],))[0])
    receive(body,None)
    counters=wa.sql("SELECT * FROM pp.wa_message WHERE conversation_id=%s AND kind='price_counteroffer'",(c['id'],))
    assert len(counters)==1
    # Repeated worker calls/reloads cannot reserve an additional offer.
    next_message(wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(c['id'],))[0])
    call('wa_delivery',counters[0]['id'],'sending',None)
    call('wa_delivery',counters[0]['id'],'sent','counter-reference')
    receive(answer,'counter-reference')
    view=get_run(run['id'])
    assert view['vendors'][0]['counteroffers_used']==1
    assert view['vendors'][0]['quote']['unit_price']==('150000' if answer=='Tidak bisa nego' else '120000')
    assert view['vendors'][0]['eligible']
    for _ in range(2):next_message(wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(c['id'],))[0])
    assert len(wa.sql("SELECT * FROM pp.wa_message WHERE kind='price_counteroffer'"))==1


def test_start_reserves_all_recipients_atomically_and_retries_no_duplicate(wa,monkeypatch):
    from test_procurement import start
    from backend.whatsapp import service
    run=start(wa)
    monkeypatch.setattr(service,'status',lambda:dict(can_start=True,connection='connected'))
    monkeypatch.setattr(service,'bridge',lambda *a,**k:dict(registered=True))
    wa.sql("INSERT INTO pp.wa_recipient(id,phone,label,opted_in,consent_source,demo_invite_until,destination) VALUES('WA-DEMO-2','628111111111','Synthetic second',true,'owned-test',now()-interval '1 hour','Cikarang dummy')")
    with pytest.raises(Exception):service.start(run['id'])
    assert not wa.sql('SELECT * FROM pp.wa_conversation')
    assert not wa.sql('SELECT * FROM pp.wa_message')
    wa.sql("UPDATE pp.wa_recipient SET demo_invite_until=now()+interval '1 hour' WHERE id='WA-DEMO-2'")
    for _ in range(2):service.start(run['id'])
    assert len(wa.sql('SELECT * FROM pp.wa_conversation'))==2
    assert len(wa.sql("SELECT * FROM pp.wa_message WHERE kind='rfq'"))==2


def test_invalid_new_form_clears_old_identity_and_cannot_publish_old_item(wa,monkeypatch):
    from test_whatsapp_review import arrange_quoted_conversation
    from backend.whatsapp.repository import call
    from backend.whatsapp import worker,extraction
    from backend.procurement.service import get_run
    rid,cid,_=arrange_quoted_conversation(wa)
    text='Merek dan nomor kode : NTT-860\nHarga per pcs (Rp) : 120000'
    mid=call('wa_inbound','invalid-revision','628123456789',text,datetime.now(timezone.utc))
    wa.sql("UPDATE pp.wa_message SET created_at=now()-interval '10 seconds' WHERE id=%s",(mid,))
    monkeypatch.setattr(extraction,'call_gateway_completion',lambda *a,**k:pytest.fail('No gateway for form'))
    worker.process_conversation(wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(cid,))[0])
    c=wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',(cid,))[0]
    assert 'identity' not in c['fields'] and c['status']=='partial'
    assert not get_run(rid)['vendors'][0]['eligible']
    assert not wa.sql("SELECT * FROM pp.wa_message WHERE kind='price_counteroffer'")
    assert 'Merek dan nomor kode' in wa.sql("SELECT body FROM pp.wa_message WHERE kind='followup'")[0]['body']
