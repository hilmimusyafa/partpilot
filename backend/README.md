# PartPilot Backend Database Bundle

This directory contains the database schemas, additive extensions, and synthetic seed fixtures for PartPilot backend services.

## Overview

- `db/001_schema.sql`: Base relational database schema definitions (`midea`, `erp`, and `pp` schemas).
- `db/009_bearing_lookup.sql`: Additive exact lookup function (`pp.lookup_bearing_exact`) and supporting indexes.
- `db/seed/009_bearing_mvp_synth.sql`: Combined synthetic seed fixture with conflict guards, covering 8 items and 8 bins across warehouses `SYN-WH-01` and `SYN-WH-02`.

## Execution Order

Run the following commands from this directory (`backend/`) using a locally configured PostgreSQL connection:

```bash
psql "$PGDATABASE" -f db/001_schema.sql
psql "$PGDATABASE" -f db/009_bearing_lookup.sql
psql "$PGDATABASE" -f db/seed/009_bearing_mvp_synth.sql
```

Do not hardcode database credentials or private connection strings.

## Synthetic Fixture Details

The combined seed fixture provisions:
- 1 Company: `SYN-COMPANY-01` (default currency `IDR`)
- 5 Leaf Warehouses: `SYN-WH-01` through `SYN-WH-05` (`SYN-WH-03`..`SYN-WH-05` remain empty)
- 1 Item Group: `Bearing`
- 8 Items & Bins:
  - 5 items in `SYN-WH-01` (`SYN-WH01-NTN-6200LLU`, `SYN-WH01-NTN-6801ZZ`, `SYN-WH01-NTN-6900LLB`, `SYN-WH01-NTN-6000LLH`, `SYN-WH01-NTN-6701LLF`), each with stock 10, reserved 0.
  - 3 items in `SYN-WH-02` (`G2-BRG-017` stock 8, `G2-BRG-018` stock 14, `G2-BRG-019` stock 9), reserved 0.
- All items belong to category `Bearing`, brand `NTN`, and stock UOM `Nos`.

## Conflict Protection & Idempotency

- Replaying the seed against identical data is safe and produces no state modifications.
- Discrepancies on seed-owned fields (company currency, warehouse configuration, category properties, item details, or stock levels) trigger PostgreSQL exceptions rather than overwriting existing records.

## Scope & Deferrals

- This bundle is strictly backend/database-scoped. Frontend integration is deferred.
- Lookup logic is strictly exact; fuzzy matching and cross-warehouse fallbacks are excluded.
