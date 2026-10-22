"""Self-contained integration harness: private socket PG16; no shared DSN is ever used."""
import atexit
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import psycopg
from psycopg.conninfo import make_conninfo, conninfo_to_dict
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv/bin/python'
PG = Path('/usr/lib/postgresql/16/bin')
BASE = '/api/v1/work-orders'


def run(argv, **kwargs):
    return subprocess.run([str(x) for x in argv], cwd=ROOT, text=True,
                          capture_output=True, timeout=kwargs.pop('timeout', 90), **kwargs)


def validate_target(conn, database, owner):
    """Check the connected server, not a DSN substring; before any DDL/DML."""
    assert re.fullmatch(r'partpilot_test_core_[0-9a-f]{16}', database), 'unowned database name'
    assert re.fullmatch(r'sentinel_[0-9a-f]{16}', owner), 'unowned role name'
    row = conn.execute("SELECT current_database(), current_user, pg_get_userbyid(datdba), current_setting('server_version_num')::int FROM pg_database WHERE datname=current_database()").fetchone()
    assert tuple(row[:3]) == (database, owner, owner), 'actual DB/user/owner mismatch'
    assert 160000 <= row[3] < 170000, 'PostgreSQL16 required'
    assert not conn.execute("SELECT nspname FROM pg_namespace WHERE nspname NOT IN ('public','information_schema') AND nspname NOT LIKE 'pg_%'").fetchall(), 'database not empty'


