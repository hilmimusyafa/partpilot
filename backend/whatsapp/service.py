import os
from datetime import datetime,timezone
from decimal import Decimal
import httpx
from backend.procurement import repository as procurement
from backend.procurement.models import Quote
from .repository import query,call,available
from .extraction import FIELDS,LABELS

def bridge(path,body=None):
    token=os.environ.get('PARTPILOT_WA_INTERNAL_TOKEN','')
    if not token:raise procurement.ProcurementError('whatsapp_not_configured','Koneksi WhatsApp belum dikonfigurasi',503)
    try:
        with httpx.Client(timeout=30) as client:
            response=client.request('GET' if body is None else 'POST','http://127.0.0.1:18081'+path,json=body,headers={'Authorization':'Bearer '+token})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        raise procurement.ProcurementError('whatsapp_unavailable','Koneksi WhatsApp belum tersedia; lihat halaman WhatsApp',503) from None

def status():
    recipients=query('SELECT id,label,opted_in,demo_invite_until,destination FROM pp.wa_recipient ORDER BY id') if available() else []
    try:result=bridge('/status')
    except procurement.ProcurementError:result={'connection':'disconnected','qr_data_url':None,'enabled':False}
    can_start=len(recipients)>0 and all(r['opted_in'] and r['destination'] and r['demo_invite_until'] and r['demo_invite_until']>datetime.now(timezone.utc) for r in recipients)
    return {**result,'can_start':can_start,'blocked_reason':None if can_start else 'Persetujuan peserta/tujuan atau masa undangan demo belum aktif.',
            'recipients':[{'id':r['id'],'label':r['label'],'registered':None} for r in recipients]}

def messages(cid):return query('SELECT id,direction,body AS text,status,kind,created_at,received_at,delivered_at FROM pp.wa_message WHERE conversation_id=%s ORDER BY created_at,id',(cid,))

def conversations(run_id=None):
    rows=query('SELECT c.*,r.label FROM pp.wa_conversation c JOIN pp.wa_recipient r ON r.id=c.vendor_id '+('WHERE c.run_id=%s ' if run_id else '')+'ORDER BY c.created_at DESC LIMIT 50',(run_id,) if run_id else ())
    for c in rows:
        c['messages']=messages(c['id']);c['missing_fields']=[k for k in FIELDS if k not in c['fields']]
        c['counteroffers_used']=sum(m['kind']=='price_counteroffer' for m in c['messages'])
        c['followups_used']=sum(m['kind']=='followup' for m in c['messages'])
    return {'conversations':rows}

def rfq(c):
    s=c['snapshot'];identity=s['identity'];code=f"{identity['brand']} {identity['base']}{identity['suffix']}"
    return ("Halo Kak, kami dari PartPilot. Mau tanya ketersediaan bearing berikut:\n\n"
      f"Barang: {code}\nKebutuhan: {s['quantity']} pcs\nTujuan pengiriman: {s['shipping_destination']} (alamat dummy untuk demo)\n\n"
      "Ini pengujian yang sudah disepakati, bukan pesanan pembelian.\n\n"
      "Kalau stok tersedia, mohon salin dan isi form berikut ya Kak:\n\n"+quote_form(FIELDS)+"\n\n"
      "Kalau stok kosong, cukup balas 'stok kosong'. Jika ada yang belum diketahui, tulis 'belum tahu'. Ongkir dan pajak diisi total untuk kebutuhan di atas; tulis 0 jika tidak dikenakan. Terima kasih 🙏\n\n"
      f"Referensi demo: PP-{c['id'][:8]}. Mohon balas memakai fitur Reply pada pesan ini agar tidak tertukar dengan pengujian sebelumnya.")

def quote_form(fields):
    return '\n'.join(f'{LABELS[k]} : ' for k in fields)

def start(run_id):
    info=status()
    if not info['can_start']:raise procurement.ProcurementError('wa_consent_or_window_required',info['blocked_reason'])
    if info['connection']!='connected':raise procurement.ProcurementError('whatsapp_not_connected','Hubungkan WhatsApp dengan memindai QR dahulu')
    recipients=query('SELECT id,phone FROM pp.wa_recipient WHERE opted_in ORDER BY id')
    # Validate every recipient before reserving any message.
    for r in recipients:
        if not bridge('/check',{'phone':r['phone']}).get('registered'):
            raise procurement.ProcurementError('whatsapp_number_unregistered',f"{r['id']} tidak terdaftar di WhatsApp; periksa nomor demo",422)
    for r in recipients:
        c=call('wa_start',run_id,r['id']);call('wa_enqueue',c['id'],'rfq',rfq(c),{})
    return conversations(run_id)

