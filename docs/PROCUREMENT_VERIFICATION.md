# Verification record — 22 October 2026

Implementation is a synthetic backend demo, not a production release or native Hermes workflow acceptance. No main database migration, service restart, commit/push, or real vendor message was performed.

## Evidence and scope

- Final canonical-source regression run: **34 passed, 1 deselected** in 132.77 seconds. The deselected case is explicitly marked live gateway; that integration passed in the separate 34-test run below. No other skips/xfails. Command: `.venv/bin/python scripts/run_isolated_checks.py -- -q --tb=short tests/codex`.
- Tests use independently owned PostgreSQL 16 clusters on Unix sockets. They validate database/user ownership before loading fixture SQL and remove their own clusters afterward. API requests run in fresh Python processes.
- Full MVP run from the canonical VPS project: **34 passed**, including a real gateway call, before the final conflict-detail regression was added. Command: `.venv/bin/python scripts/run_isolated_checks.py --gateway-env /home/rifqisetiawan/.config/partpilot/gateway-codex.env`.
- Final conflict-detail change: **6 passed** in targeted testing, including the preserved real-PostgreSQL test `test_g6_unit_conflicting_valid_observations_not_last_value_wins` and five public identity tests. This fixes missing explanatory conflict details; conflicting identities were already blocked from identification.
- Expanded compatibility run: **192 passed, 3 failed**, on the earlier review candidate. One failure was the conflict-detail defect above and passed after repair. The other two retained tests require immediate `failed` on the first retryable gateway timeout/outage; the worker instead queues a durable retry and fails after the second attempt. New `test_gateway_failure_has_durable_backoff_then_bounded_failure[timeout/outage]` tests both passed, including rejection of an early retry and a third call. Historical tests were not edited, deleted, skipped or marked xfail to hide this difference. This is not an all-green historical acceptance claim.
- Re-running those three historical failures against the final candidate produced **1 passed, 2 failed**: conflict details are repaired; the two immediate-failure expectations remain as documented. The durable-backoff behavior is consistent with the existing ADR007 addendum's G4 requirement. A future acceptance-contract update should reconcile G4 and the two G6 assertions rather than silently removing either.
- Two independent reviewers inspected the implementation and reviewed the corrections; neither reported remaining blockers in the bounded demo scope. PostgreSQL execution evidence comes from the implementation test runs, not from the reviewers' static assessments.
- Python AST parsing and worker CLI help checks passed. No dependency upgrade was performed.

## Business rules covered

Origin-sufficient stops vendor contact; exact WH02 alias; missing suffix and unsupported modifier fail closed; human-only quantity correction preserves raw submission; unknown warehouse rules and non-piece UOMs are not invented; five simulated vendor outcomes; single-source whole quantity; persistent one-counteroffer limit; committed-outbox crash recovery; retries and fresh-process reads; no inventory mutation; deterministic economics; unknown donor/economic inputs unrankable; original quote selectable after refusal; idempotent creation/comparison/decision; expired, stock-changed, quote-changed and item-changed choices rejected; immutable comparisons/audit; database rejects forged partial-source comparisons and unsafe outbound payloads.

## Tested environment

Python 3.12.3; PostgreSQL 16; FastAPI 0.156.8; Pydantic 2.14.1; psycopg 3.3.6; httpx 0.28.1; PyYAML 6.0.3; pytest 9.1.1. These are observed installed versions, not a new lockfile. The gateway model alias is configured by existing code; a requested alias does not prove an identical upstream model identity.

## Remaining boundaries

See `PROCUREMENT_DEMO.md` for exact API contract, simulation assumptions and deployment steps. Authentication/tenant isolation, a real WhatsApp adapter, migration of legacy WO DML to validating functions, production database-role tests, comprehensive rejected-request audit, and a consistent cross-warehouse read snapshot remain production hardening. The manager endpoint records intent only. It does not create a PO, transfer stock or complete repair.

The eight original bearing seed records and warehouse note files were preserved. Before synchronization, every affected source file was checked against its saved hash; concurrent drift would abort. Original-source backup: `/srv/hermes-control/services/partpilot/private/codex-backup-20261022-105345`. Later backups retain incremental reviewed changes. Gateway environment values were not copied to source or logs.

Durable test logs are saved under `private/codex-verification-20261022/` (Git-ignored). Final source hashes are recorded there as well. No current test cluster is used as a persistent demonstration database.
