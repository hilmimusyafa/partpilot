# Handoff to Jarvis / Forge / fresh Sentinel / Relay

Authoring task t_8dfdf171. release_ready=false. No product implementation or DB
execution is authorized by completing this authoring card.

Exact test files: test_bundle.py, test_sql.py. Supporting protected acceptance:
conftest.py, pytest.ini, expected.json, REQUIREMENTS.md, COLLECTION.json,
run_checks.py, HANDOFF.md, WORKFLOW_PROPOSAL.json. MANIFEST.json pins these and
original source/historical acceptance plus credential-resolver harness. Register
MANIFEST.json itself as protected in the native contract (no circular self-hash).
Do not regenerate frozen hashes/collection to accommodate an implementation.

Commands from repository root (existing .venv contains pytest and psycopg):
  .venv/bin/python tests/acceptance/monorepo_db/run_checks.py collection
  .venv/bin/python tests/acceptance/monorepo_db/run_checks.py static-red
  .venv/bin/python tests/acceptance/monorepo_db/run_checks.py runtime
First two commands never connect to any database. Runtime is reserved for fresh
Sentinel after managed implementation review. Timeout 180s child / 240s native
budget; collection/static 45s child / 60s native. Preserve evidence directories.

Minimum preparation by Forge, managed by Jarvis on existing release graph:
1. Copy frozen 001 and 009 to backend/db/ without changing/removing originals.
2. Implement new combined seed at backend/db/seed/009_bearing_mvp_synth.sql using
   expected.json's eight records and guards rejecting every mismatched seed-owned
   field; identical seed replay must be no-op. Do not edit original five-row seed.
3. Write public-safe backend/README.md and backend/docs/db/bearing-mvp.md with
   relative run order specified in REQUIREMENTS.md, synthetic/unverified limits
   and frontend-deferred scope. Review exact SQL before runtime for transaction
   escape/external side effects. This harness is not a sandbox for hostile SQL.
4. Native-register these exact checks/protected files and candidate hashes; Forge
   requests new independent Sentinel review. No earlier PASS applies to new seed.
5. Relay resumes SAME publication card t_72da7891 after fresh PASS, exact allowlist
   backend bundle plus root README only if authorized; no old private paths/tests/
   original root SQL or internal artifacts. No push by this authoring task.

Scribe separately owns backend/knowledge/PartPilot/ snapshot export; do not edit
that subtree. Its content/link safety and optional root README remain Relay's
exact publication-diff review, not invented prerequisites for SQL authoring.

Historical 56 tests remain untouched, not reused as WH02-empty oracle. Main DB
was not inspected or modified in this run. Runtime remains NOT_VERIFIED until
fresh review. Authoring evidence records real expected-red missing product files,
not mocked success. Native software acceptance remains separate from card done.
