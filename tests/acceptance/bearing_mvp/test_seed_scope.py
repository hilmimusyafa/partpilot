from conftest import COMPANY, WH, NAMES, DIMS

def test_B01_seed_shape(db):
    assert db.execute('SELECT name FROM erp.company ORDER BY name').fetchall()==[(COMPANY,)]
    assert db.execute('SELECT name,company,is_group,disabled,parent_warehouse FROM erp.warehouse ORDER BY name').fetchall()==[(f'SYN-WH-{i:02}',COMPANY,False,False,None) for i in range(1,6)]
    assert db.execute('SELECT warehouse,count(*) FROM erp.bin GROUP BY warehouse').fetchall()==[(WH,5)]
    assert db.execute('SELECT count(*) FROM erp.item').fetchone()[0]==5

def test_B02_names_specs(db):
    rows=db.execute('SELECT item_name,item_code,description,stock_uom FROM erp.item').fetchall()
    assert {r[0] for r in rows}==set(NAMES)
    dimensions=dict(zip(NAMES,DIMS))
    for name,code,description,uom in rows:
        assert code=='SYN-WH01-'+name.replace(' ','-')
        assert description.startswith('USER-PROVIDED; MANUFACTURER-UNVERIFIED')
        assert dimensions[name] in description
        assert name.split()[-1][4:] in description
        assert uom=='Nos'
    assert db.execute('SELECT DISTINCT actual_qty,reserved_qty FROM erp.bin').fetchall()==[(10,0)]

def test_B02_existing_columns(db):
    rows=db.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='erp' AND table_name='item' ORDER BY ordinal_position").fetchall()
    assert [r[0] for r in rows]==['item_code','item_name','item_group','stock_uom','is_stock_item','disabled','allow_alternative_item','safety_stock','min_order_qty','lead_time_days','brand','description']

def test_B11_unrelated_seed_empty(db):
    for table in ('erp.item_manufacturer','erp.item_alternative','erp.material_request','erp.stock_reservation_entry'):
        assert db.execute('SELECT count(*) FROM '+table).fetchone()[0]==0
