# Bearing MVP — Database Lookup & Fixture Specification

Public-safe documentation for the PartPilot Bearing MVP additive database slice.

## 1. Scope & Entities

- **Company**: 1 synthetic company `SYN-COMPANY-01`.
- **Warehouses**: 5 leaf warehouses `SYN-WH-01` through `SYN-WH-05`.
  - `SYN-WH-01`: Populated with 5 bearing items and 5 bins.
  - `SYN-WH-02` through `SYN-WH-05`: Empty warehouse leaf nodes.
- **Category / Item Group**: `Bearing`.
- **Items & Bins**: Exactly 5 bearing records in `SYN-WH-01`, each with `actual_qty = 10` and `reserved_qty = 0` (available = 10).

## 2. Source Lineage & Provenance

Item names and specifications verbatim:

| Item Code | Item Name | Dimensions | Suffix Meaning |
|---|---|---|---|
| `SYN-WH01-NTN-6200LLU` | NTN 6200LLU | 10x30x9 mm | contact seal both sides |
| `SYN-WH01-NTN-6801ZZ`  | NTN 6801ZZ  | 12x21x5 mm | metal shield both sides |
| `SYN-WH01-NTN-6900LLB` | NTN 6900LLB | 10x22x6 mm | noncontact seal both sides |
| `SYN-WH01-NTN-6000LLH` | NTN 6000LLH | 10x26x8 mm | low torque both sides |
| `SYN-WH01-NTN-6701LLF` | NTN 6701LLF | 12x18x4 mm | noncontact seal; not equivalent to LLB |

All dimensions and seal descriptions are flagged with `USER-PROVIDED; MANUFACTURER-UNVERIFIED`.
Stock figures and codes are synthetic.

Second-brain catalog notes are indexed at `01-Projects/PartPilot/catalog-notes/manifest.md` with individual warehouse notes (`SYN-WH-01/bearing.md` .. `SYN-WH-05/bearing.md`). Warehouse note retrieval is handled at the application layer, not inside database procedures.

## 3. Run Order & Application

For an isolated bearing target database:

1. `db/001_schema.sql`: Baseline ERP and extension schemas (`erp`, `pp`, `midea`).
2. `db/009_bearing_lookup.sql`: Additive lookup function and indexes.
3. `db/seed/009_bearing_mvp_synth.sql`: Synthetic seed fixture.

In automated test execution, the harness applies these within a single uncommitted transaction with test-level savepoints, rolling back entirely upon completion.

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
- Filter out disabled items, disabled warehouses, and group warehouses (`is_group = true`).
- Ambiguity preservation: if multiple codes share a name in the same scope, all matching rows are returned.
- Availability calculation: `actual_qty - reserved_qty`. Zero-available items (`available_qty = 0`) are returned if the item exists in the bin.
- Empty scope: queries targeting empty warehouses (`SYN-WH-02` .. `SYN-WH-05`) or invalid scopes return 0 rows without fallback.

Indexes added:
- `erp.pp_bearing_item_group_name_code_idx` on `erp.item (item_group, item_name, item_code)`
- `erp.pp_bearing_bin_warehouse_item_idx` on `erp.bin (warehouse, item_code)`

## 5. Limitations & Boundaries

1. **No Fuzzy / Normalization**: No trigram, Levenshtein, regex, phonetic, or case-insensitive matching. Suffixes (LLU, ZZ, LLB, LLH, LLF) must match exact strings. LLF is distinct from LLB.
2. **No Global Fallback**: Searches are strictly scoped to the specified warehouse and company. No cross-warehouse auto-redirects.
3. **No Schema Alterations to Legacy Tables**: Existing columns in `erp.item` are retained unchanged; no new parser tables, vector columns, or embeddings are introduced.
4. **Isolated Slice**: This MVP slice is additive and independent. It does not replace or release unresolved legacy migrations (such as 008 contracts) or existing database test suites.
