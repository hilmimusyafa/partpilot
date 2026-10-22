"""One-time provisioning of an EMPTY dedicated demo database, not a shared ERP."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
CONTEXT = dict(company_id='SYN-COMPANY-01',site_id='DEMO-SITE',production_line_id='DEMO-LINE',
               station_id='DEMO-STATION',machine_id='DEMO-CONVEYOR')

def install_demo(conn, *, allow_test_database=False):
    row = conn.execute('SELECT current_database() AS name').fetchone()
    name = row['name'] if isinstance(row,dict) else row[0]
    if name != 'partpilot_demo' and not (allow_test_database and re.fullmatch(r'partpilot_test_core_[0-9a-f]{16}',name)):
        raise ValueError('Installer requires dedicated partpilot_demo database')
    exists = conn.execute("SELECT to_regclass('pp.demo_control') IS NOT NULL AS ready").fetchone()
    ready = exists['ready'] if isinstance(exists,dict) else exists[0]
    if ready:
        raise ValueError('Demo already initialized; use guarded reset, not installer')
    if not allow_test_database:
        if conn.execute("SELECT 1 FROM information_schema.tables WHERE table_schema IN ('pp','erp','midea') LIMIT 1").fetchone():
            raise ValueError('Target database is not empty')
        for path in ['001_schema.sql','009_bearing_lookup.sql','seed/009_bearing_mvp_synth.sql',
                     '010_work_order_identification.sql','011_work_order_production_context.sql']:
            conn.execute((ROOT/'backend/db'/path).read_text(),prepare=False)
    for path in ['012_procurement_demo.sql','013_demo_console.sql','014_whatsapp.sql','015_purchase_orders.sql','016_negotiation_policy.sql','018_dashboard_revisions.sql','019_plain_vendor_replies.sql']:
        conn.execute((ROOT/'backend/db'/path).read_text(),prepare=False)
    if conn.execute("SELECT 1 FROM erp.company WHERE name<>'SYN-COMPANY-01'").fetchone():
        raise ValueError('Non-demo company present')
    conn.execute("INSERT INTO pp.production_site(id,company,name) VALUES('DEMO-SITE','SYN-COMPANY-01','Pabrik AC Cikarang (simulasi)')")
    conn.execute("INSERT INTO pp.production_line(id,company,site_id,name,production_scope) VALUES('DEMO-LINE','SYN-COMPANY-01','DEMO-SITE','Lini perakitan AC A','AC')")
    conn.execute("INSERT INTO pp.production_station(id,company,production_line_id,name) VALUES('DEMO-STATION','SYN-COMPANY-01','DEMO-LINE','Stasiun conveyor assembly')")
    conn.execute("INSERT INTO erp.asset(name,asset_name,company,status) VALUES('DEMO-CONVEYOR','Conveyor assembly CV-01','SYN-COMPANY-01','Submitted')")
    conn.execute("INSERT INTO pp.machine_context(asset,company,station_id) VALUES('DEMO-CONVEYOR','SYN-COMPANY-01','DEMO-STATION')")
    conn.execute("INSERT INTO pp.asset_ext(asset,site_warehouse,criticality) VALUES('DEMO-CONVEYOR','SYN-WH-01','D')")
    conn.execute("UPDATE erp.bin SET reserved_qty=6 WHERE item_code='SYN-WH01-NTN-6200LLU' AND warehouse='SYN-WH-01'")
    conn.execute("INSERT INTO pp.demo_control(dataset_tag,reset_enabled,stock_baseline) SELECT 'synthetic-bearing-demo-v1',true,jsonb_agg(to_jsonb(b)) FROM erp.bin b")
    # Fixture017 checks the enabled demo control and appends three baselines;
    # historical seed009 and the original eight baseline rows remain intact.
    conn.execute((ROOT/'backend/db/017_five_warehouse_demo.sql').read_text(),prepare=False)
