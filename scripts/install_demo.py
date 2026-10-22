"""Provision new dedicated deployment; refuses existing or non-demo databases."""
from pathlib import Path
import sys
from urllib.parse import urlparse,unquote
import psycopg
from psycopg import sql
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.demo.bootstrap import install_demo

def main():
    p=Path('/home/rifqisetiawan/.config/partpilot')
    owner=(p/'demo-db-owner-password').read_text().strip()
    with psycopg.connect(host='127.0.0.1',port=55438,dbname='partpilot_demo',user='partpilot_owner',password=owner) as conn:
        install_demo(conn)
        for role,filename in [('pp_demo_api','demo-runtime.env'),('pp_demo_worker','demo-worker.env')]:
            values=dict(line.split('=',1) for line in (p/filename).read_text().splitlines() if '=' in line)
            password=unquote(urlparse(values['DATABASE_URL']).password)
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role),sql.Literal(password)))
            conn.execute(sql.SQL('GRANT CONNECT ON DATABASE partpilot_demo TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT USAGE ON SCHEMA erp,pp TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT SELECT ON ALL TABLES IN SCHEMA erp,pp TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT INSERT,UPDATE ON pp.wo_identification_session,pp.wo_identification_event,pp.wo_identification_job,pp.wo_identification_idempotency TO {}').format(sql.Identifier(role)))
            conn.execute(sql.SQL('GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA pp TO {}').format(sql.Identifier(role)))
        # Agent/model receives no DSN. Trusted API can execute only approved procurement/reset functions.
        for signature, in conn.execute("SELECT p.oid::regprocedure::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='pp' AND p.proname IN ('demo_start','demo_enqueue','demo_receive','demo_compare','demo_choose','demo_reset','demo_plan_negotiation','wa_start','wa_enqueue')"):
            conn.execute(sql.SQL('GRANT EXECUTE ON FUNCTION {} TO pp_demo_api').format(sql.SQL(signature)))
        conn.execute('REVOKE ALL ON pp.demo_reset_audit FROM pp_demo_api,pp_demo_worker')
        conn.execute('REVOKE ALL ON pp.demo_control FROM pp_demo_worker')
    print('Dedicated demo initialized; runtime roles cannot modify ERP stock or directly reset workflow tables.')

if __name__=='__main__':main()
