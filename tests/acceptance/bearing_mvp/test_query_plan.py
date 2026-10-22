import json
from conftest import COMPANY,WH,NAMES

def test_B09_function(db):
    rows=db.execute("SELECT p.provolatile,p.prosecdef,p.pronargdefaults,l.lanname,pg_get_functiondef(p.oid) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang WHERE n.nspname='pp' AND p.proname='lookup_bearing_exact'").fetchall()
    assert len(rows)==1
    volatility,definer,defaults,language,source=rows[0]
    assert (volatility,definer,defaults,language)==('s',False,0,'sql')
    for forbidden in ['match_text','item_keys','match_candidates','norm_key','ilike','similarity','embedding']:
        assert forbidden not in source.lower()
    assert db.execute("SELECT to_regprocedure('pp.lookup_bearing_exact(text,text,text,text)') IS NOT NULL").fetchone()[0]

def test_B09_indexes(db):
    rows=dict(db.execute("SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='erp'").fetchall())
    assert '(item_group, item_name, item_code)' in rows['pp_bearing_item_group_name_code_idx']
    assert '(warehouse, item_code)' in rows['pp_bearing_bin_warehouse_item_idx']

def explain(db,label):
    plan=db.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT * FROM pp.lookup_bearing_exact(%s,%s,%s,%s)',(COMPANY,'Bearing',WH,NAMES[0])).fetchone()[0]
    print('BEARING_PLAN',label,json.dumps(plan,default=str,sort_keys=True))
    assert plan[0]['Plan']['Actual Rows']==1
    assert 'Execution Time' in plan[0]
    # Tiny sequential scans are valid; no fabricated performance threshold.

def test_B09_plan_tiny(db):
    db.execute('ANALYZE erp.item'); db.execute('ANALYZE erp.bin')
    explain(db,'tiny:5 items/5 bins')

def test_B09_plan_large(db):
    db.execute("INSERT INTO erp.item_group(name) VALUES ('SYN-OTHER')")
    db.execute("INSERT INTO erp.item(item_code,item_name,item_group,stock_uom) SELECT 'SYN-LOAD-'||n,'SYN-LOAD-'||n,'SYN-OTHER','Nos' FROM generate_series(1,10000) n")
    db.execute("INSERT INTO erp.bin(item_code,warehouse,actual_qty) SELECT item_code,%s,10 FROM erp.item WHERE item_group='SYN-OTHER'",(WH,))
    db.execute('ANALYZE erp.item'); db.execute('ANALYZE erp.bin')
    explain(db,'large:10005 items/bins;10000 other-category;5 Bearing;WH01')
