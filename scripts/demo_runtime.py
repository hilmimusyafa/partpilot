"""Supervised demo API/worker. Load only scoped server-side credential files."""
import os
import signal
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def load(path,allowed):
    for line in Path(path).read_text().splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip() in allowed:os.environ[key.strip()]=value.strip().strip('\"\'')

def main():
    load('/run/partpilot/runtime.env',{'DATABASE_URL','PARTPILOT_DEMO_PASSWORD','PARTPILOT_PUBLIC_ORIGIN'})
    if sys.argv[1]=='api':
        if not os.environ.get('PARTPILOT_DEMO_PASSWORD'):raise RuntimeError('Missing demo login')
        import uvicorn
        uvicorn.run('backend.demo.app:app',host='127.0.0.1',port=18080,proxy_headers=True,forwarded_allow_ips='127.0.0.1',access_log=False)
    elif sys.argv[1]=='worker':
        load('/run/partpilot/gateway.env',{'HERMES_9ROUTER_API_KEY','HERMES_9ROUTER_BASE_URL'})
        from backend.wo.gateway import runtime_timeout
        runtime_timeout()  # Validate bounded configuration before claiming any job.
        from backend.wo.worker import claim_next_job,process_job
        running=True
        def stop(*_):
            nonlocal running
            running=False
        signal.signal(signal.SIGTERM,stop)
        signal.signal(signal.SIGINT,stop)
        while running:
            try:
                job=claim_next_job('partpilot-deployed-worker')
                if job:process_job(job)
            except Exception as exc:
                # Do not log connection strings, model messages or credential values.
                print('Worker tick failed:',type(exc).__name__,flush=True)
            time.sleep(1)
    else:raise ValueError('Expected api or worker')

if __name__=='__main__':main()