class Cluster:
    def __init__(self):
        token = uuid.uuid4().hex[:16]
        self.database = 'partpilot_test_core_' + token
        self.owner = 'sentinel_' + token
        self.temp = tempfile.TemporaryDirectory(prefix='partpilot-owned-')
        self.path = Path(self.temp.name)
        self.started = False
        self.marker = self.path / 'owner.json'
        self.marker.write_text(json.dumps({'database': self.database, 'owner': self.owner}))
        self.data = self.path / 'data'
        self.sock = self.path / 'socket'
        self.sock.mkdir(mode=0o700)
        p = run([PG/'initdb', '-D', self.data, '-U', self.owner, '--auth=trust', '--no-locale', '--encoding=UTF8'])
        assert p.returncode == 0, 'owned initdb failed: ' + p.stderr[-400:]
        p = run([PG/'pg_ctl', '-D', self.data, '-l', self.path/'postgres.log', '-o', f"-k {self.sock} -h '' -p 55439 -F", '-w', 'start'])
        assert p.returncode == 0, 'owned PG start failed: ' + p.stderr[-400:]
        self.started = True
        atexit.register(self.close)
        admin = make_conninfo(host=str(self.sock), port=55439, dbname='postgres', user=self.owner)
        with psycopg.connect(admin, autocommit=True) as conn:
            from psycopg import sql
            conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(self.database), sql.Identifier(self.owner)))
        self.dsn = make_conninfo(host=str(self.sock), port=55439, dbname=self.database, user=self.owner)
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            validate_target(conn, self.database, self.owner)
            for name in ['backend/db/001_schema.sql','backend/db/009_bearing_lookup.sql','backend/db/seed/009_bearing_mvp_synth.sql','backend/db/010_work_order_identification.sql','backend/db/011_work_order_production_context.sql']:
                conn.execute((ROOT/name).read_text(), prepare=False)
            assert {x[0] for x in conn.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('erp','pp','midea')")} == {'erp','pp','midea'}
        self.env = os.environ.copy()
        self.env.update(TEST_DATABASE_URL=self.dsn, DATABASE_URL=self.dsn,
                        PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=os.pathsep.join(filter(None,(str(ROOT),os.environ.get('PYTHONPATH')))))
        self.fixture = self.provision()
        self.before = self.snapshot()

    def connection(self):
        conn = psycopg.connect(self.dsn, row_factory=dict_row)
        actual = conn.execute("SELECT current_database() db,current_user usr,pg_get_userbyid(datdba) owner FROM pg_database WHERE datname=current_database()").fetchone()
        assert actual == {'db':self.database,'usr':self.owner,'owner':self.owner}
        return conn

    def sql(self, query, params=()):
        with self.connection() as conn:
            cur = conn.execute(query, params or None)
            return cur.fetchall() if cur.description else []

    def provision(self):
        t = uuid.uuid4().hex
        f = {'company_id':'SYN-COMPANY-01','site_id':'s-'+t,'production_line_id':'l-'+t,'station_id':'t-'+t,'machine_id':'m-'+t,'warehouse_id':'SYN-WH-01'}
        with self.connection() as c:
            c.execute('INSERT INTO erp.company(name) VALUES(%s)', ('foreign-'+t,))
            c.execute('INSERT INTO pp.production_site(id,company,name) VALUES(%s,%s,%s)', (f['site_id'],f['company_id'],'synthetic'))
            c.execute("INSERT INTO pp.production_line(id,company,site_id,name,production_scope) VALUES(%s,%s,%s,'synthetic','AC')", (f['production_line_id'],f['company_id'],f['site_id']))
            c.execute("INSERT INTO pp.production_station(id,company,production_line_id,name) VALUES(%s,%s,%s,'synthetic')", (f['station_id'],f['company_id'],f['production_line_id']))
            c.execute("INSERT INTO erp.asset(name,asset_name,company,status) VALUES(%s,'synthetic',%s,'Submitted')", (f['machine_id'],f['company_id']))
            c.execute('INSERT INTO pp.machine_context(asset,company,station_id) VALUES(%s,%s,%s)', (f['machine_id'],f['company_id'],f['station_id']))
            c.execute("INSERT INTO pp.asset_ext(asset,site_warehouse,criticality) VALUES(%s,%s,'D')", (f['machine_id'],f['warehouse_id']))
        return f

    def snapshot(self):
        names = self.sql("SELECT table_schema,table_name FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema IN ('erp','pp') AND table_name NOT LIKE 'wo_identification_%' ORDER BY 1,2")
        result = {}
        from psycopg import sql
        with self.connection() as c:
            for row in names:
                q = sql.SQL('SELECT row_to_json(t)::text v FROM {}.{} t ORDER BY row_to_json(t)::text').format(sql.Identifier(row['table_schema']),sql.Identifier(row['table_name']))
                result[row['table_schema']+'.'+row['table_name']] = hashlib.sha256(json.dumps(c.execute(q).fetchall(),sort_keys=True).encode()).hexdigest()
        return result

    def api(self, method, path, body=None, key=None, env=None):
        p = run([PYTHON,HERE/'process_probe.py','api'], input=json.dumps({'method':method,'path':path,'body':body,'key':key}), env=env or self.env)
        assert p.returncode == 0, 'API subprocess failed: '+p.stderr[-1000:]
        return json.loads(p.stdout)

    def worker(self, action='tick', job=None, worker_id=None):
        p = run([PYTHON,HERE/'process_probe.py',action],input=json.dumps({'job':job,'worker_id':worker_id or uuid.uuid4().hex}),env=self.env,timeout=80)
        assert p.returncode == 0, 'worker subprocess failed: '+p.stderr[-1000:]
        return json.loads(p.stdout)

    def draft(self, description='bearing NTN 6200LLU', **extra):
        body = dict(self.fixture, description=description, quantity='1', notes='  raw notes\n')
        body.update(extra)
        r = self.api('POST',BASE,body,uuid.uuid4().hex)
        assert r['status'] == 201, r
        return r['body']

    def row(self,sid):
        rows = self.sql('SELECT * FROM pp.wo_identification_session WHERE id=%s',(sid,))
        assert len(rows)==1, 'HTTP session absent from actual PostgreSQL'
        return rows[0]

    def close(self):
        if self.started:
            assert self.marker.exists() and self.data.parent == self.path
            saved = json.loads(self.marker.read_text())
            assert saved == {'database':self.database,'owner':self.owner}
            p = run([PG/'pg_ctl','-D',self.data,'-m','immediate','-w','stop'])
            assert p.returncode == 0, 'owned cluster shutdown failed'
            self.started = False
            self.temp.cleanup()
