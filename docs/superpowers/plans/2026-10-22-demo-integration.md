# PartPilot Integrated Demo Implementation Plan

> Execute in this session with a bounded frontend implementer and independent final review.

Goal: merge frontend main and existing backend, demonstrate bearing sourcing with repeatable isolated reset, deploy requested domain.
Architecture: Next static export served by FastAPI, PostgreSQL 16 demo-only database, persistent WO worker, existing Caddy HTTPS proxy. All credentials server-side. Existing business invariants remain.
Spec: user request 2026-10-22 and docs/PROCUREMENT_DEMO.md.

## Constraints
- Synthetic stock, aliases, vendor quotes and economic assumptions explicitly labelled.
- Manager chooses intent; no real messaging, purchasing or stock mutation.
- Preserve canonical uncommitted source and frontend design; no real ERP/reset collateral.
- Reset is guarded in database, authenticated, transactional, generation checked, audited and rejects active worker jobs.
- Existing worker may perform trusted repository writes; model never receives database access.

## Tasks
- [x] Merge main 042c913 and backend f7efc24 in owned clone; import backed-up canonical source; resolve README/gitignore preserving both.
- [x] Add protected demo config/orders/default comparison/reset API, fixture production hierarchy and reset migration. Test disabled reset, stale generation, active job, repeatability, snapshot preservation and comparison.
- [x] Connect technician, clarification and manager pages to real API; retain palette/logo, show honest states, reset confirmation and scenario presets. Build static export and check browser flow/reload.
- [x] Package dedicated PostgreSQL and API/worker deployment with restart, loopback-only listeners, gateway secret mount. Provision isolated DB; run regression and real-model bearing cases.
- [x] Independent review; deploy Caddy host after checks; verify HTTPS, auth boundary, UI/API and reset twice. Save demo guide and curl examples.

## Review Focus
Stale browser after reset; in-flight worker vs reset; partial/no-response source cannot be selected; lost POST response retry; untrusted text and public secret/cost/reset access.

## Execution ledger
Source imported from fresh canonical backup without private data or credentials. User explicitly authorized merge/deployment so no redundant approval requested. Caddy file write permission may require user action after exact artifact prepared. Frontend task delegated under workspace AGENTS bounded implementation rule.

Final verification: 42 selected PostgreSQL regressions passed (1 live case deselected), frontend lint/typecheck/static build passed, live model origin/alias/vendor/clarification verified, browser retry/decision reload/reset twice/stale tab/mobile verified. Independent reviewer findings fixed with RED/GREEN regressions. Runtime 60s timeout bounded below 90s lease after measured 41.94s valid extraction; default remains20s. Demo reset archives audit and returns seed stock4/8. PublicHTTPS verified; runtime permissions checked after API/worker restart.
