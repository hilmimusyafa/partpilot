# Handoff to Jarvis -> Forge -> fresh Sentinel

Authoring complete only; release_ready=false. No product implementation or managed
registration created here. Do not unblock t_d0f3de47 (DB); do not duplicate Nova's
QA-tool revision t_f0f41c25. A fresh backend card is not an escape from original DB
or integration gates. This directory was NEW and unregistered when scoped edits landed.

## Corrected ownership from Rifqi

UI, negotiation AND decision/automatic strategy-selection engine belong to Rifqi's
colleague. Backend owns data, identification/mapping, clarification, API, persistence,
validation and handoff interface. There are NO ranking/optimization/decision-engine or
full-product E2E tests here. OpenAPI fulfillment/options, fulfillment/select, approval
and vendor-handoff operations remain contract integration boundaries to align with the
colleague: validate integrity/approval/idempotency at that boundary, not generate the
colleague's decisions. No edits to private/protected OpenAPI were made. UI->negotiation
->decision E2E is deferred until those modules exist and Rifqi requests integration.

## EXECUTED_BY_SENTINEL

Repo /srv/hermes-control/services/partpilot, branch backend, HEAD 9af43b4 at start.
Product interpreter .venv/bin/python: Python 3.12.3 (not assumed shell version).
FastAPI 0.156.8, Starlette 1.9.0, httpx 0.28.1, pytest 9.1.1, Pydantic 2.14.1.
Product venv lacks yaml/jsonschema; schema-only checks use existing
/srv/apps/hermes/hermes-agent/venv/bin/python3 with those packages. This is QA tooling,
NOT Hermes in the product runtime. No packages installed or manifest modified.

Commands, run from repository root:

    .venv/bin/python -B tests/acceptance/api_workflow/run_checks.py syntax
    .venv/bin/python -B tests/acceptance/api_workflow/run_checks.py schema
    .venv/bin/python -B tests/acceptance/api_workflow/run_checks.py collect
    .venv/bin/python -B tests/acceptance/api_workflow/run_checks.py baseline
    .venv/bin/python -B tests/acceptance/api_workflow/run_checks.py test

Actual checks: Python syntax passes; configured skip/xfail AST guard passes; exact
collection 56 nodes passes (no skips); JSON Schema Draft2020-12 component validation,
local refs, 9 unique operations and 86 request/response example visits INCLUDING
reused error examples pass. This is NOT a rerun of official OpenAPI metaschema validation.
Baseline hash comparison: 30 upstream files and 5 private source documents unchanged.

Red run: evidence/20261021T143630108879Z/{collection.log,test.log,junit.xml,result.json}.
Exit 1, 56 setup errors, 0 assertion failures, 0 skips. All errors are explicit
MISSING_IMPLEMENTATION (partpilot.app absent); this is genuine missing-product RED,
NOT 56 behavioral assertions exercised/passed. Dependencies needed for collection ARE
available. Starlette emitted an existing httpx deprecation warning; retained in logs,
not suppressed or 'fixed' by dependency mutation. A first authoring tool cell had an
IndentationError before executing any file/tool operation; corrected cell then wrote
files. No product or upstream failed evidence was removed.

## INSPECTED_BY_SENTINEL

Read private OpenAPI/integration/FSM/required-BE/DB-decision documents, pyproject and
existing SQL function boundary names. BASELINE.json pins read sources and upstream
files. Protected production DB wrappers for the new aggregate/job model are not assumed
available: old SQL names do not establish a complete API transaction implementation.
Test doubles have no routes/domain decisions, no real PG/provider/customer data.

## UPSTREAM_REPORTED / NOT_VERIFIED

Upstream design task reported official OpenAPI validation and other checks; NOT
independently reproduced as official metaschema validation here. Existing DB acceptance
and smoke suites NOT run: they require separate authorized isolated PG work; this task
must not reset/touch DB. No listener, PG transaction, race, restart, role isolation,
actual LLM timeout clock, lease/reclaim/fencing, full identification/catalog mapping,
audit durability, financial approval or colleague integration is verified.
Editor LSP used the Hermes interpreter (without pytest/product) and reported missing
pytest/product imports; actual product-venv collection succeeds. No required typecheck
has been claimed green. Product missing remains blocking for product acceptance.

