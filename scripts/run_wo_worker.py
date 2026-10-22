"""Explicit, bounded worker invocation; gateway secrets remain server-side."""
import argparse
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gateway-env', type=Path)
    parser.add_argument('--max-ticks', type=int, default=1)
    parser.add_argument('--poll-seconds', type=float, default=1)
    parser.add_argument('--worker-id', default='partpilot-demo-worker')
    args = parser.parse_args()
    if not 1 <= args.max_ticks <= 10000 or not 0.1 <= args.poll_seconds <= 60:
        parser.error('max-ticks must be 1..10000 and poll-seconds 0.1..60')
    if args.gateway_env:
        for line in args.gateway_env.read_text().splitlines():
            key, sep, value = line.partition('=')
            if sep and key.strip() in {'HERMES_9ROUTER_API_KEY','HERMES_9ROUTER_BASE_URL'}:
                os.environ[key.strip()] = value.strip().strip('\"\'')
    from backend.wo.repository import get_db_connection
    from backend.wo.worker import claim_next_job, process_job
    processed = 0
    try:
        with get_db_connection() as conn:
            conn.execute('SELECT 1')
        for tick in range(args.max_ticks):
            job = claim_next_job(args.worker_id)
            if job:
                process_job(job)
                processed += 1
            if tick + 1 < args.max_ticks:
                time.sleep(args.poll_seconds)
    except Exception as exc:
        # Raw exceptions can contain connection details or vendor content.
        print(f'Worker stopped ({type(exc).__name__}); inspect private operational logs.', file=sys.stderr)
        return 1
    print(f'Worker finished: {processed} jobs processed in {args.max_ticks} ticks.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
