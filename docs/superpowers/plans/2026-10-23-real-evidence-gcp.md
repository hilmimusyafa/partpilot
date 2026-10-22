# PartPilot real evidence and GCP implementation plan

> **For agentic workers:** Apply the approved user scope with parallel file ownership; verify each component before deployment.

**Goal:** Run a source-backed food-conveyor maintenance and sourcing demo. Active provider remains 9router per the user's later instruction; Vertex AI project `hackathon-primestep-16` is prepared as an optional adapter pending credentials and live verification.

**Architecture:** Retain the existing durable WO, procurement, stock and WhatsApp workflow. Add persisted external evidence and a bounded tool-using maintenance assessment; extend supported complete-unit identities; calculate published-rate economics separately from contribution-margin economics. Deploy an isolated release after database backup and regression tests.

**Tech stack:** Python/FastAPI, PostgreSQL16, Next.js static frontend, Docker Compose, 9router with optional Vertex AI, Baileys WhatsApp.

**Spec:** User-approved source packages in `outputs/PartPilot-Kasus-Nyata` and `outputs/PartPilot-Downtime-Data-Asli`, plus `work/feasibility-code-review.md`.

## Global constraints

- Historical cases and technical facts must be sourced OEM publications with URL, locator, hash and missing values preserved. Never create fictitious historical WOs.
- RHP PSF20CR is the requested complete flange unit; RHP PSF20/LP99 is a candidate requiring engineering and hygiene review. No automatic interchangeability claim.
- Stocks, vendors, prices, delivery times and local operating schedules are explicitly synthetic.
- SS-E-2054 reports 3332 in printed dollar units/hour; ISO currency and price year are unknown. Any IDR conversion is an explicitly acknowledged simulation assumption, never a sourced FX fact.
- No remaining-useful-life or predictive-maintenance claim. Assessment produces likely causes and inspections, not a confirmed diagnosis.
- WhatsApp test outbound recipient must be `6282178830078`; live messaging starts only after notifying the user. No other recipient may receive messages.
- Existing authorization covers implementation, evidence ingestion and demo deployment. Secrets remain server-side and never appear in logs or deliverables.

## Review focus

1. An explicitly selected Vertex provider must fail clearly when credentials are missing; no silent provider fallback. The user's approved active provider is 9router.
2. Candidate parts must not bypass technical approval or replace exact stock silently.
3. Currency assumptions must not relabel published dollars as actual IDR costs.
4. Repeated requests must not create duplicate WOs, decisions or WhatsApp messages.
5. Model text and retrieved evidence cannot execute arbitrary tools or invent local history.

## Tasks and ownership

- [x] **Gateway (vps_audit):** `backend/wo/gateway.py`, new Vertex adapter, dependencies and tests. Preserve completion interface; add `call_agent_turn(messages, tools, ...)` with native function calls and metadata. Test missing credentials, malformed output, bounded tokens and tool-result round trip; live Vertex verification remains deferred per the user until authenticated.
- [x] **Identity (technical_sources):** WO parser/matcher, procurement identity, WhatsApp extractor, migration021 and tests. Legacy 6xxx stays `{brand,base,suffix}`. Known PSF units additionally carry manufacturer/full_designation/unit_scope. Test insert/unit distinction, exact-versus-candidate mismatch and downstream SQL/PO validation.
- [x] **Evidence and assessment (maintenance_evidence):** migration020, `backend/maintenance/`, seed script and tests. Persist source facts and bounded tool trace; expose `/api/v1/maintenance/evidence`, `/assess`, `/assessments/{id}`. Validate citations and return a provisional draft requiring technician confirmation.
- [x] **Scenario and economics (root):** new benchmark model/calculator, comparison integration, migration022 fixture, confirmed draft/engineering linkage, food-scenario UI. Test schedule intersections, unknown currency, missing conversion, stock and alternative approval gates.
- [x] **Messaging safety (root):** normalize and enforce one-number allowlist in start/send path; explicit UI trigger instead of automatic live sends. Test nonallowlisted delivery blocked before transport call.
- [x] **Integration (root):** mount routes, configure approved 9router runtime and optional GCP adapter, backup DB, install migrations and source data, build and deploy isolated release, run maintained regression plus browser and WhatsApp demo. Record actual outcomes and unresolved external blockers.
- [x] **Documentation (root):** update README, short DEMO_GUIDE.md, DATA_AND_AGENTIC_AI.md and implementation test results; copy final user-facing markdown into outputs.

## Execution ledger

- Source snapshot preserved from deployed release including its pre-existing uncommitted changes. New local branch `feature/real-evidence-gcp`; production source untouched.
- Native Vertex ADC missing in initial host/container inspection; user asked asynchronously about competition auth. Implementation continues independently.
- User explicitly chose to retain 9router when no GCP credential was found. Active release uses 9router native tool calling; Vertex is not claimed as live-tested.
- Applied migrations020–022 and ingested10 immutable evidence records after a private database/config backup. Active release: `releases/evidence-20261023`.
- Maintained non-live regression:291 passed; authenticated gateway regression:1 passed. Initial bare pytest exposed obsolete legacy paths, missing test-environment dependency, and an outdated live-test migration fixture; these results are reported separately.
- Browser assessment completed using4 evidence tool calls. Browser WO test exposed a category-span validator issue; regression fix and source-backed food WO knowledge are being verified before the remaining sourcing/WhatsApp test.

- Final release evidence-20261023-r4 active. Migrations020-023 and10 evidence records verified; exact WhatsApp flow completed through warehouse decision, separate candidate flow completed through demo PO.
- Final targeted suites:117 WhatsApp/date cases and97 identity/catalog/food/warehouse/procurement cases passed in isolated PostgreSQL. Full recovery horizon regression:32 passed. Final public runtime smoke passed at04:39WIB, including fresh OEM provenance for both SKU identities across five warehouses.
- README, demo guide, source/agentic explanation and verification report finalized. GCP credentials/live Vertex validation remain explicitly outside the revised active-provider scope.
