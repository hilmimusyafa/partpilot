"""Run selected checks with gateway-only configuration; never load a production DSN."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--gateway-env',type=Path)
    parser.add_argument('args',nargs=argparse.REMAINDER)
    options=parser.parse_args()
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONPATH=os.pathsep.join([str(ROOT),str(ROOT/'private/core-corrective-v1')]))
    env.pop('DATABASE_URL',None);env.pop('TEST_DATABASE_URL',None)
    if options.gateway_env:
        for line in options.gateway_env.read_text().splitlines():
            key,sep,value=line.partition('=')
            if sep and key.strip() in {'HERMES_9ROUTER_API_KEY','HERMES_9ROUTER_BASE_URL'}:
                env[key.strip()]=value.strip().strip('\"\'')
    args=options.args
    if args and args[0]=='--':args=args[1:]
    if not args:args=['-q','tests/codex']
    if not options.gateway_env:args=['-m','not live_gateway',*args]
    return subprocess.run([sys.executable,'-m','pytest','--import-mode=importlib','-p','no:cacheprovider',*args],cwd=ROOT,env=env).returncode
if __name__=='__main__':sys.exit(main())
