"""Bounded offline checks. Run from any cwd; all generated evidence stays HERE."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PYTHON = str(ROOT / '.venv/bin/python')
SCHEMA_PYTHON = '/srv/apps/hermes/hermes-agent/venv/bin/python3'
MANIFEST = json.loads((HERE / 'COLLECTION.json').read_text())
ENV = {'PATH': '/usr/bin:/bin', 'HOME': str(HERE), 'LANG': 'C.UTF-8',
       'PYTHONHASHSEED': '0', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}


def syntax():
    for file in HERE.glob('*.py'):
        tree = ast.parse(file.read_text(), filename=str(file))
        compile(tree, str(file), 'exec')
        if file.name.startswith('test_') or file.name == 'conftest.py':
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr in {'skip', 'skipif', 'xfail', 'importorskip'}:
                    raise AssertionError(f'Forbidden skip/xfail: {file.name}:{node.lineno}')
    print('PASS syntax; no skip/xfail directives', flush=True)


def execute(argv):
    result = subprocess.run(argv, cwd=HERE, env=ENV, text=True, capture_output=True, timeout=180)
    return result, result.stdout + result.stderr


def check_baseline():
    baseline = json.loads((HERE / 'BASELINE.json').read_text())
    changed = [name for name, digest in baseline['upstream_files'].items()
               if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    changed += [name for name, digest in baseline['private_sources'].items()
                if not Path(name).is_file() or hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest]
    assert not changed, f'Baseline drift: {changed}'
    print(f"PASS unchanged: {len(baseline['upstream_files'])} upstream files; {len(baseline['private_sources'])} private sources", flush=True)


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    assert mode in {'syntax', 'schema', 'collect', 'test', 'baseline'}
    syntax()
    if mode == 'syntax':
        return
    if mode == 'baseline':
        check_baseline()
        return
    if mode == 'schema':
        result, output = execute([SCHEMA_PYTHON, '-B', str(HERE / 'schema_check.py')])
        print(output, end='')
        raise SystemExit(result.returncode)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = HERE / 'evidence' / stamp
    run.mkdir(parents=True, exist_ok=False)
    argv = [PYTHON, '-B', '-m', 'pytest', '-c', str(HERE / 'pytest.ini'),
            '--confcutdir=' + str(HERE), '-p', 'no:cacheprovider', '-q', str(HERE)]
    result, output = execute(argv + ['--collect-only'])
    (run / 'collection.log').write_text(output)
    nodes = [line.strip() for line in result.stdout.splitlines() if line.startswith('test_') and '::' in line]
    assert result.returncode == 0, 'COLLECTION BLOCKER: see ' + str(run / 'collection.log')
    assert nodes == MANIFEST['nodeids'], 'Exact collection mismatch; see ' + str(run / 'collection.log')
    print(f'PASS exact collection: {len(nodes)} nodes; {run}', flush=True)
    if mode == 'collect':
        return
    report = run / 'junit.xml'
    result, output = execute(argv + ['--junitxml=' + str(report)])
    (run / 'test.log').write_text(output)
    suites = ET.parse(report).getroot()
    cases = list(suites.iter('testcase'))
    skipped = list(suites.iter('skipped'))
    valid_count = len(cases) == len(MANIFEST['nodeids']) and not skipped
    record = {'argv': argv, 'exit_code': result.returncode, 'testcases': len(cases),
              'failures': len(list(suites.iter('failure'))), 'errors': len(list(suites.iter('error'))),
              'skipped': len(skipped), 'exact_count': valid_count,
              'release_ready': False,
              'protected_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in HERE.iterdir() if p.is_file() and p.name != 'WORKFLOW_PROPOSAL.json'}}
    (run / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(output, end='')
    print('Evidence: ' + str(run), flush=True)
    if not valid_count:
        raise SystemExit(2)
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
