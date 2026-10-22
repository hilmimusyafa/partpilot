-- Additive fixture upgrade for the explicitly dedicated synthetic demo only.
-- Historical seed009 remains unchanged. No reset, workflow truncate, or live
-- stock overwrite: old runs, WhatsApp messages and PO snapshots are untouched.
DO $$
DECLARE control_row record; fixture record; baseline_row jsonb; already_applied boolean;
 fixtures jsonb := '[
  {"warehouse":"SYN-WH-03","code":"G3-LHR-031","name":"BEARING KONVEYOR 10X30X9 SEGEL KONTAK G3","qty":2,
   "description":"SIMULASI; USER-REQUESTED DEMO FIXTURE; MANUFACTURER-UNVERIFIED; explicit label: NTN / 6200 / LLU; dimensions: 10x30x9 mm; LLU contact both sides; local code G3-LHR-031 is not an MPN; mapping explicitly assigned for this synthetic warehouse fixture, not inferred from dimensions."},
  {"warehouse":"SYN-WH-04","code":"G4-SPR-041","name":"G4 LAHER MOTOR NTN 6200 LLU","qty":3,
   "description":"SIMULASI; USER-REQUESTED DEMO FIXTURE; MANUFACTURER-UNVERIFIED; explicit label: NTN / 6200 / LLU; dimensions: 10x30x9 mm; LLU contact both sides; local code G4-SPR-041 is not an MPN; mapping explicitly assigned for this synthetic warehouse fixture, not inferred from dimensions."},
  {"warehouse":"SYN-WH-05","code":"G5-BRG-051","name":"BANTALAN 10X30X9 KARET RAPAT DUA SISI G5","qty":1,
   "description":"SIMULASI; USER-REQUESTED DEMO FIXTURE; MANUFACTURER-UNVERIFIED; explicit label: NTN / 6200 / LLU; dimensions: 10x30x9 mm; LLU contact both sides; local code G5-BRG-051 is not an MPN; mapping explicitly assigned for this synthetic warehouse fixture, not inferred from dimensions."}
 ]'::jsonb;
