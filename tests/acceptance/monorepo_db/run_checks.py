"""Bounded acceptance runner; runtime is opt-in and never invoked by collection."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTS = ["test_bundle.py", "test_sql.py"]
SQL_PATHS = ["backend/db/001_schema.sql", "backend/db/009_bearing_lookup.sql",
             "backend/db/seed/009_bearing_mvp_synth.sql"]

def integrity():
    manifest = json.loads((HERE / "MANIFEST.json").read_text())
    for group in ("protected_sha256", "original_sha256"):
        for path, digest in manifest[group].items():
            if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Protected/source hash mismatch: " + path)

def sql_boundary(text):
    # Remove quoted values/identifiers, dollar bodies and comments before
    # recognizing top-level commands. Nested block comments are handled.
    out = []
    i = 0
    while i < len(text):
        if text.startswith('--', i):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
        elif text.startswith('/*', i):
            depth = 1
            i += 2
            while depth and i < len(text):
                if text.startswith('/*', i): depth += 1; i += 2
                elif text.startswith('*/', i): depth -= 1; i += 2
                else: i += 1
            if depth: raise RuntimeError("Unterminated SQL comment")
        elif text[i] in ("'", '"'):
            quote = text[i]
            i += 1
            while i < len(text):
                if text[i] == quote:
                    i += 1
                    if i < len(text) and text[i] == quote: i += 1; continue
                    break
                if text[i] == "\\": i += 1
                i += 1
            out.append(' VALUE ')
        elif text[i] == '$' and (match := re.match(r'\$(?:[A-Za-z_][A-Za-z_0-9]*)?\$', text[i:])):
            tag = match.group()
            end = text.find(tag, i + len(tag))
            if end < 0: raise RuntimeError("Unterminated dollar body")
            i = end + len(tag)
            out.append(' BODY ')
        else:
            out.append(text[i]); i += 1
    cleaned = ''.join(out)
    # These files may define SQL/PLpgSQL routines, not control this runner's
    # outer transaction, access server files/network, or change privileges.
    for statement in cleaned.split(';'):
        first = statement.strip().upper()
        if re.match(r'(?:COMMIT|END|ABORT|ROLLBACK|BEGIN|START|SAVEPOINT|RELEASE|PREPARE|VACUUM|GRANT|REVOKE|COPY|ALTER\s+(?:SYSTEM|ROLE|USER)|CREATE\s+(?:DATABASE|ROLE|USER)|DROP\s+DATABASE)\b', first):
            raise RuntimeError("Unsafe top-level SQL command")
    if re.search(r'(?i)\b(?:dblink|pg_read_file|pg_write_file|lo_import|lo_export)\b', cleaned):
        raise RuntimeError("External SQL access refused")

def pytest_command(mode):
    args = [sys.executable, '-m', 'pytest', '-c', str(HERE / 'pytest.ini'),
            '--confcutdir', str(HERE), '-p', 'no:cacheprovider', '-q']
    if mode == 'collection': args += ['--collect-only']
    return args + [str(HERE / name) for name in (TESTS[:1] if mode == 'static-red' else TESTS)]

def runtime():
    import psycopg
    import pytest
    integrity()
    candidate = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SQL_PATHS}
    sql = [(ROOT / p).read_text() for p in SQL_PATHS]
    for text in sql: sql_boundary(text)
    spec = importlib.util.spec_from_file_location('approved_harness', ROOT / 'scripts/bearing_isolated_harness.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    # Existing local resolver only; no DSN accepted from argv/environment.
    password = harness._read_target_password()
    conn = psycopg.connect(host='127.0.0.1', port=5432,
                          dbname='partpilot_bearing_test', user='pp_migrator',
                          password=password, autocommit=False, connect_timeout=5)
    code = 1
    try:
        conn.execute("SET statement_timeout='20s'")
        conn.execute("SET lock_timeout='3s'")
        conn.execute("SET idle_in_transaction_session_timeout='45s'")
        locked = conn.execute('SELECT pg_try_advisory_lock(58057083)').fetchone()[0]
        if not locked: raise RuntimeError('Dedicated target busy')
        harness.verify_target_connection(conn)
        print('Dedicated target/owner/endpoint/empty preflight passed', flush=True)
        # Original SQL is frozen; the changed seed must not escape transaction.
        conn.execute(sql[0])
        conn.execute(sql[1])
        columns = conn.execute("SELECT json_agg(row(table_schema,table_name,column_name,data_type) ORDER BY table_schema,table_name,ordinal_position)::text FROM information_schema.columns WHERE table_schema IN ('erp','pp','midea')").fetchone()[0]
        conn.execute("SELECT set_config('acceptance.columns_before',%s,true)", (columns,))
        conn.execute(sql[2])
        class Plugin:
            def pytest_configure(self, config): config.monorepo_connection = conn
        args = pytest_command('runtime')[3:]
        code = int(pytest.main(args, plugins=[Plugin()]))
    finally:
        try:
            conn.rollback()
            harness.verify_target_connection(conn)
            print('Post-rollback target empty: 0 user relations/routines', flush=True)
            conn.rollback()
        finally:
            conn.close()  # releases session advisory lock even on failure
    integrity()
    if candidate != {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SQL_PATHS}:
        raise RuntimeError('Candidate drift during execution')
    return code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['collection','static-red','runtime'])
    parser.add_argument('--runtime-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.runtime_child:
        try: return runtime()
        except Exception as exc:
            # Credential-bearing exception messages/tracebacks never emitted.
            print('Runtime failed: ' + type(exc).__name__ + '; target refused or SQL/check failure')
            return 1
    integrity()
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = HERE / 'evidence' / stamp
    output.mkdir(parents=True)
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1')
    command = ([sys.executable, str(Path(__file__).resolve()), 'runtime', '--runtime-child']
               if args.mode == 'runtime' else pytest_command(args.mode))
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=180 if args.mode == 'runtime' else 45)
        log = result.stdout.decode(errors='replace')
        code = result.returncode
    except subprocess.TimeoutExpired:
        log = 'Bounded runner timeout; child terminated; connection closure rolls back transaction.\n'
        code = 124
    (output / 'checks.log').write_text(log)
    if args.mode == 'collection' and code == 0:
        nodes = [line for line in log.splitlines() if '::test_' in line]
        expected = json.loads((HERE / 'COLLECTION.json').read_text())
        if nodes != expected: code = 1; log += '\nExact collection mismatch\n'
    integrity()
    (output / 'result.json').write_text(json.dumps(dict(mode=args.mode, exit_code=code,
        provenance='EXECUTED_BY_SENTINEL' if args.mode != 'runtime' else 'EXECUTED_BY_RUNNER',
        release_ready=False), indent=2)+'\n')
    print(log, end='')
    print('Evidence: ' + str(output))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