def quote(c,fields):
    if any(k not in fields for k in FIELDS) or fields['identity']!=c['snapshot']['identity']:return None
    s=c['snapshot']
    try:
        q=Quote.model_validate(dict(fields,quote_id='wa:'+c['id'],revision=c['version'],quantity_unit='Nos',currency='IDR',
            destination_warehouse_id=s['destination_warehouse_id'],source='whatsapp:vendor-reply',assumption_version='vendor-reported-v1'))
        if q.delivered_eta<datetime.fromisoformat(s['requested_at']):return None
        return q.model_dump(mode='json')
    except (ValueError,TypeError):return None

def vendor_views(run,at):
    result=[]
    for c in conversations(run['id'])['conversations']:
        events=procurement.exchanges(run['id'])
        first=next((e for e in events if e['vendor_id']==c['vendor_id'] and e['kind']=='rfq'),{})
        counter=next((e for e in events if e['vendor_id']==c['vendor_id'] and e['kind']=='price_counteroffer'),{})
        q=(counter.get('response') or {}).get('quote') or (first.get('response') or {}).get('quote')
        from backend.procurement.service import quote_reasons
        reasons=quote_reasons(q,run['snapshot'],at)
        if c['status'] not in ('quoted','negotiation_refused','insufficient_stock'):reasons.append(c['status'])
        if counter and counter.get('response') is None:reasons.append('negotiation_pending')
        result.append({'vendor_id':c['vendor_id'],'outcome':c['status'],'quote':q,'initial_quote':(first.get('response') or {}).get('quote'),
            'counteroffers_used':c['counteroffers_used'],'eligible':not reasons,'ineligible_reasons':reasons,'followups_used':c['followups_used']})
    return result

def next_message(c):
    if c['status'] in ('closed','needs_review','no_stock','no_response','insufficient_stock','negotiation_refused'):return
    msgs=messages(c['id'])
    if any(m['direction']=='out' and m['status'] in ('queued','sending','uncertain') for m in msgs):return
    counter=next((m for m in msgs if m['kind']=='price_counteroffer'),None)
    inbound=[m for m in msgs if m['direction']=='in']
    need_counter_confirmation=bool(counter and counter['status']=='sent' and inbound and
        (inbound[-1]['received_at'] or inbound[-1]['created_at'])>=counter['delivered_at'] and
        query("SELECT 1 FROM pp.demo_outbox WHERE run_id=%s AND vendor_id=%s AND kind='price_counteroffer' AND response IS NULL",(c['run_id'],c['vendor_id'])))
    if c['status']=='quoted' and not counter:
        from backend.procurement.negotiation import plan
        round_plan=plan(c['run_id'])
        planned=next((v for v in (round_plan or {}).get('vendors',[]) if v['vendor_id']==c['vendor_id']),None)
        if not planned or planned['status']!='planned':return
        target=Decimal(planned['target_unit_price'])
        price=f'{target:,.0f}'.replace(',','.')
        call('wa_enqueue',c['id'],'price_counteroffer',f"Terima kasih penawarannya, Kak. Untuk kebutuhan demo {c['snapshot']['quantity']} pcs ini, apakah bisa dibantu Rp{price} per pcs? Ongkir, pajak, dan jadwal tetap mengikuti penawaran tadi. Mohon balas harga per pcs yang disetujui, atau 'tidak bisa nego' jika harga awal sudah pas. Ini belum konfirmasi pembelian ya Kak 🙏",{'target_unit_price':str(target)})
        return
    missing=[k for k in FIELDS if k not in c['fields']]
    if need_counter_confirmation and 'unit_price' not in missing:missing.append('unit_price')
    if not missing or not inbound or sum(m['kind']=='followup' for m in msgs)>=3:return
    key=inbound[-1]['id']
    previous=query("SELECT 1 FROM pp.wa_message WHERE conversation_id=%s AND request_key=%s",(c['id'],'followup:'+key))
    if previous:return
    text=('Terima kasih, Kak. Jawaban sebelumnya sudah kami catat. Mohon salin dan isi bagian yang masih kurang jelas ini ya:\n\n'
          +quote_form(missing)+'\n\nKalau belum diketahui, tulis "belum tahu". Untuk ongkir/pajak, isi total rupiah; tulis 0 jika tidak dikenakan. Terima kasih 🙏')
    call('wa_enqueue',c['id'],'followup',text,{'request_key':key,'missing_fields':missing})
