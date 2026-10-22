"""Database connection fixtures and test session lifecycle configuration."""

import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = (REPO_ROOT / "../../private/partpilot/secrets").resolve()
DB_DIR = REPO_ROOT / "db"
RESET_SCRIPT = REPO_ROOT / "scripts" / "reset_test_db.sh"


def pytest_configure(config):
    """Register custom markers for the test suite."""
    config.addinivalue_line("markers", "acceptance: Acceptance test marker")
    config.addinivalue_line("markers", "db_layer: Database contract test marker")


def get_role_connection_url(role_name: str) -> str:
    """Retrieve connection string for a specific database role."""
    env_var_key = f"TEST_DATABASE_URL_{role_name.upper()}"
    if env_var_key in os.environ:
        url = os.environ[env_var_key]
    elif "TEST_DATABASE_URL" in os.environ and role_name == "pp_migrator":
        url = os.environ["TEST_DATABASE_URL"]
    else:
        secrets_path = SECRETS_DIR / f"{role_name}.env"
        if not secrets_path.exists():
            pytest.skip(f"Role configuration not found at {secrets_path}")

        env_vars = {}
        with open(secrets_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()

        url = env_vars.get("TEST_DATABASE_URL")
        if not url:
            pytest.skip(f"TEST_DATABASE_URL not found in {secrets_path}")

    assert url is not None
    parsed = urlparse(url)
    db_name = (parsed.path or "").lstrip("/")
    if db_name != "partpilot_test":
        pytest.fail(f"Refusing to run tests against non-test database: {db_name}")

    return str(url)


def create_role_connection(role_name: str, autocommit: bool = True) -> psycopg.Connection:
    """Create a new database connection for the requested role."""
    url = get_role_connection_url(role_name)
    return psycopg.connect(url, autocommit=autocommit)


def reset_test_database():
    """Reset test database applying baseline 001-006 and 008 when present."""
    if RESET_SCRIPT.exists():
        subprocess.run(
            [str(RESET_SCRIPT)],
            check=True,
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    # Apply 008_mvp_contracts.sql if present
    migration_008 = DB_DIR / "008_mvp_contracts.sql"
    if migration_008.exists():
        url = get_role_connection_url("pp_migrator")
        subprocess.run(
            ["psql", "-v", "ON_ERROR_STOP=1", url, "-f", str(migration_008)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )


@pytest.fixture(scope="session", autouse=True)
def session_database_setup():
    """Ensure database is reset and migrations applied at test session start."""
    reset_test_database()


@pytest.fixture
def migrator_conn():
    """Database connection with migration owner privileges."""
    conn = create_role_connection("pp_migrator", autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def app_conn():
    """Database connection with application role privileges."""
    conn = create_role_connection("pp_app", autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def agent_conn():
    """Database connection with tool-caller role privileges."""
    conn = create_role_connection("pp_agent", autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def console_conn():
    """Database connection with approval console role privileges."""
    conn = create_role_connection("pp_console", autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def worker_conn():
    """Database connection with background worker role privileges."""
    conn = create_role_connection("pp_worker", autocommit=True)
    try:
        yield conn
    finally:
        conn.close()
