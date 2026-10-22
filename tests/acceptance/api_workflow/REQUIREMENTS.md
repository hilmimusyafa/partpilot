# Offline API/workflow acceptance — authoring only

Status: test-first proposal, NOT registered managed workflow and NOT product acceptance.
release_ready=false. Only this new directory is writable in task t_9e765a14.

## Authority and corrected scope

Source hashes/paths: BASELINE.json. Normative private OpenAPI draft and integration
guide override older CLOSED/replay-200 diagrams: terminal DONE; replay initial 202;
fixed trusted synthetic organization. Original DB contracts/tests remain untouched.
No raw private contracts are distributed with this package.

Latest Rifqi/operator correction: UI, negotiation AND decision/strategy-selection
engine belong to the user's colleague. Our scope is backend/data, identification/
mapping, clarification workflow, API, storage/validation and interface handoff.
Do not implement/test ranking, optimization, automatic strategy selection, or full
UI->negotiation->decision E2E. Selection/decision contract operations are integration
boundaries requiring alignment with the colleague, not backend-owned decision logic.
The YAML is not silently changed. Such E2E is deferred until colleague modules are
ready and Rifqi explicitly requests integration. Integrity, approval validity and
idempotency remain backend obligations; these are NOT business decision ownership.

## Pinned wire contract (no new endpoints)

- POST /api/v1/work-orders: intakeWorkOrder, 202 WorkOrderResult.
  Intake body: work_order_id, asset_id, site_id, target_warehouse_id,
  maintenance_type corrective/preventive, priority 1..5, parts_requested 1..50,
  optional claimed_actor. Line: unique positive line_number, requested_text 1..4000,
  positive decimal STRING qty_needed (max 3 fractional digits), uom PCS.
- GET /api/v1/work-orders/{work_order_id}: getWorkOrder, 200 WorkOrderResult,
  Cache-Control no-store; no mutation or enqueue.
- POST /api/v1/work-orders/{work_order_id}/parts/{wo_part_id}/clarifications/answer:
  answerClarification, 202. Answer body: expected_version >=1, question_id,
  session_id, turn_number 1..3, answer_text 1..4000, optional claimed_actor.
- POST /api/v1/work-orders/{work_order_id}/parts/{wo_part_id}/match:
  matchPart, 202 only if state permits; expected_version and optional claimed_actor.
  Existing active queued/running match and MANUAL_REVIEW must reject 409 INVALID_STATE.
- POST requires Idempotency-Key, 8..128 ASCII chars matching contract regex.
  Scope org+method+canonical path+case-sensitive key; fingerprint canonical RFC8785
  request JSON including version/claimed_actor. Identical replay returns initial
  status/body before version guard, Idempotency-Replayed=true. Changed body ->409
  IDEMPOTENCY_CONFLICT. Missing key ->400 CONTEXT_REJECTED.
- Stale aggregate version ->409 VERSION_CONFLICT with current_version. Wrong parent
  resource ->404 NOT_FOUND; stale/wrong question relation ->404/409 INVALID_STATE as
  contract permits, no answer/job effects. Extra/invalid fields ->422 VALIDATION_ERROR.
- Forbidden context headers ->400 CONTEXT_REJECTED. Hostile host/origin ->403 LOCAL_ONLY.
  Body >256KiB ->413 REQUEST_TOO_LARGE; media ->415 UNSUPPORTED_MEDIA_TYPE;
  malformed JSON ->422 VALIDATION_ERROR. Storage/enqueue unavailable ->503
  SERVICE_UNAVAILABLE retryable=true; no partial success/outcome.
- Success/error bodies validated against pinned private schema, including required
  sanitized request_id, retryable/current_version for errors. No product auth feature.

## Callable acceptance port (proposed INTERNAL Python interface, not HTTP contract)

