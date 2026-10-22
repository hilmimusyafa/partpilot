# Demo purchase orders

Apply migration `015_purchase_orders.sql` after the existing procurement demo
migrations (production also has WhatsApp migration 014). Manager selection via
`pp.demo_choose` inserts a decision; an AFTER INSERT trigger creates the vendor
PO in that same transaction. Invalid invoice values abort the entire decision.
Warehouse decisions produce no PO. Existing decisions made before migration are
not backfilled.

The service role needs only:

```sql
GRANT SELECT ON pp.demo_purchase_order TO pp_demo_api;
```

Use the actual scoped API role if the deployment names it differently. Do not
grant table write/truncate privileges or EXECUTE on `demo_create_purchase_order`.
Existing authorized EXECUTE on `demo_choose` remains the approval entry point.
The trigger function has a fixed search path and PUBLIC execution is revoked.

Authenticated read routes, registered in `backend.demo.app`:

- `GET /api/v1/demo/sourcing-runs/{run_id}/purchase-order` returns
  `{"purchase_order": null}` until a vendor decision, otherwise the snapshot
  plus `id`, `number`, `decision_id`, `run_id`, `created_at` and `pdf_url`.
- `GET /api/v1/demo/purchase-orders/{id}/pdf` downloads the PDF; unknown IDs
  return 404. Both routes inherit demo Basic authentication and no-store headers.

The snapshot stores approved identity, requested quantity, selected quote price,
shipping and tax amounts, an exact decimal subtotal and their total, supplier
label, dummy issuer/shipping information, terms and approval evidence. It omits
internal recovery and production economics. Higher precision quote amounts stay
visible in the PDF, avoiding independently rounded rows that do not add up.

One immutable PO exists per decision and run. No foreign key points to resettable
workflow tables; reset archives the approval/audit while retaining the PO and its
approval evidence. Direct update, delete and truncate are rejected. UUID-based
document identity and a dated unique PO number survive reset without reuse.

The pinned ReportLab renderer uses only the stored snapshot and invariant PDF
metadata. Repeated downloads in the same renderer version are byte-identical.
No agent tool creates or approves POs, and no endpoint transmits a PO or changes
ERP purchasing/stock state. All documents explicitly identify their dummy data
and simulation status.

Validation: `pytest tests/codex/test_purchase_orders.py` uses an owned PostgreSQL
16 cluster with migrations 014, 015 and 016. It covers approval/replay, separate
invoice totals, warehouse behavior, auth, changed quotes, transaction rollback,
role privileges, reset retention and deterministic PDF generation. The PDF-only
test can run without PostgreSQL using `-k pdf_repeatable`.
