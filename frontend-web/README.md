# PartPilot frontend

The existing `frontend-web` application is the only UI. It exports static Next.js pages; all work-order, sourcing, negotiation, decision and PO data comes from the authenticated same-origin `/api/v1` backend. Browser requests preserve existing session credentials. WhatsApp connection/QR remains on its private dedicated page.

## Original design audit (2026-10-22)

Reference inspected directly with `git show 042c913:frontend-web/src/app/...`:

| Original page | Original composition reused | Live adaptation |
| --- | --- | --- |
| `page.tsx` | Centered role-selection card, logo, gradient role menu | Existing landing page retained. |
| `technician/page.tsx` | `max-w-5xl` form, white rounded panel, icon/title, description, two-column machine/quantity stepper, urgency button row, yellow Find Parts and navy Save Draft | Fixed demo machine plus server warehouse selector, quantity starts at 6, physical-description placeholder with outer diameter 30 mm. Presets still come from backend. |
| `technician/clarification/page.tsx` | Centered yellow AI question banner, form card, yellow submission action | Actual server-generated brand/measurement/seal questions and persisted answers. No fabricated AI question or success state. |
| `manager/page.tsx` | `max-w-7xl`, Order List heading with search alongside, status pills, urgency filter/create action, flush gray-header table | Real work orders, counts, urgency/search filters and automatic updates. Columns describe work orders rather than invented vendor prices. |
| `manager/decision/page.tsx` | `max-w-6xl`, Meja Keputusan heading, yellow back control, yellow recommendation banner, wide gray-header comparison table, rounded approval popup | Actual total-cost recommendation, global ranks retained within separate warehouse/vendor tables, real pending/incomplete/expired states, vendor approval generates a demo PO; warehouse selection shows confirmation only. |

Shared original colors (`#F1F3F6`, `#0F274A`, `#F5C767`, `#F6E5B4`, `#EAECEF`), font-sans typography, logo assets, radii and spacing are retained. Additional stock evidence, transport controls, WhatsApp conversations and reset controls remain necessary operational UI. The old hard-coded suppliers, invented downtime numbers, fake notifications and pretend actions are not restored.

## Decision behavior

- Sort complete options by exact decimal `future_relevant_option_total_unrounded` (rounded value only as an older-response fallback), then canonical `source_kind` and `source_id`, matching the backend. No monetary value is converted to floating point for ranking. Assign a global rank, then partition into warehouse/vendor sections without renumbering. Unrankable options appear with reasons within the matching section. Expired complete quotes are disabled using the comparison's authoritative `unexpired_option_ids`.
- Recommend the cheapest complete currently eligible option. Coverage gaps are explicit. The backend remains authoritative for money, availability and final approval validation.
- Negotiation waits only on explicit `negotiation_pending`; zero counteroffers alone does not imply a pending negotiation. Frozen plan skip reasons and positive vendor targets are displayed when available.
- Vendor approval uses the existing versioned/idempotent decision endpoint. Afterwards, and after page reload, fetch `GET /demo/sourcing-runs/{run_id}/purchase-order`. The PO number and authenticated `/demo/purchase-orders/{id}/pdf` download link are displayed. A failed document read has its own retry and cannot repeat the manager decision.
- Warehouse approval shows a recorded-selection popup, never fetches/creates a PO, and does not mutate inventory. No email or WhatsApp PO dispatch is performed.

## Verification

From the repository root:

```text
npm run lint --workspace=frontend-web
npm run build --workspace=frontend-web
node frontend-web/tests/ranking.cjs
node frontend-web/tests/demo-ui-smoke.cjs
```

The ranking test uses Node's native TypeScript stripping and checks precision beyond IEEE-754, equal rounded prices, canonical ties, scientific notation and older-response fallback. The standalone browser smoke test needs Playwright available via normal Node resolution or `NODE_PATH`, and an installed Chrome channel (override `PLAYWRIGHT_CHANNEL` if needed). It serves the production `out/` build on an ephemeral loopback port and intercepts every API request with synthetic fixtures. It never reaches a live API, sends a WhatsApp message, or resets a demo.

It checks quantity controls, three clarification fields, deliberately unsorted warehouse/vendor costs and global ranks, skipped negotiation, disabled expired quote, manager vendor approval, PO read failure/retry without re-approval, PO persistence after reload, warehouse confirmation without PO, mobile page overflow, manager search and browser runtime errors. Screenshots are written to ignored `.next/ui-smoke/` for desktop and mobile visual inspection.

This is frontend contract verification. Real database totals, PDF contents, authorization and full simulator flows must also be tested with the integrated backend.
