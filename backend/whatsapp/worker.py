"""Single supervised consumer; DB lock prevents overlapping chat workers."""
import time
from datetime import datetime,timezone,timedelta
from backend.wo.repository import get_db_connection
from .repository import query,call
from .service import bridge,quote,next_message
from .extraction import extract,FIELDS

def process_conversation(c):
    pending=query("SELECT * FROM pp.wa_message WHERE conversation_id=%s AND direction='in' AND status='received' ORDER BY created_at,id",(c['id'],))
    if not pending:
        if c['status']!='no_response' and c['last_inbound_at'] is None and datetime.now(timezone.utc)>c['created_at']+timedelta(hours=24):
            call('wa_apply',c['id'],c['version'],c['fields'],'no_response',None,[])
        else:next_message(c)
        return
    # Debounce consecutive vendor messages, avoiding a follow-up for every WhatsApp bubble.
    if datetime.now(timezone.utc)-pending[-1]['created_at']<timedelta(seconds=8):return
    fields=dict(c['fields']);outcome=None;ids=[];changed=set()
    for m in pending[:8]:
        if not call('wa_parse_attempt',m['id']):return
        result=extract(m['body'],m['received_at'] or m['created_at'])
        invalid=[key for key in result.get('invalid_fields',[]) if key in FIELDS]
        for key in invalid:fields.pop(key,None)
        fields.update(result['fields']);changed.update(result['fields']);changed.update(invalid);outcome=result['outcome'] or outcome;ids.append(m['id'])
    counter=query("SELECT * FROM pp.wa_message WHERE conversation_id=%s AND kind='price_counteroffer' AND status='sent'",(c['id'],))
    applicable_counter=bool(counter and any((m['received_at'] or m['created_at'])>=counter[0]['delivered_at']-timedelta(seconds=5) for m in pending[:8]))
    # A non-answer cannot publish a stale quote as a negotiated revision.
    q=quote(c,fields) if changed or outcome=='negotiation_refused' and applicable_counter else None
    if applicable_counter and 'unit_price' not in changed and outcome!='negotiation_refused':q=None
    status=('quoted' if q else 'partial') if changed else c['status']
    if status=='waiting':status='partial'
    if fields.get('identity') and fields['identity']!=c['snapshot']['identity']:status='needs_review';q=None
    if outcome=='no_stock':status='no_stock';fields['qty_available']='0';q=None
    elif outcome=='negotiation_refused' and applicable_counter:
        status='negotiation_refused'
    if q:
        from decimal import Decimal
        if Decimal(q['qty_available'])<Decimal(c['snapshot']['quantity']):status='insufficient_stock'
    if call('wa_apply',c['id'],c['version'],fields,status,q,ids):
        updated=query('SELECT * FROM pp.wa_conversation WHERE id=%s',(c['id'],))[0]
        next_message(updated)

def tick():
    with get_db_connection() as singleton:
        if not singleton.execute('SELECT pg_try_advisory_lock(72490123)').fetchone()[0]:return
        try:
            status=bridge('/status')
            if status.get('connection')!='connected':return
            for msg in bridge('/inbox').get('messages',[]):
                call('wa_inbound',msg['message_id'],msg['phone'],msg['text'],msg['received_at'],msg.get('quoted_transport_id'))
                bridge('/inbox/ack',{'message_ids':[msg['message_id']]})
            for c in query("SELECT * FROM pp.wa_conversation WHERE status<>'closed' ORDER BY created_at"):
                try:process_conversation(c)
                except Exception as exc:print('WA extraction tick:',type(exc).__name__,flush=True)
            # Shared reset fence spans send: reset cannot race a new delivery.
            with get_db_connection() as fence:
                fence.execute('SELECT pg_advisory_xact_lock_shared(72490122)')
                for m in query("SELECT m.*,r.phone FROM pp.wa_message m JOIN pp.wa_recipient r ON r.id=m.vendor_id WHERE m.direction='out' AND m.status IN ('queued','sending') ORDER BY m.created_at LIMIT 8"):
                    if m['status']=='sending':
                        # Previous process may have sent it. Conservative no-resend on crash.
                        call('wa_delivery',m['id'],'uncertain',None);continue
                    reserved=call('wa_delivery',m['id'],'sending',None)
                    if reserved['status']!='sending':continue
                    try:
                        result=bridge('/send',{'event_id':m['id'],'phone':m['phone'],'text':m['body']})
                        call('wa_delivery',m['id'],'sent' if result.get('status')=='sent' else 'uncertain',result.get('message_id'))
                    except Exception:call('wa_delivery',m['id'],'uncertain',None)
        finally:singleton.execute('SELECT pg_advisory_unlock(72490123)')

def run():
    while True:
        try:tick()
        except Exception as exc:print('WA worker tick:',type(exc).__name__,flush=True)
        time.sleep(3)
