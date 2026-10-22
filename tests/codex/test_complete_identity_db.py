"""Database boundary rejects forged complete-unit runs and PO identities."""
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

sys.path.insert(0, str(Path(__file__).parent))
from isolated import Cluster
from test_complete_identity import CR, LP99

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def complete_db():
    c = Cluster()
    try:
        with c.connection() as conn:
            for filename in ('012_procurement_demo.sql', '015_purchase_orders.sql', '021_complete_part_identity.sql'):
                path = ROOT / 'backend/db' / filename
                if path.exists():
                    conn.execute(path.read_text(), prepare=False)
            conn.execute("INSERT INTO erp.item(item_code,item_name,brand,item_group,stock_uom,is_stock_item) VALUES ('TEST-RHP-CR','RHP PSF20CR','RHP','Bearing','Nos',true)")
            conn.execute("INSERT INTO erp.bin(item_code,warehouse,actual_qty,reserved_qty) VALUES ('TEST-RHP-CR','SYN-WH-01',0,0)")
        yield c
    finally:
        c.close()


def run_snapshot(c, identity):
    draft = c.draft(description='bearing RHP PSF20CR', quantity='1')
    candidate = c.sql("SELECT item_code,item_name,brand,description FROM erp.item WHERE item_code='TEST-RHP-CR'")[0]
    c.sql("UPDATE pp.wo_identification_session SET state='identified',version=2,result=%s WHERE id=%s",
          (Jsonb({'identified_candidate': candidate}), draft['id']))
    snapshot = {'status': 'sourcing', 'identity': identity, 'quantity': '1',
                'destination_warehouse_id': 'SYN-WH-01', 'requested_at': '2026-10-23T00:00:00Z',
                'expires_at': '2026-10-24T00:00:00Z'}
    return draft['id'], snapshot


def test_database_allows_exact_complete_unit_with_zero_stock(complete_db, monkeypatch):
    c = complete_db
    monkeypatch.setenv('TEST_DATABASE_URL', c.dsn)
    monkeypatch.setenv('DATABASE_URL', c.dsn)
    from backend.wo.repository import get_scoped_candidates
    rows, truncated = get_scoped_candidates('SYN-COMPANY-01', 'SYN-WH-01', item_code='TEST-RHP-CR')
    assert not truncated and rows[0]['item_code'] == 'TEST-RHP-CR'
    assert float(rows[0]['available_qty']) == 0
    sid, snapshot = run_snapshot(c, CR)
    row = c.sql('SELECT pp.demo_start(%s,2,%s,%s) id', (sid, uuid.uuid4().hex, Jsonb(snapshot)))
    assert row[0]['id']
    assert c.sql('SELECT snapshot FROM pp.demo_run WHERE id=%s', (row[0]['id'],))[0]['snapshot']['identity'] == CR


@pytest.mark.parametrize('identity', [LP99, {k: CR[k] for k in ('brand', 'base', 'suffix')},
                                     {**CR, 'full_designation': 'PSF20CR/C3'},
                                     {**CR, 'unit_scope': 'bearing_insert'}])
def test_database_rejects_upgrade_or_incomplete_identity_in_original_run(complete_db, identity):
    c = complete_db
    sid, snapshot = run_snapshot(c, identity)
    with pytest.raises(psycopg.Error):
        c.sql('SELECT pp.demo_start(%s,2,%s,%s)', (sid, uuid.uuid4().hex, Jsonb(snapshot)))
    assert c.sql('SELECT count(*) n FROM pp.demo_run')[0]['n'] == 0


def test_purchase_order_storage_rejects_insert_scope_for_complete_unit(complete_db):
    c = complete_db
    invalid = {'identity': {**CR, 'unit_scope': 'bearing_insert'}}
    with pytest.raises(psycopg.Error):
        c.sql("INSERT INTO pp.demo_purchase_order(number,decision_id,run_id,created_at,snapshot) VALUES ('PO-BAD','D-BAD','R-BAD',now(),%s)", (Jsonb(invalid),))
    assert c.sql('SELECT count(*) n FROM pp.demo_purchase_order')[0]['n'] == 0