## BE coverage mapping (partial is not fulfillment of the whole BE gate)

| BE | Current package contribution | Still mandatory later |
|---|---|---|
|01|Schema/ref/example checker, generated slice operation IDs, response schema validation|Official OpenAPI metaschema and full generated spec compatibility|
|02|Hostile host/origin refuses mutation offline|Actual listener/bind/proxy/CORS/preflight|
|03|Forbidden context headers and extra org field|All spoof fields, DB binding, unverified audit provenance|
|04|Multiline/decimal/duplicate/context validation, unit-of-work atomicity|Real PG atomicity and adapter|
|05|Sequential identical replay, changed payload|Concurrent race, path scoping, lost committed response|
|06|Missing header, stale answer version, replay after worker advance|Concurrent optimistic-lock race|
|07|Readonly polling, queued/suspended/failed states, aggregate priority|Running/exhausted live snapshots, full aggregate table|
|08|Relationship/answered/replay, 3 distinct turns, atomic answer/resume|Real PG races and persistence|
|09|Three conditions, no repeat answered attribute, finite idle worker|Live persistence of suspend/resume|
|10-11|No fabricated match in negative extraction tests|Exact master/rules/suffix/provenance and conflict catalog mapping|
|12|Active-job/manual-review rematch rejection; tool escalation refusal|Actual tool capability boundary and adapter privileges|
|13-15|NOT TESTED: options/select are colleague integration boundary|Backend snapshot/integrity/state validation after interface alignment; NOT strategy engine|
|16-20|NOT TESTED: no fabricated approval/handoff in negative path only|DB approval validity/material invalidation, handoff integrity and colleague-boundary stubs|
|21|Finite no-op waiting/failed behavior only|Actual crash/lease/reclaim<=3/fencing/semantic uniqueness|
|22-25|NOT TESTED|Independent audit, least privilege, trusted org and controlled publication|
|26|Error envelope/schema, media/size/malformed JSON, bounded extraction failures|Live clock timeout, PG/provider exceptions and all endpoint errors|

## Bounded Forge instructions / registration prerequisites

1. Jarvis reviews scope/ports and WORKFLOW_PROPOSAL.json; it is a proposal, NOT a native
   registered contract. None of the 4 proposed candidate files exist yet. Authorized
   Forge preparation must create minimal importable placeholders only and report hashes
   before Jarvis registers exact protected checks/candidate paths. Placeholder preparation
   must not implement product behavior or claim PASS. Sentinel did not write placeholders.
2. Jarvis registers protected test/helper/runner/manifests and the existing candidate
   files, preserving criteria and evidence. If more candidate paths are needed, expand
   the contract explicitly BEFORE writing them. Protect the actual checker dependency
   interpreters/environment as operational prerequisites; no arbitrary fallback installs.
3. Forge implements real FastAPI and finite workflow using REQUIREMENTS.md internal port.
   Small modules only; no framework expansion. No product imports of acceptance files.
   No autonomous real external calls at startup. Injected doubles are explicit offline
   mode only, never production default. Missing live adapter stays 503 failclosed.
4. Live persistence adapter follows approved existing DB contracts. Unsupported wrappers
   remain unavailable; raise gap for separately authorized DB implementation, never invent
   a permissive direct-DML adapter or relax protected DB tests/grants.
5. Forge -> native request review reviewer=sentinel -> NEW independent Sentinel run.
   This author's test execution is not independent product approval. Preserve failure
   logs and hash changes across cycles; do not reuse future green after candidate drift.
6. Original DB gates plus later real PG/backend integration remain mandatory. Do not
   create/complete release cards from this authoring task. Colleague decision negotiation
   is an explicit stub/interface boundary, not an implementation-complete claim.

Verdict: authoring deliverable ready for registration review; product NOT VERIFIED and
NOT RELEASE READY (missing implementation and mandatory integration evidence).
