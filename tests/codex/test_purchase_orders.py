"""Owned database approval, immutable snapshot and offline PDF regressions."""
import sys
from decimal import Decimal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def po_demo(monkeypatch):
    from isolated import Cluster
    from backend.demo.bootstrap import install_demo
    from fastapi.testclient import TestClient
    c = Cluster()
    monkeypatch.setenv('DATABASE_URL', c.dsn)
    monkeypatch.setenv('TEST_DATABASE_URL', c.dsn)
    monkeypatch.setenv('PARTPILOT_DEMO_PASSWORD', 'test-only-secret')
    try:
        with c.connection() as conn:
            conn.execute("DELETE FROM erp.company WHERE name LIKE 'foreign-%'")
            install_demo(conn, allow_test_database=True)
            for prefix, table in [('014', 'wa_recipient'), ('015', 'demo_purchase_order'), ('016', 'demo_negotiation_round')]:
                if not conn.execute('SELECT to_regclass(%s) AS found', ('pp.'+table,)).fetchone()['found']:
                    for migration in sorted((ROOT/'backend/db').glob(prefix+'*.sql')):
                        conn.execute(migration.read_text(), prepare=False)
        from backend.demo.app import app
        with TestClient(app) as client:
            client.auth = ('demo', 'test-only-secret')
            client.headers.update({'X-PartPilot-Request':'demo','X-PartPilot-Generation':'1'})
            yield c, client
    finally:
        c.close()


def prepared(c, client, **kwargs):
    from test_procurement import start, advance
    run = advance(c, start(c, **kwargs))
    response = client.post(f"/api/v1/demo/sourcing-runs/{run['id']}/prepare-comparison", json={},
                           headers={'Idempotency-Key':'po-compare'})
    assert response.status_code == 201, response.text
    return run, response.json()


def choose(client, comparison, kind='vendor', key='po-choice'):
    option = next(o for o in comparison['eligible_complete_options'] if o['source_kind']==kind)
    response = client.post(f"/api/v1/demo/comparisons/{comparison['id']}/decision",
                           json={'expected_version':1,'option_id':option['option_id'],'acknowledgment':'demo_only'},
                           headers={'Idempotency-Key':key})
    assert response.status_code == 201, response.text
    return option, response.json()


def test_vendor_approval_atomic_exact_snapshot_and_retry(po_demo):
    c, client = po_demo
    run, comparison = prepared(c, client)
    url = f"/api/v1/demo/sourcing-runs/{run['id']}/purchase-order"
    assert client.get(url).json() == {'purchase_order':None}
    before = c.sql('SELECT count(*) n FROM pp.demo_outbox')[0]['n']
    option, decision = choose(client, comparison)
    po = client.get(url).json()['purchase_order']
    assert po['decision_id']==decision['id'] and po['identity']==option['quote']['identity']
    assert Decimal(po['line_subtotal'])==Decimal(option['quantity'])*Decimal(option['quote']['unit_price'])
    assert Decimal(po['total'])==sum(Decimal(po[k]) for k in ['line_subtotal','shipping_amount','tax_amount'])
    assert Decimal(po['total'])<Decimal(option['economics']['future_relevant_option_total_unrounded'])
    assert po['procurement_executed'] is False
    assert not any(word in str(po).lower() for word in ['downtime','recovery','contribution'])
    with ThreadPoolExecutor(max_workers=3) as pool:
        repeated = list(pool.map(lambda _: choose(client, comparison)[1], range(3)))
    assert all(d==decision for d in repeated)
    assert len(c.sql('SELECT * FROM pp.demo_purchase_order'))==1
    assert c.sql('SELECT count(*) n FROM pp.demo_outbox')[0]['n']==before
    assert client.get(url).json()['purchase_order']==po


def test_warehouse_selection_never_generates_po(po_demo):
    c, client = po_demo
    run, comparison = prepared(c, client, qty='6', origin='SYN-WH-01', code='SYN-WH01-NTN-6200LLU')
    choose(client, comparison, 'warehouse')
    assert client.get(f"/api/v1/demo/sourcing-runs/{run['id']}/purchase-order").json()=={'purchase_order':None}
    assert not c.sql('SELECT * FROM pp.demo_purchase_order')


def test_po_pdf_auth_immutability_and_reset_retention(po_demo):
    c, client = po_demo
    run, comparison = prepared(c, client)
    choose(client, comparison)
    po = client.get(f"/api/v1/demo/sourcing-runs/{run['id']}/purchase-order").json()['purchase_order']
    pdf = client.get(po['pdf_url'])
    assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
    assert client.get(po['pdf_url'],auth=('demo','wrong')).status_code==401
    assert client.get('/api/v1/demo/purchase-orders/missing/pdf').status_code==404
    for statement in ['UPDATE pp.demo_purchase_order SET snapshot=\'{}\'::jsonb',
                      'DELETE FROM pp.demo_purchase_order','TRUNCATE pp.demo_purchase_order']:
        with pytest.raises(Exception,match='immutable'):
            c.sql(statement)
    reset = client.post('/api/v1/demo/reset',json={'confirmation':'RESET DEMO','expected_generation':1},
                        headers={'Idempotency-Key':'po-reset'})
    assert reset.status_code==200,reset.text
    assert client.get(po['pdf_url']).content==pdf.content
    assert client.get(f"/api/v1/demo/sourcing-runs/{run['id']}/purchase-order").json()['purchase_order']==po
    archived = c.sql('SELECT archived_workflow FROM pp.demo_reset_audit')[0]['archived_workflow']
    assert any(a['event_type']=='purchase_order_generated' for a in archived['audit'])
    assert archived['decisions'][0]['id']==po['decision_id']


