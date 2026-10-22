# PartPilot procurement simulator implementation plan

> Execute inline using executing-plans and TDD; fresh independent review at completion.

Goal: persisted bearing WO identification -> five warehouse evaluation -> simulated vendor quotations -> at most one price counteroffer per vendor -> deterministic comparison -> manager decision only.
Architecture: retain FastAPI/PostgreSQL worker; isolate transport behind a protocol, keep stock read-only, all procurement mutations through validating database functions and append-only events. No real messaging, stock mutation, production migration, deploy, commit or push.
Spec: latest human conversation; private/handover/PartPilot_PRD_End_to_End_untuk_Astra.md and private/vendor-demo-v1/DECISIONS.md are supporting context. Additional frontend/lifecycle scope in handover is not authorized by the present request.

## Global constraints
- Python 3.12, PostgreSQL 16, FastAPI, Pydantic, psycopg, httpx. Reuse deterministic Decimal calculator.
- One source must fulfill the entire requested quantity; synthetic bearing records only; preserve original eight seed records.
- Origin sufficient terminates source search, not repair. Otherwise assess other warehouses and simulated vendors.
- Counteroffer budget is per procurement run and vendor, persistent across retry/restart; no response is not zero stock.
- No competitor quote, downtime or contribution-margin values in outbound payloads.
- Manager selection records intent; never executes procurement. Preserve historical protected tests and logs.

## Tasks and acceptance
1. Core: reproduce existing failures in isolated PostgreSQL; repair exact identity, clarification, persistent workers, ancestry and economics defects. Files backend/wo/*.py, tests/codex/*.py. Existing corrective suite plus targeted regressions must pass or be reported explicitly.
2. Persistence/transport: backend/procurement/{models,transport,simulator,repository,service}.py, backend/db/012_procurement_demo.sql. Tests must prove source scoping, whole quantities, SQL-enforced counteroffer limit under concurrency/retry and fresh-process reads.
3. Comparison/API: backend/procurement/{comparison,router}.py; reuse backend.wo.economics. Tests must prove price/ETA/expiry validity, unknown inputs unrankable, immutable historical snapshots, no automatic decision, expired/changed source rejection.
4. Integration/runbook: tests/codex full workflow plus fault/restart checks; read-only inventory assertions; docs procurement API, explicit migrations, simulator/worker entrypoints and tested commands.
5. Independent review and final verification. Report native Hermes workflow as untouched, never fabricate native acceptance. No publish/deploy without separate approval.

## Review focus
- Identity token collisions and missing suffix cannot silently select a different bearing.
- Crash between sending and receiving must reuse logical event ID; counteroffer retry cannot spend a second budget.
- Missing costs and no response must not become zero/cheap winning options.
- Source changes/expiry between comparison and manager decision must fail closed.
- All SQL writes audit provenance and preserve inventory; externally supplied vendor text confers no authority.

## Execution rulings
- Human already approved design and execution; no redundant plan approval is requested.
- Preserve dirty backend branch and untracked source. Snapshot baseline; stage candidate in an isolated copy, test there, then synchronize reviewed source changes with drift checks. Do not create a worktree that would omit untracked implementation.
- Human explicitly stopped Hermes development; do not create native Hermes tasks or reactivate workers. Independent code review does not restart Hermes.
