import os
from pathlib import Path
from urllib.parse import urlparse
import psycopg
import pytest

DEFAULT_SECRETS = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "private"
    / "partpilot"
    / "secrets"
    / "pp_migrator.env"
)
SECRETS_FILE = os.getenv("SECRETS_FILE", str(DEFAULT_SECRETS))


def get_connection_url() -> str:
    if "TEST_DATABASE_URL" in os.environ:
        return os.environ["TEST_DATABASE_URL"]

    secrets_path = Path(SECRETS_FILE)
    if not secrets_path.exists():
        pytest.skip(f"Configuration file not found at {SECRETS_FILE}")

    env_vars = {}
    with open(secrets_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

    test_url = env_vars.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("TEST_DATABASE_URL not found in configuration")

    parsed = urlparse(test_url)
    db_name = parsed.path.lstrip("/")
    if db_name != "partpilot_test":
        pytest.fail(f"Refusing to run tests against non-test database: {db_name}")

    return test_url


@pytest.fixture(scope="module")
def db_conn():
    url = get_connection_url()
    conn = psycopg.connect(url)
    try:
        yield conn
    finally:
        conn.close()


def test_db_connection(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user;")
        row = cur.fetchone()
        assert row is not None
        db_name, user = row
        assert db_name == "partpilot_test"
        assert user == "pp_migrator"


def test_schema_existence(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name IN ('midea', 'erp', 'pp');
            """
        )
        schemas = {r[0] for r in cur.fetchall()}
        assert schemas == {"midea", "erp", "pp"}


def test_object_counts(db_conn):
    expected_tables = {
        "midea": 2,
        "erp": 29,
        "pp": 34,
    }
    expected_views = {
        "midea": 1,
        "erp": 0,
        "pp": 10,
    }

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_schema, table_type, COUNT(*)
            FROM information_schema.tables
            WHERE table_schema IN ('midea', 'erp', 'pp')
            GROUP BY table_schema, table_type;
            """
        )
        rows = cur.fetchall()

    actual_tables = {s: 0 for s in expected_tables}
    actual_views = {s: 0 for s in expected_views}

    for schema, tbl_type, count in rows:
        if tbl_type == "BASE TABLE":
            actual_tables[schema] = count
        elif tbl_type == "VIEW":
            actual_views[schema] = count

    # DB-01 spec in PRD: midea 2, erp 29, pp 34 tables; 11 total views (1 midea, 10 pp)
    assert actual_tables == expected_tables, f"Table count mismatch: {actual_tables} vs {expected_tables}"
    assert actual_views == expected_views, f"View count mismatch: {actual_views} vs {expected_views}"
    assert sum(actual_tables.values()) == 65
    assert sum(actual_views.values()) == 11


def test_core_tables_populated(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM midea.spare_parts_report;")
        midea_parts = cur.fetchone()[0]
        assert midea_parts == 222

        cur.execute("SELECT COUNT(*) FROM erp.item;")
        erp_items = cur.fetchone()[0]
        assert erp_items == 222

        cur.execute("SELECT COUNT(*) FROM pp.source_catalog;")
        catalogs = cur.fetchone()[0]
        assert catalogs == 5