def test_invalid_quote_cannot_leave_decision_or_po(po_demo):
    c,client = po_demo
    run,comparison = prepared(c,client)
    option = next(o for o in comparison['eligible_complete_options'] if o['source_kind']=='vendor')
    c.sql("UPDATE pp.demo_outbox SET response=jsonb_set(response,'{quote,unit_price}','\"999999\"'::jsonb) WHERE run_id=%s AND vendor_id=%s",(run['id'],option['source_id']))
    result = client.post(f"/api/v1/demo/comparisons/{comparison['id']}/decision",json={
        'expected_version':1,'option_id':option['option_id'],'acknowledgment':'demo_only'},headers={'Idempotency-Key':'stale-po'})
    assert result.status_code==409
    assert not c.sql('SELECT * FROM pp.demo_decision')
    assert not c.sql('SELECT * FROM pp.demo_purchase_order')


def test_po_api_role_cannot_write_or_generate(po_demo):
    c,_ = po_demo
    c.sql('CREATE ROLE po_read_test NOLOGIN')
    c.sql('GRANT USAGE ON SCHEMA pp TO po_read_test')
    c.sql('GRANT SELECT ON pp.demo_purchase_order TO po_read_test')
    permissions=c.sql("SELECT has_table_privilege('po_read_test','pp.demo_purchase_order','SELECT') AS read, has_table_privilege('po_read_test','pp.demo_purchase_order','INSERT,UPDATE,DELETE,TRUNCATE') AS write,has_function_privilege('po_read_test','pp.demo_create_purchase_order()','EXECUTE') AS generate")[0]
    assert permissions=={'read':True,'write':False,'generate':False}


def test_po_trigger_failure_rolls_back_manager_decision(po_demo):
    from copy import deepcopy
    from psycopg.types.json import Jsonb
    c, client = po_demo
    run, comparison = prepared(c, client)
    snapshot = deepcopy(c.sql('SELECT snapshot FROM pp.demo_comparison WHERE id=%s', (comparison['id'],))[0]['snapshot'])
    option = next(o for o in snapshot['eligible_complete_options'] if o['source_kind']=='vendor')
    option['quote']['shipping_amount']='-1'
    # Owned-owner fixture simulates corrupt stored quote; runtime has no direct
    # write privileges. The PO trigger must reject and roll back the decision.
    c.sql("UPDATE pp.demo_outbox SET response=jsonb_set(response,'{quote}',%s) WHERE run_id=%s AND vendor_id=%s AND response->'quote' IS NOT NULL",
          (Jsonb(option['quote']),run['id'],option['source_id']))
    snapshot['eligible_complete_options']=[option]
    cid=c.sql("INSERT INTO pp.demo_comparison(run_id,request_key,request,snapshot) VALUES(%s,'corrupt-po-fixture','{}',%s) RETURNING id",
              (run['id'],Jsonb(snapshot)))[0]['id']
    with pytest.raises(Exception,match='invalid_comparison'):
        c.sql('SELECT pp.demo_choose(%s,1,%s,%s)',(cid,option['option_id'],'corrupt-po-choice'))
    assert not c.sql('SELECT * FROM pp.demo_decision')
    assert not c.sql('SELECT * FROM pp.demo_purchase_order')


def sample_order():
    return dict(number='PO-DEMO-20261022-ABCDEF123456',created_at='2026-10-22T04:05:00+00:00',
        issuer=dict(name='PT PartPilot',address='Jl. Contoh Industri No. 123, Cikarang - ALAMAT DUMMY',
                    email='purchasing@partpilot.example',phone='Nomor telepon dummy: 000-0000-0000'),
        supplier=dict(id='SIM-REVISE',name='SIM-REVISE',address='Alamat pemasok belum diberikan (dummy untuk demo)'),
        ship_to=dict(name='PT PartPilot - Gudang Penerima',warehouse_id='SYN-WH-01',
                     address='Jl. Contoh Gudang No. 45, Cikarang - ALAMAT DUMMY'),
        identity=dict(brand='NTN',base='6200',suffix='LLU'),quantity='6',quantity_unit='Nos',
        unit_price='130000.01',line_subtotal='780000.06',shipping_amount='25000',tax_amount='88550.01',total='893550.07',
        quote_id='00000000-0000-0000-0000-000000000000:SIM-REVISE',quote_revision=2,
        delivered_eta='2026-10-22T12:00:00+07:00',approval=dict(approved_at='2026-10-22T04:05:00+00:00'),
        terms=['Dokumen simulasi; tidak dikirim kepada pemasok dan bukan pesanan pembelian nyata.',
               'Pembayaran: NET 30 hari (ketentuan dummy untuk demo).',
               'Pengiriman: sesuai estimasi penawaran; alamat dan kontak perusahaan adalah dummy.',
               'Pajak mengikuti nominal penawaran; dokumen ini bukan faktur pajak.'])


def test_pdf_repeatable_currency_and_escaped_supplier():
    from backend.purchase_orders.pdf import render_pdf,idr
    assert idr('893550.07')=='Rp 893.550,07'
    assert idr('12.345')=='Rp 12,345'
    order=sample_order()
    pdf=render_pdf(order)
    assert pdf.startswith(b'%PDF-') and pdf==render_pdf(order)
    order['supplier']['name']='Vendor <b>tidak tepercaya</b> & rekan'
    assert render_pdf(order).startswith(b'%PDF-')