BEGIN
 PERFORM pg_advisory_xact_lock(72490122);
 IF current_database()<>'partpilot_demo' AND current_database() !~ '^partpilot_test_core_[0-9a-f]{16}$' THEN
  RAISE EXCEPTION 'five_warehouse_demo_scope_required';
 END IF;
 IF to_regclass('pp.demo_control') IS NULL THEN RAISE EXCEPTION 'five_warehouse_demo_scope_required'; END IF;
 SELECT * INTO control_row FROM pp.demo_control WHERE singleton FOR UPDATE;
 IF NOT FOUND OR control_row.database_name<>current_database()
  OR control_row.dataset_tag<>'synthetic-bearing-demo-v1' OR NOT control_row.reset_enabled
  OR jsonb_typeof(control_row.stock_baseline) IS DISTINCT FROM 'array'
  OR EXISTS(SELECT 1 FROM erp.company WHERE name<>'SYN-COMPANY-01')
  OR (SELECT count(*) FROM erp.warehouse WHERE name IN ('SYN-WH-01','SYN-WH-02','SYN-WH-03','SYN-WH-04','SYN-WH-05')
      AND company='SYN-COMPANY-01' AND NOT disabled AND NOT is_group AND parent_warehouse IS NULL)<>5
 THEN RAISE EXCEPTION 'five_warehouse_demo_scope_required'; END IF;

 CREATE TABLE IF NOT EXISTS pp.demo_warehouse_display (
  warehouse_id text PRIMARY KEY REFERENCES erp.warehouse(name),
  name text NOT NULL CHECK(length(name)>0),
  address text NOT NULL CHECK(position('DUMMY' in address)>0),
  simulated boolean NOT NULL DEFAULT true CHECK(simulated)
 );
 CREATE TABLE IF NOT EXISTS pp.demo_fixture_revision (
  version text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
 );
 SELECT EXISTS(SELECT 1 FROM pp.demo_fixture_revision WHERE version='five-warehouse-v1') INTO already_applied;

 FOR fixture IN SELECT * FROM jsonb_to_recordset(fixtures)
  AS f(warehouse text,code text,name text,qty numeric,description text)
 LOOP
  IF EXISTS(SELECT 1 FROM erp.item WHERE item_code=fixture.code AND
    (item_name IS DISTINCT FROM fixture.name OR item_group IS DISTINCT FROM 'Bearing'
     OR stock_uom IS DISTINCT FROM 'Nos' OR brand IS DISTINCT FROM 'NTN'
     OR description IS DISTINCT FROM fixture.description OR disabled OR NOT is_stock_item))
   OR EXISTS(SELECT 1 FROM erp.bin WHERE item_code=fixture.code AND warehouse<>fixture.warehouse)
  THEN RAISE EXCEPTION 'five_warehouse_fixture_conflict: %',fixture.code; END IF;
  IF NOT already_applied AND EXISTS(SELECT 1 FROM erp.bin WHERE item_code=fixture.code AND warehouse=fixture.warehouse
      AND (actual_qty<>fixture.qty OR reserved_qty<>0))
  THEN RAISE EXCEPTION 'five_warehouse_fixture_stock_conflict: %',fixture.code; END IF;
  INSERT INTO erp.item(item_code,item_name,item_group,stock_uom,brand,description,is_stock_item,disabled)
  VALUES(fixture.code,fixture.name,'Bearing','Nos','NTN',fixture.description,true,false)
  ON CONFLICT(item_code) DO NOTHING;
  INSERT INTO erp.bin(item_code,warehouse,actual_qty,reserved_qty)
  VALUES(fixture.code,fixture.warehouse,fixture.qty,0) ON CONFLICT(item_code,warehouse) DO NOTHING;

  SELECT value INTO baseline_row FROM jsonb_array_elements(control_row.stock_baseline)
   WHERE value->>'item_code'=fixture.code AND value->>'warehouse'=fixture.warehouse;
  IF FOUND THEN
   IF (baseline_row->>'actual_qty')::numeric IS DISTINCT FROM fixture.qty
    OR (baseline_row->>'reserved_qty')::numeric IS DISTINCT FROM 0::numeric
   THEN RAISE EXCEPTION 'five_warehouse_fixture_baseline_conflict: %',fixture.code; END IF;
  ELSE
   IF already_applied THEN RAISE EXCEPTION 'five_warehouse_fixture_baseline_missing: %',fixture.code; END IF;
   SELECT to_jsonb(b) INTO baseline_row FROM erp.bin b WHERE item_code=fixture.code AND warehouse=fixture.warehouse;
   control_row.stock_baseline=control_row.stock_baseline||jsonb_build_array(baseline_row);
  END IF;
 END LOOP;
 UPDATE pp.demo_control SET stock_baseline=control_row.stock_baseline WHERE singleton;
 INSERT INTO pp.demo_warehouse_display(warehouse_id,name,address,simulated) VALUES
  ('SYN-WH-01','Gudang 1 - Pabrik AC Cikarang','Jl. Contoh Perakitan AC No. 1, Cikarang Utara, Bekasi - ALAMAT DUMMY',true),
  ('SYN-WH-02','Gudang 2 - Suku Cadang Bekasi','Jl. Contoh Suku Cadang No. 2, Bekasi - ALAMAT DUMMY',true),
  ('SYN-WH-03','Gudang 3 - Perawatan Karawang','Jl. Contoh Perawatan No. 3, Karawang - ALAMAT DUMMY',true),
  ('SYN-WH-04','Gudang 4 - Logistik Cibitung','Jl. Contoh Logistik No. 4, Cibitung, Bekasi - ALAMAT DUMMY',true),
  ('SYN-WH-05','Gudang 5 - Penyangga Tambun','Jl. Contoh Penyangga No. 5, Tambun, Bekasi - ALAMAT DUMMY',true)
 ON CONFLICT(warehouse_id) DO NOTHING;
 INSERT INTO pp.demo_fixture_revision(version) VALUES('five-warehouse-v1') ON CONFLICT(version) DO NOTHING;
 REVOKE ALL ON pp.demo_warehouse_display,pp.demo_fixture_revision FROM PUBLIC;
 IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='pp_demo_api') THEN
  GRANT SELECT ON pp.demo_warehouse_display TO pp_demo_api;
 END IF;
END $$;
