-- Additive food demo; real catalog names, explicitly synthetic operational state.
ALTER TABLE pp.production_line DROP CONSTRAINT IF EXISTS production_line_production_scope_check;
ALTER TABLE pp.production_line ADD CONSTRAINT production_line_production_scope_check CHECK(production_scope IN ('AC','FOOD'));

CREATE TABLE IF NOT EXISTS pp.maintenance_engineering_review (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 assessment_id text NOT NULL REFERENCES pp.maintenance_assessment(id),
 reviewer text NOT NULL CHECK(length(btrim(reviewer)) BETWEEN 2 AND 100),
 decision text NOT NULL CHECK(decision IN ('approved','rejected')),
 checks jsonb NOT NULL, notes text NOT NULL CHECK(length(btrim(notes))>=10),
 CHECK(decision<>'approved' OR checks @> '{"interface_load_speed_checked":true,"temperature_duty_checked":true,"hygiene_approved":true}'::jsonb),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pp.maintenance_work_order (
 assessment_id text NOT NULL REFERENCES pp.maintenance_assessment(id),
 session_id text NOT NULL UNIQUE,
 generation bigint NOT NULL,
 part_kind text NOT NULL CHECK(part_kind IN ('exact','candidate')),
 confirmed_by text NOT NULL, engineering_review_id text REFERENCES pp.maintenance_engineering_review(id),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(assessment_id,generation,part_kind),
 CHECK(part_kind='exact' OR engineering_review_id IS NOT NULL)
);
CREATE OR REPLACE FUNCTION pp.maintenance_one_decision() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE aid text; chosen_kind text; latest_decision text;
BEGIN
 SELECT w.assessment_id,w.part_kind INTO aid,chosen_kind FROM pp.maintenance_work_order w JOIN pp.demo_run r ON r.session_id=w.session_id WHERE r.id=NEW.run_id;
 IF aid IS NOT NULL THEN
  PERFORM 1 FROM pp.maintenance_assessment WHERE id=aid FOR UPDATE;
  IF chosen_kind='candidate' THEN
   SELECT decision INTO latest_decision FROM pp.maintenance_engineering_review WHERE assessment_id=aid ORDER BY created_at DESC,id DESC LIMIT 1;
   IF latest_decision IS DISTINCT FROM 'approved' THEN RAISE EXCEPTION 'engineering_approval_required'; END IF;
  END IF;
  IF EXISTS(SELECT 1 FROM pp.demo_decision d JOIN pp.demo_run r ON r.id=d.run_id JOIN pp.maintenance_work_order w ON w.session_id=r.session_id WHERE w.assessment_id=aid AND d.run_id<>NEW.run_id) THEN
   RAISE EXCEPTION 'maintenance_request_already_selected';
  END IF;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS maintenance_one_decision ON pp.demo_decision;
CREATE TRIGGER maintenance_one_decision BEFORE INSERT ON pp.demo_decision FOR EACH ROW EXECUTE FUNCTION pp.maintenance_one_decision();
DROP TRIGGER IF EXISTS maintenance_review_immutable ON pp.maintenance_engineering_review;
CREATE TRIGGER maintenance_review_immutable BEFORE UPDATE OR DELETE ON pp.maintenance_engineering_review FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();

CREATE OR REPLACE FUNCTION pp.maintenance_candidate_run_guard() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE aid text; decision text;
BEGIN
 IF NEW.snapshot->'identity'->>'full_designation'='PSF20/LP99' THEN
  SELECT assessment_id INTO aid FROM pp.maintenance_work_order WHERE session_id=NEW.session_id AND part_kind='candidate';
  IF aid IS NULL THEN RAISE EXCEPTION 'engineering_approval_required'; END IF;
  PERFORM 1 FROM pp.maintenance_assessment WHERE id=aid FOR UPDATE;
  SELECT r.decision INTO decision FROM pp.maintenance_engineering_review r WHERE r.assessment_id=aid ORDER BY created_at DESC,id DESC LIMIT 1;
  IF decision IS DISTINCT FROM 'approved' THEN RAISE EXCEPTION 'engineering_approval_required'; END IF;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS maintenance_candidate_run_guard ON pp.demo_run;
CREATE TRIGGER maintenance_candidate_run_guard BEFORE INSERT ON pp.demo_run FOR EACH ROW EXECUTE FUNCTION pp.maintenance_candidate_run_guard();

INSERT INTO pp.production_site(id,company,name) VALUES('FOOD-SITE','SYN-COMPANY-01','Pabrik makanan demo (simulasi)') ON CONFLICT DO NOTHING;
INSERT INTO pp.production_line(id,company,site_id,name,production_scope) VALUES('FOOD-LINE','SYN-COMPANY-01','FOOD-SITE','Lini conveyor makanan setelah washdown','FOOD') ON CONFLICT DO NOTHING;
INSERT INTO pp.production_station(id,company,production_line_id,name) VALUES('FOOD-STATION','SYN-COMPANY-01','FOOD-LINE','Conveyor CV-FOOD-01') ON CONFLICT DO NOTHING;
INSERT INTO erp.asset(name,asset_name,company,status) VALUES('FOOD-CONVEYOR','Conveyor makanan CV-FOOD-01 (simulasi)','SYN-COMPANY-01','Submitted') ON CONFLICT DO NOTHING;
INSERT INTO pp.machine_context(asset,company,station_id) VALUES('FOOD-CONVEYOR','SYN-COMPANY-01','FOOD-STATION') ON CONFLICT DO NOTHING;
INSERT INTO pp.asset_ext(asset,site_warehouse,criticality) VALUES('FOOD-CONVEYOR','SYN-WH-01','D') ON CONFLICT DO NOTHING;

INSERT INTO erp.item(item_code,item_name,item_group,stock_uom,brand,description,is_stock_item,disabled) VALUES
 ('DEMO-RHP-PSF20CR','RHP PSF20CR','Bearing','Nos','RHP','Complete four-bolt flange unit RHP PSF20CR; catalog designation verified; local stock and machine assignment are synthetic.',true,false),
 ('DEMO-RHP-PSF20-LP99','RHP PSF20/LP99','Bearing','Nos','RHP','Complete four-bolt flange unit RHP PSF20/LP99; catalog designation verified; candidate requires engineering and hygiene approval; stock synthetic.',true,false)
ON CONFLICT(item_code) DO NOTHING;
INSERT INTO erp.bin(item_code,warehouse,actual_qty,reserved_qty)
 SELECT i.item_code,w.name,CASE WHEN i.item_code='DEMO-RHP-PSF20CR' AND w.name='SYN-WH-02' THEN 2 WHEN i.item_code='DEMO-RHP-PSF20-LP99' AND w.name='SYN-WH-03' THEN 2 ELSE 0 END,0
 FROM erp.item i CROSS JOIN erp.warehouse w WHERE i.item_code IN ('DEMO-RHP-PSF20CR','DEMO-RHP-PSF20-LP99') AND w.name IN ('SYN-WH-01','SYN-WH-02','SYN-WH-03','SYN-WH-04','SYN-WH-05')
ON CONFLICT DO NOTHING;
UPDATE pp.demo_control SET stock_baseline=stock_baseline || coalesce((SELECT jsonb_agg(to_jsonb(b)) FROM erp.bin b WHERE b.item_code IN ('DEMO-RHP-PSF20CR','DEMO-RHP-PSF20-LP99') AND NOT EXISTS(SELECT 1 FROM jsonb_array_elements(stock_baseline) s WHERE s->>'item_code'=b.item_code AND s->>'warehouse'=b.warehouse)),'[]'::jsonb) WHERE singleton;
REVOKE ALL ON pp.maintenance_engineering_review,pp.maintenance_work_order FROM PUBLIC;
