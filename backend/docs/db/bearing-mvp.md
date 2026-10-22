# Bearing MVP — Database Lookup & Fixture Specification

Public-safe documentation for the PartPilot Bearing MVP additive database slice and combined synthetic seed fixture. Frontend application implementation is deferred.

## 1. Scope & Entities

- **Company**: 1 synthetic company `SYN-COMPANY-01` (default currency `IDR`).
- **Warehouses**: 5 leaf warehouses `SYN-WH-01` through `SYN-WH-05` (all with `parent_warehouse = NULL`, `is_group = false`, `disabled = false`).
  - `SYN-WH-01`: Populated with 5 bearing items and 5 bins.
  - `SYN-WH-02`: Populated with 3 user bearing items and 3 bins.
  - `SYN-WH-03` through `SYN-WH-05`: Empty leaf warehouse nodes.
- **Category / Item Group**: `Bearing` (`is_group = false`, `parent_item_group = NULL`).
- **Items & Bins**: Exactly 8 bearing records across `SYN-WH-01` and `SYN-WH-02`, all with `reserved_qty = 0`, `item_group = 'Bearing'`, `stock_uom = 'Nos'`, `brand = 'NTN'`.

## 2. Source Lineage & Provenance

Exact 8 records cataloged across `SYN-WH-01` and `SYN-WH-02`:

| Item Code | Item Name | Warehouse | Quantity | Stock UOM | Brand | Description |
|---|---|---|---|---|---|---|
| `SYN-WH01-NTN-6200LLU` | NTN 6200LLU | SYN-WH-01 | 10 | Nos | NTN | USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x30x9 mm; LLU contact both sides |
| `SYN-WH01-NTN-6801ZZ` | NTN 6801ZZ | SYN-WH-01 | 10 | Nos | NTN | USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x21x5 mm; ZZ metal shields both sides |
| `SYN-WH01-NTN-6900LLB` | NTN 6900LLB | SYN-WH-01 | 10 | Nos | NTN | USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x22x6 mm; LLB noncontact both sides |
| `SYN-WH01-NTN-6000LLH` | NTN 6000LLH | SYN-WH-01 | 10 | Nos | NTN | USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x26x8 mm; LLH low torque both sides |
| `SYN-WH01-NTN-6701LLF` | NTN 6701LLF | SYN-WH-01 | 10 | Nos | NTN | USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x18x4 mm; LLF noncontact; not equivalent to LLB |
| `G2-BRG-017` | LAHER ALUR 10X30X9 KARET RAPAT DUA SISI | SYN-WH-02 | 8 | Nos | NTN | SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-017; label: NTN / 6200 / LLU; brand: NTN; base: 6200; suffix: LLU; location: B-02-03; user quantity: 8 pcs; stock_uom Nos represents individual pieces. User explicitly identifies this label as NTN 6200LLU, matching the provided Gudang1 NTN 6200LLU label; not inferred from name similarity. |
| `G2-BRG-018` | LAHER ALUR 10X30X9 PLAT DUA SISI | SYN-WH-02 | 14 | Nos | NTN | SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-018; label: NTN / 6200 / ZZ; brand: NTN; base: 6200; suffix: ZZ; location: B-02-04; user quantity: 14 pcs; stock_uom Nos represents individual pieces. |
| `G2-BRG-019` | LAHER ALUR 10X30X9 KARET NONKONTAK DUA SISI | SYN-WH-02 | 9 | Nos | NTN | SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-019; label: NTN / 6200 / LLB; brand: NTN; base: 6200; suffix: LLB; location: B-02-05; user quantity: 9 pcs; stock_uom Nos represents individual pieces. |

All WH01 specifications retain user-provided dimensions and seal descriptions.
All WH02 specifications retain simulation, local-code-not-MPN, location, and label metadata verbatim.
`stock_uom` value `Nos` represents individual pieces.

## 3. Run Order & Application

Execute the following portable commands from the repository root using a locally configured connection:

```bash
psql "$PGDATABASE" -f backend/db/001_schema.sql
psql "$PGDATABASE" -f backend/db/009_bearing_lookup.sql
psql "$PGDATABASE" -f backend/db/seed/009_bearing_mvp_synth.sql
```

Do not execute with hardcoded credentials or literal connection strings.

## 4. Contract: `pp.lookup_bearing_exact`

Signature:
```sql
pp.lookup_bearing_exact(
    p_company   text,
    p_category  text,
    p_warehouse text,
    p_item_name text
)
RETURNS TABLE (
    item_code     text,
    item_name     text,
    description   text,
    warehouse     text,
    actual_qty    numeric,
    reserved_qty  numeric,
    available_qty numeric
)
LANGUAGE sql
STABLE
SECURITY INVOKER;
```

Semantics:
- Strict equality matching across `company`, `category`, `warehouse`, and `item_name`.
- Filters out disabled items (`i.disabled = false`), disabled warehouses (`w.disabled = false`), and group warehouses (`w.is_group = false`).
- Returns `available_qty = actual_qty - reserved_qty`.
- Scoped strictly to warehouse: querying `SYN-WH-02` with WH01 item names or `SYN-WH-01` with WH02 item names returns 0 rows.
- WH02 local names do not become label aliases: searching `SYN-WH-02` for `NTN 6200LLU` returns 0 rows.
- Empty warehouses (`SYN-WH-03` through `SYN-WH-05`) return 0 rows.

Indexes added:
- `erp.pp_bearing_item_group_name_code_idx` on `erp.item (item_group, item_name, item_code)`
- `erp.pp_bearing_bin_warehouse_item_idx` on `erp.bin (warehouse, item_code)`

## 5. Conflict Guards & Idempotency

The synthetic seed fixture enforces explicit conflict rejection guards:
- Replaying the seed against identical database state is an idempotent no-op. Full table snapshots before and after replay remain identical.
- Any conflict on seed-owned fields (currency mismatch on company, disabled state or hierarchy on warehouse, group flag on item group, name or description mismatch on item, actual or reserved quantity mismatch on bin) raises a PostgreSQL exception.
- Conflicting updates are never silently overwritten or ignored.

## 6. Limitations & Boundaries

1. **No Fuzzy Matching**: Case-sensitive and exact-string matching only. No normalization, typo-tolerance, or partial substring lookups.
2. **No Cross-Warehouse Fallbacks**: Searches are strictly isolated to the requested warehouse scope.
3. **Additive Slice**: Preserves original schemas and table structures without adding columns or altering legacy tables.
4. **Deferred Scope**: Frontend implementation is deferred to future milestones.
