"""Bounded authoring runner. Runtime cannot activate by environment flags."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
TESTS=['test_seed_scope.py','test_exact_lookup.py','test_query_plan.py']

def main():
    mode=sys.argv[1] if len(sys.argv)==2 else ''
    if mode not in ('collection','static-red','runtime'):
        raise SystemExit('usage: run_checks.py collection|static-red|runtime')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    evidence=BASE/'evidence'/stamp
    evidence.mkdir(parents=True,exist_ok=False)
    result={'mode':mode,'release_ready':False,'provenance':'EXECUTED_BY_SENTINEL when run by Sentinel','errors':[]}
    def fail(message): result['errors'].append(message)
    baseline=json.loads((BASE/'BASELINE.json').read_text())['sha256']
    for name,digest in baseline.items():
        if not Path(name).is_file() or hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            fail('original drift: '+name)
    manifest=json.loads((BASE/'COLLECTION.json').read_text())
    for name,digest in manifest['protected_sha256'].items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:
            fail('acceptance drift: '+name)
    for name in ['conftest.py',*TESTS,'run_checks.py']:
        tree=ast.parse((BASE/name).read_text(),filename=name)
        for node in ast.walk(tree):
            if isinstance(node,ast.Attribute) and node.attr in ('skip','skipif','xfail'):
                fail('forbidden skip/xfail: '+name)
    env={k:v for k,v in os.environ.items() if not k.startswith(('PYTEST','PG','DATABASE','PARTPILOT','BEARING'))}
    env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
    argv=[sys.executable,'-B','-m','pytest','-c',str(BASE/'pytest.ini'),'--confcutdir',str(BASE),'-p','no:cacheprovider','--collect-only','-q',*[str(BASE/t) for t in TESTS]]
    result['collection_argv']=argv
    try:
        proc=subprocess.run(argv,cwd=BASE,env=env,text=True,capture_output=True,timeout=45)
        (evidence/'collection.log').write_text(proc.stdout+proc.stderr)
        result['collection_exit']=proc.returncode
        ids=[line for line in proc.stdout.splitlines() if line.startswith('test_') and '::' in line]
        result['collected']=len(ids)
        if proc.returncode!=0 or ids!=manifest['nodeids']: fail('exact collection mismatch')
    except subprocess.TimeoutExpired:
        fail('collection timeout')
    if mode=='static-red':
        missing=[name for name in manifest['planned_candidates'] if not (ROOT/name).is_file()]
        result['missing_candidates']=missing
        for name in missing: fail('candidate missing: '+name)
        # Presence is not behavior acceptance; never turn static-only into PASS.
        fail('runtime/backend/notes/safety gates NOT VERIFIED')
    if mode=='runtime':
        fail('RUNTIME_NOT_ACTIVATED: official revision and protected isolated harness required; no DB connection attempted')
    result['exit_code']=1 if result['errors'] else 0
    result['verdict']='AUTHORING_CHECK_ONLY' if not result['errors'] else 'NOT_VERIFIED'
    (evidence/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'evidence':str(evidence),**result},indent=2))
    return result['exit_code']

if __name__=='__main__':
    raise SystemExit(main())
