"""Five warehouse fixture upgrades against owned PostgreSQL, never the live demo."""
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from isolated import Cluster

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / 'backend/db/017_five_warehouse_demo.sql'
IDENTITY = dict(brand='NTN', base='6200', suffix='LLU')


@pytest.mark.parametrize('warehouse', ['SYN-WH-03', 'SYN-WH-04', 'SYN-WH-05'])
def test_new_warehouse_notes_are_explicitly_scoped_simulations(warehouse):
    from backend.wo.knowledge import load_scoped_note
    note = load_scoped_note(warehouse)
    assert note['status'] == 'available'
    assert note['frontmatter']['warehouse'] == warehouse
    assert note['frontmatter']['company'] == 'SYN-COMPANY-01'
    assert note['frontmatter']['simulated'] is True
    assert 'MANUFACTURER-UNVERIFIED' in note['source_status']
    assert load_scoped_note('SYN-WH-99')['status'] == 'knowledge_unavailable'


@pytest.fixture
def legacy_demo(monkeypatch):
    db = Cluster()
    monkeypatch.setenv('TEST_DATABASE_URL', db.dsn)
    monkeypatch.setenv('DATABASE_URL', db.dsn)
    try:
        with db.connection() as conn:
            conn.execute("DELETE FROM erp.company WHERE name LIKE 'foreign-%'")
            for name in ['012_procurement_demo.sql', '013_demo_console.sql', '014_whatsapp.sql',
                         '015_purchase_orders.sql', '016_negotiation_policy.sql']:
                conn.execute((ROOT/'backend/db'/name).read_text(), prepare=False)
            conn.execute("UPDATE erp.bin SET reserved_qty=6 WHERE item_code='SYN-WH01-NTN-6200LLU'")
            conn.execute("INSERT INTO pp.demo_control(dataset_tag,reset_enabled,stock_baseline) SELECT 'synthetic-bearing-demo-v1',true,jsonb_agg(to_jsonb(b)) FROM erp.bin b")
        yield db
    finally:
        db.close()


def apply_upgrade(db):
    with db.connection() as conn:
        conn.execute(MIGRATION.read_text(), prepare=False)


def test_upgrade_preserves_existing_work_and_uses_five_real_scoped_catalogs(legacy_demo):
    from test_procurement import start
    from backend.wo.availability import evaluate_scope
    from backend.demo.console import config
    db = legacy_demo
    run = start(db, qty='6', origin='SYN-WH-01', code='SYN-WH01-NTN-6200LLU')
    db.sql("INSERT INTO pp.wa_recipient(id,phone,label,destination) VALUES('WA-DEMO-1','620000000000','Owned test only','DUMMY')")
    db.sql("INSERT INTO pp.wa_message(vendor_id,direction,kind,body,status) VALUES('WA-DEMO-1','in','reply','Existing owned test message','received')")
    db.sql("INSERT INTO pp.demo_purchase_order(number,decision_id,run_id,created_at,snapshot) VALUES('TEST-EXISTING','old-decision','old-run',now(),'{\"fixture\":true}')")
    preserved = {table: db.sql(f'SELECT * FROM pp.{table}') for table in
                 ('demo_run', 'wo_identification_session', 'wa_message', 'demo_purchase_order')}
    baseline = db.sql('SELECT stock_baseline FROM pp.demo_control')[0]['stock_baseline']
    stock_before = db.sql('SELECT * FROM erp.bin ORDER BY item_code')
    apply_upgrade(db)
    assert all(db.sql(f'SELECT * FROM pp.{table}') == rows for table, rows in preserved.items())
    assert all(row in db.sql('SELECT * FROM erp.bin ORDER BY item_code') for row in stock_before)
    after_baseline = db.sql('SELECT stock_baseline FROM pp.demo_control')[0]['stock_baseline']
    assert all(row in after_baseline for row in baseline) and len(after_baseline) == len(baseline) + 3
    expected = [('SYN-WH-01', '4'), ('SYN-WH-02', '8'), ('SYN-WH-03', '2'), ('SYN-WH-04', '3'), ('SYN-WH-05', '1')]
    scopes = [evaluate_scope(w, Decimal('6'), IDENTITY) for w, _ in expected]
    assert [Decimal(s.available_qty) for s in scopes] == [Decimal(q) for _, q in expected]
    assert [s.status for s in scopes] == ['insufficient', 'sufficient', 'insufficient', 'insufficient', 'insufficient']
    assert len({s.item_code for s in scopes}) == 5
    assert all(s.knowledge_refs and s.evidence for s in scopes)
    from backend.wo.matching import extract_facts_from_text, match_candidates
    from backend.wo.repository import get_scoped_candidates
    description = 'bearing NTN 10x30x9 mm karet rapat dua sisi'
    for scope in scopes:
        rows, truncated = get_scoped_candidates('SYN-COMPANY-01', scope.warehouse_id, 'Bearing')
        matched = match_candidates(rows, extract_facts_from_text(description),
                                   truncated=truncated, input_text=description)
        assert matched['state'] == 'identified'
        assert matched['identified_candidate']['item_code'] == scope.item_code
    assert evaluate_scope('SYN-WH-99', Decimal('6'), IDENTITY).status == 'knowledge_unavailable'
    warehouses = config()['warehouses']
    assert [w['id'] for w in warehouses] == [w for w, _ in expected]
    assert all(w['simulated'] is True and 'DUMMY' in w['address'] and w['name'] for w in warehouses)
    # The response must read the database rather than another hardcoded list.
    db.sql("UPDATE pp.demo_warehouse_display SET name='Nama tampilan uji' WHERE warehouse_id='SYN-WH-03'")
    assert config()['warehouses'][2]['name'] == 'Nama tampilan uji'
    assert db.sql('SELECT id FROM pp.demo_run')[0]['id'] == run['id']


