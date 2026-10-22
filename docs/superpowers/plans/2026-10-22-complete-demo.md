# Complete bearing procurement demo implementation plan

**Goal:** Restore the original main frontend design, demonstrate physical-description clarification through cross-warehouse/vendor comparison, one best-total-based negotiation round and a generated PT PartPilot PO after manager selection.

**Authorization:** User explicitly asked to continue unattended, implement and test; defer tests requiring their participation. Prior deployment and Git publication authorization remains. Do not send extra live demo messages, reset their active run, or issue a real purchase as a testing shortcut.

**Architecture:** Existing Python/PostgreSQL demo remains authoritative. Reuse original frontend at 042c913 rather than inventing a second frontend. Additive migrations persist negotiation basis and immutable PO snapshots. Existing one-counteroffer-per-vendor constraint remains. Model extracts evidence; deterministic backend computes money and creates documents. Manager selection is the PO approval gate; generated documents are demo purchase orders, not automatically transmitted.

## Decisions
- Current main has frontend-web; inspect original 042c913 source and preserve its page composition, typography, colors and components as far as functional integration permits.
- Best means lowest complete eligible future relevant total (goods + shipping + tax + recovery + future lost contribution), warehouse or vendor. Freeze one basis per run and one target per vendor. Revisions cannot start another round. New late vendors can join the same round once; no competitor/internal costs appear in outgoing text.
- Target unit price = floor_IDR((0.90 * frozen best total - vendor non-item costs) / requested quantity). Only positive targets lower than that vendor's current price are sent. Negative/unachievable targets are recorded as skipped, never sent as negative/zero offers.
- Comparisons rank globally ascending total but present warehouse and vendor sections separately, preserving rank badges and clear missing/expired statuses.
- Proper main demo uses quantity6: origin4, warehouse2=8 under G2-BRG-017, vendors also queried. Initial input mentions only outer diameter30mm; chatbot asks for brand, remaining measurements and seal. Use simulator for unattended full end-to-end tests; do not require a person to answer WhatsApp.
- Selecting a vendor atomically creates one immutable PO snapshot using selected quote quantity/prices/identity; selecting warehouse creates no PO and shows a confirmation popup. PO includes PT PartPilot, explicit dummy addresses/terms and correct database totals. Downtime/recovery costs belong to decision comparison, never vendor invoice totals.

## Tasks
- [x] Frontend owner: source audit, restore original layouts, separate ranked sections, PO links and transfer popup; lint/build and browser checks.
- [x] PO owner: migration015, protected snapshot/PDF endpoints, atomic unique decision-linked generation, reset retention and tests. Contract GET /api/v1/demo/sourcing-runs/{run_id}/purchase-order returns {purchase_order:null|{id,number,...}}, GET /api/v1/demo/purchase-orders/{id}/pdf downloads authenticated PDF. No outbound PO dispatch.
- [x] Root: shared negotiation planning using pure comparison economics and frozen database ledger, migration016, simulator+WA integration, tests for warehouse best, vendor best, infeasible target, duplicate/restart, changed terms.
- [x] Root: descriptive presets and exact guide follow-up answers; owned test+deployed browser full simulation including warehouse match and vendor decision/PO.
- [x] Independent review: protected approval boundary, money/rank consistency, duplicate PO/counteroffer, stale/expired quotes, reset semantics, no private data in Git.
- [x] Deploy migrations with backup, rebuild and health check, update guide/evidence, commit/push. Report live WhatsApp tests requiring participants as deferred.

## Verification evidence

- 145 isolated backend tests passed, 1 explicit live-gateway test deselected; one non-failing upstream Starlette/httpx deprecation warning.
- Frontend lint, production build, synthetic browser checks and exact-decimal ranking checks passed.
- Deployed browser independently used the real gateway: incomplete outer diameter -> three clarification questions -> NTN 6200LLU; origin available4, WH02 alias available8; simulator one round with best1,170,000 and target1,053,000.
- Two persisted browser flows passed: manager vendor approval generated exactly one PDF, quantity6, unit129,666, invoice802,996, retained after reload; warehouse choice showed popup and returned no PO. No browser errors or extra WhatsApp conversations.
- Actual generated one-page PDF rendered and visually inspected. No clipping; snapshot values agree with selected quote and comparison, excluding internal250,000 recovery cost.
- Additive migrations/grants applied after private backup; API health200 and existing WhatsApp connection preserved. No live reset or extra recipient outreach used for testing.
- Independent final review found no blocker. New actual WhatsApp negotiation replies remain deferred until participants are available.
