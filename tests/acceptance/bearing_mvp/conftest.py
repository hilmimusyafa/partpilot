"""No legacy fixtures, DSN access or DB connection on import/collection."""
import pytest
NAMES = ('NTN 6200LLU','NTN 6801ZZ','NTN 6900LLB','NTN 6000LLH','NTN 6701LLF')
DIMS = ('10x30x9','12x21x5','10x22x6','10x26x8','12x18x4')
COMPANY = 'SYN-COMPANY-01'
WH = 'SYN-WH-01'

@pytest.fixture
def db(request):
    provider=request.config.pluginmanager.get_plugin('bearing_authorized_harness')
    if provider is None:
        pytest.fail('RUNTIME_NOT_ACTIVATED: native revision and isolated harness required',pytrace=False)
    if not provider.native_authorization_verified():
        pytest.fail('NATIVE_AUTHORIZATION_MISSING',pytrace=False)
    with provider.rollback_only_connection() as connection:
        yield connection

@pytest.fixture
def lookup(db):
    def call(name=NAMES[0],company=COMPANY,category='Bearing',warehouse=WH):
        return db.execute('SELECT * FROM pp.lookup_bearing_exact(%s,%s,%s,%s)',(company,category,warehouse,name)).fetchall()
    return call

@pytest.fixture
def decoy(db):
    def add(code,name=NAMES[0],category='Bearing',warehouse=WH):
        db.execute('INSERT INTO erp.item_group(name) VALUES (%s) ON CONFLICT DO NOTHING',(category,))
        db.execute("INSERT INTO erp.item(item_code,item_name,item_group,stock_uom) VALUES (%s,%s,%s,'Nos')",(code,name,category))
        db.execute('INSERT INTO erp.bin(item_code,warehouse,actual_qty) VALUES (%s,%s,10)',(code,warehouse))
    return add


def pytest_collection_modifyitems(config, items):
    for item in items:
        if item.get_closest_marker('skip') or item.get_closest_marker('skipif') or item.get_closest_marker('xfail'):
            raise pytest.UsageError('skip/xfail forbidden in bearing acceptance')


def pytest_sessionfinish(session, exitstatus):
    reporter=session.config.pluginmanager.get_plugin('terminalreporter')
    if reporter is not None and any(reporter.stats.get(key) for key in ('skipped','xfailed','xpassed')):
        session.exitstatus=1