Forge prepares src/partpilot/__init__.py, app.py, workflow.py, adapters.py. No product
files are authored by Sentinel. create_app(*, repository=None, erp, llm) returns a real
FastAPI app with app.state.workflow.run_once(). Injected repository/ERP/LLM are explicit
offline test doubles from doubles.py. Product MUST NOT import acceptance helpers,
hardcode scripted outputs, or substitute route stubs for domain workflow logic.
run_once synchronously claims at most one queued job, processes finite work and returns;
no background startup task, sleep, scheduling/network needed in this offline mode.
It may handle all lines within one WO job or one line/job. Waiting/failed/terminal jobs
are not automatically retried by idle run_once. No HTTP worker/resume route is added.

MemoryRepository is a generic transactional namespace store: work_orders, jobs,
idempotency, answers. transaction() yields detached dict; all business mutations to
these namespaces commit together or not at all. Values may be product-owned dicts or
models. snapshot() is inspection only. fail_commit injects storage failure. This proves
SEQUENTIAL application unit-of-work behavior only, NOT durable enqueue in real PG.
Exact decimal values must be retained, never binary float quantities. Product owns
idempotency keys, question/session/turn validation, aggregate calculation and transitions.

FakeERP.validate_context validates the fixed org's one synthetic site/asset and five
warehouses; lookup_exact returns no catalog identity. No real manufacturer/catalog or
customer codes in fixture. Real mapping/catalog acceptance remains later work.
FakeLLM.extract(text=..., answers=...) returns extraction-only JSON:
{facts: [], missing_attributes: [attribute,...], knowledge_gap: bool, conflicts: [text,...]}.
No state, permission, approval, raw SQL or tools are authorized by this port. The real
workflow validates response, generates questions, versions and jobs itself. Scripted
exceptions/invalid JSON/tool calls test refusal. One extraction + <=2 transport retries
per job; timeout setting <=20s is a proposed server bound, not a UI field. No technical
failure creates a fabricated match/approval. Terminal failed/exhausted remains inert
without an authorized retry path. Crash/reclaim max3/fencing is separate real-PG work.

## Minimum behavior under test

- Atomic multiline intake/outcome/job; failed commit leaves all namespaces unchanged;
  same-key retry after failure succeeds; exact decimal positives incl 0.100; validation.
- Poll queued/suspended/failed snapshots, no-store and no side effects; finite job states
  distinct from business states; multi-line MANUAL_REVIEW aggregate takes priority.
- Missing user information -> one open question + suspended_waiting_input. System
  knowledge gap -> immediate MANUAL_REVIEW with no open question. Conflict is visible,
  never silently matched. Idle worker does not keep calling LLM.
- Answer + aggregate version increment + resume enqueue + idempotency result atomic.
  Replay after worker advance returns original response, no turn/job duplication.
- Question/session/parent/turn checks, answered-ticket/new-key rejection, stale version.
- At most three distinct question/answer turns in one session, no repeated answered
  attribute; unresolved after turn3 -> MANUAL_REVIEW, no fourth question.
- Invalid/timeout/escalated-tool extraction stops within bound, failed/exhausted and
  sanitized error code, no financial action or false identity success.
- repository=None must fail closed 503, NEVER silently choose memory persistence.
  The production adapter must use existing approved DB contract and refuse unavailable
  operations. No tests demand nonexistent revised wrappers or broad DML privileges.

## Non-substitutable later gates

Real Postgres16 isolated synthetic integration: transaction/crash/restart durability,
concurrent idempotency + optimistic lock races, job claim/lease/reclaim max3/fencing,
semantic effect uniqueness, independent audit connection/reconciliation, actual roles,
SECURITY DEFINER isolation, fixed-org traversal, actual exact-master/rule/provenance,
material invalidation and approval validity, immutable interface handoffs. Original DB
suite and BE-01..26 remain required at their proper boundaries. Engine ranking/decision
behavior is NOT ours to implement. No blanket DML, DB reset, shared DB, provider call,
live vendor, secrets or public listener. A green offline suite alone is NOT release-ready.