def test_upgrade_replay_preserves_live_stock_and_reset_restores_all_five_baselines(legacy_demo):
    db = legacy_demo
    apply_upgrade(db)
    expected = db.sql('SELECT item_code,warehouse,actual_qty,reserved_qty FROM erp.bin ORDER BY item_code')
    db.sql("UPDATE erp.bin SET actual_qty=1 WHERE warehouse='SYN-WH-03'")
    db.sql("UPDATE erp.bin SET reserved_qty=1 WHERE warehouse='SYN-WH-04'")
    apply_upgrade(db)
    assert db.sql("SELECT actual_qty FROM erp.bin WHERE warehouse='SYN-WH-03'")[0]['actual_qty'] == 1
    assert db.sql("SELECT reserved_qty FROM erp.bin WHERE warehouse='SYN-WH-04'")[0]['reserved_qty'] == 1
    assert len(db.sql('SELECT * FROM pp.demo_warehouse_display')) == 5
    assert len(db.sql('SELECT * FROM erp.bin')) == 11
    db.sql("SELECT pp.demo_reset(1,'five-wh-reset','RESET DEMO')")
    assert db.sql('SELECT item_code,warehouse,actual_qty,reserved_qty FROM erp.bin ORDER BY item_code') == expected


def test_upgrade_refuses_non_demo_company_without_partial_fixture_changes(legacy_demo):
    db = legacy_demo
    db.sql("INSERT INTO erp.company(name,default_currency) VALUES('REAL-COMPANY','IDR')")
    with pytest.raises(Exception, match='five_warehouse_demo_scope_required'):
        apply_upgrade(db)
    assert len(db.sql('SELECT * FROM erp.item')) == 8
    assert db.sql("SELECT to_regclass('pp.demo_warehouse_display') AS name")[0]['name'] is None


def test_fresh_installer_initializes_all_five_scopes_and_reset_baselines(monkeypatch):
    from backend.demo.bootstrap import install_demo
    from backend.wo.availability import evaluate_scope
    db = Cluster()
    monkeypatch.setenv('TEST_DATABASE_URL', db.dsn)
    try:
        with db.connection() as conn:
            conn.execute("DELETE FROM erp.company WHERE name LIKE 'foreign-%'")
            install_demo(conn, allow_test_database=True)
        assert len(db.sql('SELECT * FROM erp.bin')) == 11
        assert len(db.sql('SELECT stock_baseline FROM pp.demo_control')[0]['stock_baseline']) == 11
        for warehouse in ('SYN-WH-03', 'SYN-WH-04', 'SYN-WH-05'):
            assert evaluate_scope(warehouse, Decimal('6'), IDENTITY).status == 'insufficient'
    finally:
        db.close()
