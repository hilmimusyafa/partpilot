"""Independent review regressions. Never connect to or send through WhatsApp."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import uuid

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_whatsapp import wa  # noqa: F401 -- explicitly owned PostgreSQL fixture


@pytest.mark.parametrize('field,text', [
    ('shipping_amount', 'ongkir 25rb per pcs'),
    ('shipping_amount', 'pengiriman 10000/kg'),
    ('tax_amount', 'pajak 11 persen'),
    ('tax_amount', 'PPN 11%'),
])
def test_review_percentage_and_per_unit_costs_remain_unknown(field, text):
    from backend.whatsapp.extraction import validate_extraction
    result = validate_extraction({'fields': {field: {'raw': text}}}, text,
                                 datetime.now(timezone.utc))
    assert field not in result['fields']


def complete_fields(identity):
    now = datetime.now(timezone.utc)
    return dict(identity=identity, qty_available='20', unit_price='150000',
                shipping_amount='25000', tax_amount='0', processing_hours='2',
                delivered_eta=(now + timedelta(hours=4)).isoformat(),
                valid_until=(now + timedelta(hours=23)).isoformat())


def test_review_irrelevant_reply_does_not_publish_revised_quote(monkeypatch):
    from backend.whatsapp import worker
    now = datetime.now(timezone.utc)
    identity = dict(brand='NTN', base='6200', suffix='LLU')
    conversation = dict(id='review-c', version=5, status='quoted',
                        fields=complete_fields(identity),
                        snapshot=dict(identity=identity, quantity='9',
                                      requested_at=now.isoformat(),
                                      destination_warehouse_id='SYN-WH-02'))
    pending = [dict(id='review-in', body='Sebentar ya saya cek',
                    created_at=now - timedelta(seconds=10),
                    received_at=now - timedelta(seconds=10))]

    def query(sql, args=()):
        if "status='received'" in sql:
            return pending
        if "kind='price_counteroffer'" in sql:
            return [dict(status='sent', delivered_at=now - timedelta(minutes=1))]
        raise AssertionError('Unexpected query in isolated worker test: ' + sql)

    applied = []
    def call(name, *args):
        if name == 'wa_parse_attempt':
            return True
        applied.append((name, *args))
        return False
    monkeypatch.setattr(worker, 'query', query)
    monkeypatch.setattr(worker, 'extract', lambda *args: dict(fields={}, evidence={}, outcome=None))
    monkeypatch.setattr(worker, 'call', call)
    worker.process_conversation(conversation)
    assert len(applied) == 1
    assert applied[0][0] == 'wa_apply'
    assert applied[0][5] is None, 'An acknowledgement is not a revised vendor quote'


def arrange_quoted_conversation(cluster):
    from test_procurement import start
    from backend.whatsapp.repository import call
    from backend.whatsapp.service import quote
    run = start(cluster)
    conversation = call('wa_start', run['id'], 'WA-DEMO-1')
    rfq = call('wa_enqueue', conversation['id'], 'rfq', 'Owned review RFQ', {})
    call('wa_delivery', rfq['id'], 'sending', None)
    call('wa_delivery', rfq['id'], 'sent', 'review-rfq-' + uuid.uuid4().hex)
    mid = call('wa_inbound', 'review-in-' + uuid.uuid4().hex, '628123456789',
               'Owned fixture complete vendor quote', datetime.now(timezone.utc))
    conversation = cluster.sql('SELECT * FROM pp.wa_conversation WHERE id=%s',
                               (conversation['id'],))[0]
    fields = complete_fields(conversation['snapshot']['identity'])
    published = quote(conversation, fields)
    assert published is not None
    assert call('wa_apply', conversation['id'], conversation['version'], fields,
                'quoted', published, [mid])
    return run['id'], conversation['id'], fields


def compare_real_quote(cluster, run_id):
    from test_procurement import comparison_input
    from backend.procurement.service import get_run
    from backend.procurement.models import CompareInput
    from backend.procurement.comparison import create_comparison
    run = get_run(run_id)
    payload = comparison_input(run)
    option = deepcopy(payload['options'][0])
    option['source_id'] = 'WA-DEMO-1'
    payload['options'] = [option]
    comparison = create_comparison(run_id, CompareInput.model_validate(payload), uuid.uuid4().hex)
    assert 'vendor:WA-DEMO-1' in [o['option_id'] for o in comparison['eligible_complete_options']]
    return comparison


def test_review_complete_utc_quote_can_be_compared_and_selected(wa):
    run_id, _, _ = arrange_quoted_conversation(wa)
    comparison = compare_real_quote(wa, run_id)
    result = wa.sql('SELECT pp.demo_choose(%s,1,%s,%s) result',
                    (comparison['id'], 'vendor:WA-DEMO-1', uuid.uuid4().hex))[0]['result']
    assert result['procurement_executed'] is False

def test_counteroffer_and_followup_budgets_are_database_enforced(wa):
    from backend.whatsapp.repository import call
    from concurrent.futures import ThreadPoolExecutor
    _,cid,_=arrange_quoted_conversation(wa)
    def reserve(_):return call('wa_enqueue',cid,'price_counteroffer','one counter',{'target_unit_price':'142500'})
    with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(reserve,range(3)))
    assert len({r['id'] for r in rows})==1
    with pytest.raises(Exception):call('wa_enqueue',cid,'price_counteroffer','another counter',{'target_unit_price':'140000'})
    for i in range(3):call('wa_enqueue',cid,'followup','question '+str(i),{'request_key':str(i),'missing_fields':['unit_price']})
    with pytest.raises(Exception):call('wa_enqueue',cid,'followup','fourth question',{'request_key':'fourth','missing_fields':['unit_price']})
    assert wa.sql("SELECT count(*) n FROM pp.wa_message WHERE conversation_id=%s AND kind='price_counteroffer'",(cid,))[0]['n']==1


@pytest.mark.parametrize('new_status', ['no_stock', 'needs_review'])
def test_review_changed_vendor_status_rejects_old_comparison(wa, new_status):
    from backend.whatsapp.repository import call
    run_id, conversation_id, fields = arrange_quoted_conversation(wa)
    comparison = compare_real_quote(wa, run_id)
    # Preserve the earlier RFQ object while the new counter response can be null.
    if new_status == 'no_stock':
        counter = call('wa_enqueue', conversation_id, 'price_counteroffer', 'Owned review counter',
                       {'target_unit_price': '142500'})
        call('wa_delivery', counter['id'], 'sending', None)
        call('wa_delivery', counter['id'], 'sent', 'review-counter-' + uuid.uuid4().hex)
    mid = call('wa_inbound', 'review-change-' + uuid.uuid4().hex, '628123456789',
               'stok habis' if new_status == 'no_stock' else 'Ternyata mereknya SKF',
               datetime.now(timezone.utc))
    conversation = wa.sql('SELECT * FROM pp.wa_conversation WHERE id=%s', (conversation_id,))[0]
    changed = deepcopy(fields)
    if new_status == 'no_stock':
        changed['qty_available'] = '0'
    else:
        changed['identity']['brand'] = 'SKF'
    assert call('wa_apply', conversation_id, conversation['version'], changed, new_status, None, [mid])
    with pytest.raises(Exception, match='quote_changed'):
        wa.sql('SELECT pp.demo_choose(%s,1,%s,%s)',
               (comparison['id'], 'vendor:WA-DEMO-1', uuid.uuid4().hex))
    assert wa.sql('SELECT * FROM pp.demo_decision') == []
