"""One request/claim/evaluation per OS process. Live observation never replaces adapter."""
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    request = json.load(sys.stdin)
    action = sys.argv[1]
    if action == 'api':
        import httpx
        from backend.wo.app import app
        async def invoke():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,raise_app_exceptions=False),base_url='http://qa.invalid') as client:
                headers = {'Idempotency-Key':request['key']} if request.get('key') else {}
                r = await client.request(request['method'],request['path'],json=request.get('body'),headers=headers)
                return {'status':r.status_code,'body':r.json(),'headers':dict(r.headers)}
        result = asyncio.run(invoke())
    else:
        observations=[]
        if action in ('live', 'live-lock'):
            import backend.wo.gateway as gateway
            original = gateway.call_gateway_completion
            def observed(*args,**kwargs):
                started=time.monotonic()
                locks_free = False
                if action == 'live-lock':
                    import os
                    import psycopg
                    with psycopg.connect(os.environ['TEST_DATABASE_URL']) as conn:
                        conn.execute('SELECT id FROM pp.wo_identification_session WHERE id=%s FOR UPDATE NOWAIT', (job['session_id'],)).fetchall()
                        conn.execute('SELECT id FROM pp.wo_identification_job WHERE id=%s FOR UPDATE NOWAIT', (job['id'],)).fetchall()
                        locks_free = True
                result=original(*args,**kwargs)
                observations.append({'locks_free':locks_free,'requested_model':kwargs.get('model',gateway.DEFAULT_MODEL),'reported_model':result.get('model'),'status':result.get('status'),'response_sha256':hashlib.sha256(str(result.get('content','')).encode()).hexdigest(),'elapsed':time.monotonic()-started,'max_tokens':kwargs.get('max_tokens',4096),'timeout':kwargs.get('timeout',20)})
                return result
            gateway.call_gateway_completion=observed
            gateway.call_gateway=observed
        import backend.wo.worker as worker
        if action == 'claim':
            result=worker.claim_next_job(request['worker_id'])
        elif action == 'process':
            result=worker.process_job(request['job'])
        else:
            job=worker.claim_next_job(request['worker_id'])
            result={'job':job,'processed':worker.process_job(job) if job else None,'observations':observations}
    print(json.dumps(result,default=str))

if __name__=='__main__':
    main()
