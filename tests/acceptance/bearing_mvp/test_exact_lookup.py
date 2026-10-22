import pytest
from conftest import COMPANY,WH,NAMES

@pytest.mark.parametrize('name',NAMES)
def test_B03_exact_hit(lookup,name):
    rows=lookup(name)
    assert len(rows)==1
    assert rows[0][0:2]==('SYN-WH01-'+name.replace(' ','-'),name)
    assert rows[0][3:]==(WH,10,0,10)

@pytest.mark.parametrize('warehouse',['SYN-WH-02','SYN-WH-03','SYN-WH-04','SYN-WH-05'])
def test_B03_empty_scope(lookup,warehouse):
    assert lookup(warehouse=warehouse)==[]

@pytest.mark.parametrize('field',['company','category','warehouse','name'])
@pytest.mark.parametrize('value',[None,'',' ','UNKNOWN'])
def test_B05_invalid_sql_scope(lookup,field,value):
    assert lookup(**{field:value})==[]

@pytest.mark.parametrize('name',['6200','NTN 6200','ntn 6200llu','NTN6200LLU','NTN  6200LLU','NTN 6200LLU ','NTN-6200LLU','NTN 6200LLB','NTN 6701LLB',"' OR true --",'NTN 6200LLU%','NTN 6200LL_'])
def test_B06_no_fuzzy(lookup,name):
    assert lookup(name)==[]
    assert len(lookup())==1

@pytest.mark.parametrize('field',['company','category','warehouse'])
def test_B06_scope_injection(lookup,field):
    assert lookup(**{field:"' OR true --"})==[]
    assert len(lookup())==1

def test_B04_category(decoy,lookup):
    decoy('SYN-DECOY-CATEGORY',category='NotBearing')
    assert [r[0] for r in lookup()]==['SYN-WH01-NTN-6200LLU']
    assert lookup(category='NotBearing')==[]

def test_B04_company_warehouse(db,decoy,lookup):
    decoy('SYN-DECOY-WH',warehouse='SYN-WH-02')
    assert [r[0] for r in lookup()]==['SYN-WH01-NTN-6200LLU']
    assert [r[0] for r in lookup(warehouse='SYN-WH-02')]==['SYN-DECOY-WH']
    db.execute("INSERT INTO erp.company(name) VALUES ('SYN-OTHER-COMPANY')")
    db.execute("INSERT INTO erp.warehouse(name,warehouse_name,company) VALUES ('SYN-OTHER-WH','Synthetic','SYN-OTHER-COMPANY')")
    decoy('SYN-DECOY-COMPANY',warehouse='SYN-OTHER-WH')
    assert lookup(warehouse='SYN-OTHER-WH')==[]
    assert lookup(company='SYN-OTHER-COMPANY')==[]

@pytest.mark.parametrize('target',['item','warehouse','group'])
def test_B04_disabled_group(db,lookup,target):
    assert len(lookup())==1
    if target=='item':
        db.execute('UPDATE erp.item SET disabled=true WHERE item_name=%s',(NAMES[0],))
    else:
        column='disabled' if target=='warehouse' else 'is_group'
        db.execute('UPDATE erp.warehouse SET '+column+'=true WHERE name=%s',(WH,))
    assert lookup()==[]

def test_B07_ambiguity(lookup,decoy):
    decoy('SYN-DUPLICATE')
    assert {r[0] for r in lookup()}=={'SYN-DUPLICATE','SYN-WH01-NTN-6200LLU'}
    assert len(lookup())==2

def test_B07_no_auto_merge(lookup,decoy):
    decoy('SYN-LOCAL-OTHER',name='SYN-LOCAL-NAME',warehouse='SYN-WH-02')
    assert lookup('SYN-LOCAL-NAME')==[]
    assert lookup(warehouse='SYN-WH-02')==[]
    assert lookup('SYN-LOCAL-NAME',warehouse='SYN-WH-02')[0][0]=='SYN-LOCAL-OTHER'

def test_B08_zero_stock(db,lookup):
    db.execute("UPDATE erp.bin SET reserved_qty=actual_qty WHERE item_code='SYN-WH01-NTN-6200LLU'")
    rows=lookup()
    assert len(rows)==1 and rows[0][6]==0
    assert lookup('MISSING')==[]
