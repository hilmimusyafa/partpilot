-- Synthetic seed fixture for Bearing MVP (combined WH01 and WH02)
-- 1 Company: SYN-COMPANY-01
-- 5 Leaf Warehouses: SYN-WH-01 to SYN-WH-05 (SYN-WH-01 and SYN-WH-02 populated; SYN-WH-03..05 empty)
-- 1 Item Group: Bearing
-- 8 Items and 8 Bins: 5 items in SYN-WH-01 (stock 10), 3 items in SYN-WH-02 (stock 8, 14, 9), reserved 0.
-- Idempotent: conflict-guarded against seed-owned field mismatch, no-op replay on identical data.

DO $$
BEGIN
    -- Guard 1: erp.company
    IF EXISTS (
        SELECT 1 FROM erp.company
        WHERE name = 'SYN-COMPANY-01'
          AND default_currency IS DISTINCT FROM 'IDR'
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.company: mismatch for SYN-COMPANY-01';
    END IF;

    -- Guard 2: erp.warehouse (5 leaf warehouses)
    IF EXISTS (
        SELECT 1 FROM erp.warehouse
        WHERE name IN ('SYN-WH-01', 'SYN-WH-02', 'SYN-WH-03', 'SYN-WH-04', 'SYN-WH-05')
          AND (
            warehouse_name IS DISTINCT FROM name OR
            company IS DISTINCT FROM 'SYN-COMPANY-01' OR
            is_group IS DISTINCT FROM false OR
            disabled IS DISTINCT FROM false OR
            parent_warehouse IS NOT NULL
          )
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.warehouse: mismatch for synthetic warehouse';
    END IF;

    -- Guard 3: erp.item_group
    IF EXISTS (
        SELECT 1 FROM erp.item_group
        WHERE name = 'Bearing'
          AND (
            is_group IS DISTINCT FROM false OR
            parent_item_group IS NOT NULL
          )
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.item_group: mismatch for Bearing';
    END IF;

    -- Guard 4: erp.item (8 seed items)
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('SYN-WH01-NTN-6200LLU', 'NTN 6200LLU', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x30x9 mm; LLU contact both sides'),
            ('SYN-WH01-NTN-6801ZZ',  'NTN 6801ZZ',  'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x21x5 mm; ZZ metal shields both sides'),
            ('SYN-WH01-NTN-6900LLB', 'NTN 6900LLB', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x22x6 mm; LLB noncontact both sides'),
            ('SYN-WH01-NTN-6000LLH', 'NTN 6000LLH', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x26x8 mm; LLH low torque both sides'),
            ('SYN-WH01-NTN-6701LLF', 'NTN 6701LLF', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x18x4 mm; LLF noncontact; not equivalent to LLB'),
            ('G2-BRG-017', 'LAHER ALUR 10X30X9 KARET RAPAT DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-017; label: NTN / 6200 / LLU; brand: NTN; base: 6200; suffix: LLU; location: B-02-03; user quantity: 8 pcs; stock_uom Nos represents individual pieces. User explicitly identifies this label as NTN 6200LLU, matching the provided Gudang1 NTN 6200LLU label; not inferred from name similarity.'),
            ('G2-BRG-018', 'LAHER ALUR 10X30X9 PLAT DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-018; label: NTN / 6200 / ZZ; brand: NTN; base: 6200; suffix: ZZ; location: B-02-04; user quantity: 14 pcs; stock_uom Nos represents individual pieces.'),
            ('G2-BRG-019', 'LAHER ALUR 10X30X9 KARET NONKONTAK DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-019; label: NTN / 6200 / LLB; brand: NTN; base: 6200; suffix: LLB; location: B-02-05; user quantity: 9 pcs; stock_uom Nos represents individual pieces.')
        ) AS v(code, name, grp, uom, brand, descr)
        JOIN erp.item i ON i.item_code = v.code
        WHERE i.item_name IS DISTINCT FROM v.name
           OR i.item_group IS DISTINCT FROM v.grp
           OR i.stock_uom IS DISTINCT FROM v.uom
           OR i.brand IS DISTINCT FROM v.brand
           OR i.description IS DISTINCT FROM v.descr
           OR i.disabled IS DISTINCT FROM false
           OR i.is_stock_item IS DISTINCT FROM true
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.item: mismatch for seed-owned item';
    END IF;

    -- Guard 5: erp.bin (8 seed bins)
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('SYN-WH01-NTN-6200LLU', 'SYN-WH-01', 10::numeric, 0::numeric),
            ('SYN-WH01-NTN-6801ZZ',  'SYN-WH-01', 10::numeric, 0::numeric),
            ('SYN-WH01-NTN-6900LLB', 'SYN-WH-01', 10::numeric, 0::numeric),
            ('SYN-WH01-NTN-6000LLH', 'SYN-WH-01', 10::numeric, 0::numeric),
            ('SYN-WH01-NTN-6701LLF', 'SYN-WH-01', 10::numeric, 0::numeric),
            ('G2-BRG-017',           'SYN-WH-02', 8::numeric,  0::numeric),
            ('G2-BRG-018',           'SYN-WH-02', 14::numeric, 0::numeric),
            ('G2-BRG-019',           'SYN-WH-02', 9::numeric,  0::numeric)
        ) AS v(code, wh, actual, reserved)
        JOIN erp.bin b ON b.item_code = v.code AND b.warehouse = v.wh
        WHERE b.actual_qty IS DISTINCT FROM v.actual
           OR b.reserved_qty IS DISTINCT FROM v.reserved
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.bin: mismatch for seed-owned bin';
    END IF;

    -- Guard 6: erp.bin (empty leaf warehouses must not contain seed items)
    IF EXISTS (
        SELECT 1 FROM erp.bin
        WHERE warehouse IN ('SYN-WH-03', 'SYN-WH-04', 'SYN-WH-05')
          AND item_code IN (
            'SYN-WH01-NTN-6200LLU', 'SYN-WH01-NTN-6801ZZ', 'SYN-WH01-NTN-6900LLB',
            'SYN-WH01-NTN-6000LLH', 'SYN-WH01-NTN-6701LLF',
            'G2-BRG-017', 'G2-BRG-018', 'G2-BRG-019'
          )
    ) THEN
        RAISE EXCEPTION 'Seed conflict in erp.bin: seed item bin present in empty warehouse';
    END IF;
END $$;

-- 1. Company
INSERT INTO erp.company (name, default_currency)
VALUES ('SYN-COMPANY-01', 'IDR')
ON CONFLICT (name) DO NOTHING;

-- 2. Warehouses (5 leaf warehouses, one company, no parent group)
INSERT INTO erp.warehouse (name, warehouse_name, company, is_group, disabled, parent_warehouse)
VALUES
  ('SYN-WH-01', 'SYN-WH-01', 'SYN-COMPANY-01', false, false, NULL),
  ('SYN-WH-02', 'SYN-WH-02', 'SYN-COMPANY-01', false, false, NULL),
  ('SYN-WH-03', 'SYN-WH-03', 'SYN-COMPANY-01', false, false, NULL),
  ('SYN-WH-04', 'SYN-WH-04', 'SYN-COMPANY-01', false, false, NULL),
  ('SYN-WH-05', 'SYN-WH-05', 'SYN-COMPANY-01', false, false, NULL)
ON CONFLICT (name) DO NOTHING;

-- 3. Item Group
INSERT INTO erp.item_group (name, is_group)
VALUES ('Bearing', false)
ON CONFLICT (name) DO NOTHING;

-- 4. Bearing Items (8 items across WH01 and WH02)
INSERT INTO erp.item (
    item_code,
    item_name,
    item_group,
    stock_uom,
    brand,
    description,
    is_stock_item,
    disabled
) VALUES
  ('SYN-WH01-NTN-6200LLU', 'NTN 6200LLU', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x30x9 mm; LLU contact both sides', true, false),
  ('SYN-WH01-NTN-6801ZZ',  'NTN 6801ZZ',  'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x21x5 mm; ZZ metal shields both sides', true, false),
  ('SYN-WH01-NTN-6900LLB', 'NTN 6900LLB', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x22x6 mm; LLB noncontact both sides', true, false),
  ('SYN-WH01-NTN-6000LLH', 'NTN 6000LLH', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 10x26x8 mm; LLH low torque both sides', true, false),
  ('SYN-WH01-NTN-6701LLF', 'NTN 6701LLF', 'Bearing', 'Nos', 'NTN', 'USER-PROVIDED; MANUFACTURER-UNVERIFIED: 12x18x4 mm; LLF noncontact; not equivalent to LLB', true, false),
  ('G2-BRG-017', 'LAHER ALUR 10X30X9 KARET RAPAT DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-017; label: NTN / 6200 / LLU; brand: NTN; base: 6200; suffix: LLU; location: B-02-03; user quantity: 8 pcs; stock_uom Nos represents individual pieces. User explicitly identifies this label as NTN 6200LLU, matching the provided Gudang1 NTN 6200LLU label; not inferred from name similarity.', true, false),
  ('G2-BRG-018', 'LAHER ALUR 10X30X9 PLAT DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-018; label: NTN / 6200 / ZZ; brand: NTN; base: 6200; suffix: ZZ; location: B-02-04; user quantity: 14 pcs; stock_uom Nos represents individual pieces.', true, false),
  ('G2-BRG-019', 'LAHER ALUR 10X30X9 KARET NONKONTAK DUA SISI', 'Bearing', 'Nos', 'NTN', 'SIMULASI; USER-PROVIDED; MANUFACTURER-UNVERIFIED; local stock code (not MPN): G2-BRG-019; label: NTN / 6200 / LLB; brand: NTN; base: 6200; suffix: LLB; location: B-02-05; user quantity: 9 pcs; stock_uom Nos represents individual pieces.', true, false)
ON CONFLICT (item_code) DO NOTHING;

-- 5. Bins (8 bins across SYN-WH-01 and SYN-WH-02)
INSERT INTO erp.bin (
    item_code,
    warehouse,
    actual_qty,
    reserved_qty
) VALUES
  ('SYN-WH01-NTN-6200LLU', 'SYN-WH-01', 10, 0),
  ('SYN-WH01-NTN-6801ZZ',  'SYN-WH-01', 10, 0),
  ('SYN-WH01-NTN-6900LLB', 'SYN-WH-01', 10, 0),
  ('SYN-WH01-NTN-6000LLH', 'SYN-WH-01', 10, 0),
  ('SYN-WH01-NTN-6701LLF', 'SYN-WH-01', 10, 0),
  ('G2-BRG-017',           'SYN-WH-02', 8,  0),
  ('G2-BRG-018',           'SYN-WH-02', 14, 0),
  ('G2-BRG-019',           'SYN-WH-02', 9,  0)
ON CONFLICT (item_code, warehouse) DO NOTHING;
