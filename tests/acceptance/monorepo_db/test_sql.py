import json
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ROWS = json.loads((HERE / "expected.json").read_text())
SEED = ROOT / "backend/db/seed/009_bearing_mvp_synth.sql"

def snapshot(db):
    return {table: db.execute(f"SELECT to_jsonb(t) FROM erp.{table} t ORDER BY to_jsonb(t)::text").fetchall()
            for table in ("company", "warehouse", "item_group", "item", "bin")}

@pytest.mark.parametrize("row", ROWS, ids=[r["code"] for r in ROWS])
def test_M04_exact_eight_readback(db, row):
    actual = db.execute("""SELECT i.item_name,i.item_group,i.stock_uom,i.brand,i.description,
        i.disabled,i.is_stock_item,b.warehouse,b.actual_qty,b.reserved_qty,w.company,
        w.is_group,w.disabled FROM erp.item i JOIN erp.bin b USING(item_code)
        JOIN erp.warehouse w ON w.name=b.warehouse WHERE i.item_code=%s""", (row["code"],)).fetchall()
    assert actual == [(row["name"], "Bearing", "Nos", "NTN", row["description"],
                       False, True, row["warehouse"], row["qty"], 0, "SYN-COMPANY-01", False, False)]
    lookup = db.execute("SELECT * FROM pp.lookup_bearing_exact(%s,%s,%s,%s)",
                        ("SYN-COMPANY-01", "Bearing", row["warehouse"], row["name"])).fetchall()
    assert lookup == [(row["code"],row["name"],row["description"],row["warehouse"],row["qty"],0,row["qty"])]

def test_M05_counts_and_replay(db):
    assert [db.execute(f"SELECT count(*) FROM erp.{t}").fetchone()[0]
            for t in ("company", "warehouse", "item_group", "item", "bin")] == [1,5,1,8,8]
    assert db.execute("SELECT name,company,is_group,disabled,parent_warehouse FROM erp.warehouse ORDER BY name").fetchall() == [
        (f"SYN-WH-0{i}","SYN-COMPANY-01",False,False,None) for i in range(1,6)]
    before = snapshot(db)
    db.execute(SEED.read_text())
    db.execute(SEED.read_text())
    assert snapshot(db) == before

@pytest.mark.parametrize("statement", [
    "UPDATE erp.company SET default_currency='USD'",
    "UPDATE erp.warehouse SET disabled=true WHERE name='SYN-WH-02'",
    "UPDATE erp.item_group SET is_group=true WHERE name='Bearing'",
    "UPDATE erp.item SET item_name='CONFLICT' WHERE item_code='G2-BRG-017'",
    "UPDATE erp.item SET description='CONFLICT' WHERE item_code='G2-BRG-018'",
    "UPDATE erp.bin SET actual_qty=99 WHERE item_code='G2-BRG-019'",
    "UPDATE erp.bin SET reserved_qty=1 WHERE item_code='SYN-WH01-NTN-6200LLU'",
], ids=["company","warehouse","category","name","description","stock","reserved"])
def test_M06_conflict_rejects_without_overwrite(db, statement):
    import psycopg
    db.execute(statement)
    before = snapshot(db)
    db.execute("SAVEPOINT seed_conflict")
    try:
        with pytest.raises(psycopg.Error):
            db.execute(SEED.read_text())
    finally:
        db.execute("ROLLBACK TO SAVEPOINT seed_conflict")
        db.execute("RELEASE SAVEPOINT seed_conflict")
    assert snapshot(db) == before

@pytest.mark.parametrize("scope", [
    ("OTHER", "Bearing", "SYN-WH-02", ROWS[5]["name"]),
    ("SYN-COMPANY-01", "OTHER", "SYN-WH-02", ROWS[5]["name"]),
    ("SYN-COMPANY-01", "Bearing", "SYN-WH-01", ROWS[5]["name"]),
    ("SYN-COMPANY-01", "Bearing", "SYN-WH-03", ROWS[0]["name"]),
    ("SYN-COMPANY-01", "Bearing", "SYN-WH-02", "NTN 6200LLU"),
    ("SYN-COMPANY-01", "Bearing", "SYN-WH-01", "ntn 6200llu"),
], ids=["company","category","warehouse","emptyWH03","no_label_alias","case_exact"])
def test_M07_scoped_lookup(db, scope):
    assert db.execute("SELECT * FROM pp.lookup_bearing_exact(%s,%s,%s,%s)", scope).fetchall() == []

def test_M08_indexes_and_schema_preserved(db):
    indexes = dict(db.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='erp'").fetchall())
    assert '(item_group, item_name, item_code)' in indexes['pp_bearing_item_group_name_code_idx']
    assert '(warehouse, item_code)' in indexes['pp_bearing_bin_warehouse_item_idx']
    assert db.execute("SELECT provolatile,prosecdef FROM pg_proc WHERE oid='pp.lookup_bearing_exact(text,text,text,text)'::regprocedure").fetchone() == ('s',False)
    # Runner captures baseline schema before seed; no extra columns allowed.
    expected = db.execute("SELECT current_setting('acceptance.columns_before')").fetchone()[0]
    actual = db.execute("SELECT json_agg(row(table_schema,table_name,column_name,data_type) ORDER BY table_schema,table_name,ordinal_position)::text FROM information_schema.columns WHERE table_schema IN ('erp','pp','midea')").fetchone()[0]
    assert actual == expected
