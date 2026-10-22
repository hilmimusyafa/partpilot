"""Bounded isolated test harness for Bearing MVP acceptance.
Executes real PostgreSQL queries inside an uncommitted transaction with savepoints.
Guarantees zero persistent schema modification and strict target isolation.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

import psycopg
import pytest

WORKSPACE_ROOT = Path("/srv/hermes-control/services/partpilot").resolve()
CONTRACT_PATH = Path("/srv/hermes-control/services/qa-feedback/contracts/default/t_58d57ef0.json")
SECRETS_PATH = Path("/srv/hermes-control/private/partpilot/secrets/pp_migrator.env")
BEARING_TESTS_DIR = WORKSPACE_ROOT / "tests/acceptance/bearing_mvp"

TARGET_DB = "partpilot_bearing_test"
TARGET_USER = "pp_migrator"
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 5432
ADVISORY_LOCK_ID = 58057083


class TargetRefusalError(RuntimeError):
    """Raised when target database, endpoint, or prewrite conditions fail."""


class BearingAuthorizedHarnessPlugin:
    """Pytest plugin providing db fixture backing and native authorization checks."""

    def __init__(self, connection: psycopg.Connection):
        self._conn = connection
        self._sp_counter = 0

    def native_authorization_verified(self) -> bool:
        if not CONTRACT_PATH.is_file():
            return False
        try:
            contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return False

        if contract.get("task_id") != "t_58d57ef0":
            return False
        if contract.get("workspace") != str(WORKSPACE_ROOT):
            return False
        if contract.get("implementer") != "forge":
            return False

        protected_hashes = contract.get("protected_sha256", {})
        if not protected_hashes:
            return False

        for fpath_str, expected_hash in protected_hashes.items():
            fpath = Path(fpath_str)
            if not fpath.is_file():
                return False
            actual_hash = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual_hash != expected_hash:
                return False

        candidate_files = contract.get("candidate_files", [])
        for cpath_str in candidate_files:
            cpath = Path(cpath_str)
            if not cpath.is_file():
                return False

        return True

    @contextmanager
    def rollback_only_connection(self):
        self._sp_counter += 1
        sp_name = f"bearing_sp_{self._sp_counter}"
        self._conn.execute(f"SAVEPOINT {sp_name}")
        try:
            yield self._conn
        finally:
            try:
                self._conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
                self._conn.execute(f"RELEASE SAVEPOINT {sp_name}")
            except Exception:
                pass


class PluginRegistrar:
    """Registers the bearing_authorized_harness plugin in pytest configure."""

    def __init__(self, harness_plugin: BearingAuthorizedHarnessPlugin):
        self.harness_plugin = harness_plugin

    def pytest_configure(self, config):
        config.pluginmanager.register(self.harness_plugin, name="bearing_authorized_harness")


def _read_target_password() -> str:
    """Reads pp_migrator password in-process without logging or printing."""
    if not SECRETS_PATH.is_file():
        raise TargetRefusalError("Required credentials file not found")

    values: dict[str, str] = {}
    for line in SECRETS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip("\"'")

    raw_url = values.get("TEST_DATABASE_URL", "")
    parsed = urlparse(raw_url)
    password = unquote(parsed.password or "")
    if not password:
        raise TargetRefusalError("Password resolution failed")
    return password


def verify_target_connection(conn: psycopg.Connection, expected_db: str = TARGET_DB, expected_user: str = TARGET_USER):
    """Verifies endpoint, current database, user, and initial emptiness before any write."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                current_database(),
                session_user,
                current_user,
                inet_server_addr()::text,
                inet_server_port(),
                (SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()),
                (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema'),
                (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname<>'information_schema')
            """
        )
        row = cur.fetchone()
        if not row:
            raise TargetRefusalError("Unable to retrieve target connection metadata")

        cur_db, sess_usr, cur_usr, srv_addr, srv_port, db_owner, rel_count, proc_count = row

        if cur_db != expected_db:
            raise TargetRefusalError(f"Target refusal: current_database is {cur_db}, expected {expected_db}")
        if sess_usr != expected_user or cur_usr != expected_user:
            raise TargetRefusalError(f"Target refusal: user mismatch ({sess_usr}/{cur_usr} != {expected_user})")
        if srv_addr not in ("127.0.0.1", "127.0.0.1/32"):
            raise TargetRefusalError(f"Target refusal: host address mismatch ({srv_addr} != 127.0.0.1)")
        if srv_port != TARGET_PORT:
            raise TargetRefusalError(f"Target refusal: port mismatch ({srv_port} != {TARGET_PORT})")
        if db_owner != expected_user:
            raise TargetRefusalError(f"Target refusal: database owner is {db_owner}, expected {expected_user}")
        if rel_count != 0 or proc_count != 0:
            raise TargetRefusalError(f"Target refusal: target database not empty ({rel_count} relations, {proc_count} routines)")


def prove_wrong_target_prewrite_refusal(conn: psycopg.Connection):
    """Proves that attempt to write to non-bearing target is refused before any SQL is applied."""
    try:
        verify_target_connection(conn, expected_db="partpilot_main_production")
        raise AssertionError("Wrong-target check failed to refuse")
    except TargetRefusalError:
        pass


def prove_sql_failure_abort(conn: psycopg.Connection):
    """Proves that a SQL failure aborts transaction cleanly and rolls back to pristine state."""
    sp_name = "test_failure_proof"
    conn.execute(f"SAVEPOINT {sp_name}")
    try:
        conn.execute("SELECT * FROM non_existent_table_for_failure_proof")
        raise AssertionError("SQL failure proof did not raise error")
    except psycopg.Error:
        conn.execute(f"ROLLBACK TO SAVEPOINT {sp_name}")
        conn.execute(f"RELEASE SAVEPOINT {sp_name}")


def prove_deterministic_seed_replay(conn: psycopg.Connection, sql_001: str, sql_009: str, sql_seed: str):
    """Proves that applying 001+009+seed in uncommitted cycles is strictly deterministic."""
    for cycle in (1, 2):
        sp = f"replay_cycle_{cycle}"
        conn.execute(f"SAVEPOINT {sp}")
        conn.execute(sql_001)
        conn.execute(sql_009)
        conn.execute(sql_seed)

        c_count = conn.execute("SELECT count(*) FROM erp.company").fetchone()[0]
        w_count = conn.execute("SELECT count(*) FROM erp.warehouse").fetchone()[0]
        i_count = conn.execute("SELECT count(*) FROM erp.item").fetchone()[0]
        b_count = conn.execute("SELECT count(*) FROM erp.bin").fetchone()[0]

        if (c_count, w_count, i_count, b_count) != (1, 5, 5, 5):
            raise AssertionError(f"Deterministic replay counts mismatch on cycle {cycle}: {(c_count, w_count, i_count, b_count)}")

        conn.execute(f"ROLLBACK TO SAVEPOINT {sp}")
        conn.execute(f"RELEASE SAVEPOINT {sp}")


def run_acceptance() -> int:
    """Executes the full acceptance suite under isolated single uncommitted transaction."""
    password = _read_target_password()

    sql_001 = (WORKSPACE_ROOT / "db/001_schema.sql").read_text(encoding="utf-8")
    sql_009 = (WORKSPACE_ROOT / "db/009_bearing_lookup.sql").read_text(encoding="utf-8")
    sql_seed = (WORKSPACE_ROOT / "db/seed/009_bearing_mvp_synth.sql").read_text(encoding="utf-8")

    print("[harness] Connecting to 127.0.0.1:5432/partpilot_bearing_test as pp_migrator...")
    with psycopg.connect(
        host=TARGET_HOST,
        port=TARGET_PORT,
        dbname=TARGET_DB,
        user=TARGET_USER,
        password=password,
        autocommit=False,
    ) as conn:
        # Preflight verification
        verify_target_connection(conn)
        print("[harness] Preflight verified: endpoint 127.0.0.1:5432, db partpilot_bearing_test, owner pp_migrator, 0 user objects.")

        # Safety proofs
        prove_wrong_target_prewrite_refusal(conn)
        print("[harness] Safety proof 1: Wrong-target prewrite refusal verified.")

        prove_sql_failure_abort(conn)
        print("[harness] Safety proof 2: SQL failure transaction abort verified.")

        prove_deterministic_seed_replay(conn, sql_001, sql_009, sql_seed)
        print("[harness] Safety proof 3: Deterministic seed replay verified.")

        # Advisory lock & timeouts
        conn.execute(f"SELECT pg_advisory_lock({ADVISORY_LOCK_ID})")
        conn.execute("SET statement_timeout = '30s'")
        conn.execute("SET lock_timeout = '5s'")
        conn.execute("SET idle_in_transaction_session_timeout = '60s'")
        print("[harness] Advisory lock acquired; timeouts configured.")

        try:
            # Preload 001 + 009 + seed in the main uncommitted transaction
            print("[harness] Applying 001_schema.sql, 009_bearing_lookup.sql, 009_bearing_mvp_synth.sql...")
            conn.execute(sql_001)
            conn.execute(sql_009)
            conn.execute(sql_seed)
            print("[harness] Preload applied within uncommitted transaction.")

            # Setup harness plugin
            harness_plugin = BearingAuthorizedHarnessPlugin(conn)
            if not harness_plugin.native_authorization_verified():
                print("[harness] Native authorization verification FAILED")
                return 1
            print("[harness] Native authorization verified against registered contract and protected SHA256 hashes.")

            registrar = PluginRegistrar(harness_plugin)

            pytest_args = [
                "-c",
                str(BEARING_TESTS_DIR / "pytest.ini"),
                "--confcutdir",
                str(BEARING_TESTS_DIR),
                "-p",
                "no:cacheprovider",
                "-v",
                str(BEARING_TESTS_DIR / "test_seed_scope.py"),
                str(BEARING_TESTS_DIR / "test_exact_lookup.py"),
                str(BEARING_TESTS_DIR / "test_query_plan.py"),
            ]

            print(f"[harness] Executing pytest on {len(pytest_args) - 7} test suites...")
            pytest_exit = pytest.main(pytest_args, plugins=[registrar])
            print(f"[harness] Pytest completed with exit code: {pytest_exit}")

            if pytest_exit != 0:
                print(f"[harness] Pytest run failed with code {pytest_exit}")
                return pytest_exit

        finally:
            print("[harness] Rolling back main preload transaction...")
            conn.rollback()
            try:
                conn.execute(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_ID})")
            except Exception:
                pass
            print("[harness] Advisory lock released.")

        # Post-run emptiness verification
        verify_target_connection(conn)
        print("[harness] Post-run verified: target database is completely empty (0 user objects). Zero persistent modifications.")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="PartPilot Bearing MVP Isolated Harness")
    parser.add_argument("--acceptance", action="store_true", help="Run full acceptance suite")
    args = parser.parse_args()

    if not args.acceptance:
        parser.print_help()
        return 1

    return run_acceptance()


if __name__ == "__main__":
    sys.exit(main())
