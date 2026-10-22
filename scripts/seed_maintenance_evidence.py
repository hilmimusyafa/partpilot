"""Import reviewed facts using an owner DSN. Does not run migrations or reset data."""
import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from backend.maintenance.ingest import load_evidence_pack
    from backend.maintenance.repository import seed_records
    import psycopg
    pack = Path(__file__).resolve().parents[1] / 'backend/maintenance/evidence_pack'
    parser = argparse.ArgumentParser()
    parser.add_argument('--history-dir', type=Path, default=pack / 'history')
    parser.add_argument('--economics-dir', type=Path, default=pack / 'economics')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    records = load_evidence_pack(args.history_dir, args.economics_dir)
    if args.validate_only:
        print(f'Validated {len(records)} source-backed evidence records; no database write.')
        return
    dsn = os.environ.get('MAINTENANCE_SEED_DATABASE_URL')
    if not dsn:
        raise SystemExit('Set MAINTENANCE_SEED_DATABASE_URL explicitly for owner-only evidence ingestion.')
    with psycopg.connect(dsn) as conn:
        inserted = seed_records(conn, records)
    print(f'Ingested {inserted} new evidence records; {len(records) - inserted} identical records retained.')


if __name__ == '__main__':
    main()
