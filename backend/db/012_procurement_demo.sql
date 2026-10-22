-- Additive, synthetic-only procurement workflow. Apply explicitly to owned test DBs.
CREATE TABLE IF NOT EXISTS pp.demo_run (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 session_id text NOT NULL REFERENCES pp.wo_identification_session(id),
 session_version bigint NOT NULL,
 company text NOT NULL CHECK (company='SYN-COMPANY-01'),
 version bigint NOT NULL DEFAULT 1,
 request_key text NOT NULL UNIQUE,
 request jsonb NOT NULL,
 snapshot jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(session_id,session_version)
);
CREATE TABLE IF NOT EXISTS pp.demo_outbox (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 run_id text NOT NULL REFERENCES pp.demo_run(id),
 vendor_id text NOT NULL CHECK (vendor_id IN ('SIM-ENOUGH','SIM-SHORT','SIM-REFUSE','SIM-REVISE','SIM-SILENT')),
 kind text NOT NULL CHECK (kind IN ('rfq','price_counteroffer')),
 payload jsonb NOT NULL,
 response jsonb,
 created_at timestamptz NOT NULL DEFAULT now(),
 UNIQUE(run_id,vendor_id,kind)
);
CREATE TABLE IF NOT EXISTS pp.demo_comparison (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 run_id text NOT NULL REFERENCES pp.demo_run(id),
 version bigint NOT NULL DEFAULT 1 CHECK (version=1),
 request_key text NOT NULL UNIQUE,
 request jsonb NOT NULL,
 snapshot jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pp.demo_decision (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 run_id text NOT NULL UNIQUE REFERENCES pp.demo_run(id),
 comparison_id text NOT NULL REFERENCES pp.demo_comparison(id),
 option_id text NOT NULL,
 request_key text NOT NULL UNIQUE,
 procurement_executed boolean NOT NULL DEFAULT false CHECK (procurement_executed=false),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pp.demo_audit (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 run_id text NOT NULL REFERENCES pp.demo_run(id),
 event_type text NOT NULL,
 payload jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION pp.demo_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'immutable procurement record'; END $$;
DROP TRIGGER IF EXISTS demo_audit_immutable ON pp.demo_audit;
CREATE TRIGGER demo_audit_immutable BEFORE UPDATE OR DELETE ON pp.demo_audit FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();
DROP TRIGGER IF EXISTS demo_comparison_immutable ON pp.demo_comparison;
CREATE TRIGGER demo_comparison_immutable BEFORE UPDATE OR DELETE ON pp.demo_comparison FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();
DROP TRIGGER IF EXISTS demo_decision_immutable ON pp.demo_decision;
CREATE TRIGGER demo_decision_immutable BEFORE UPDATE OR DELETE ON pp.demo_decision FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();

CREATE OR REPLACE FUNCTION pp.demo_start(p_session text,p_version bigint,p_key text,p_snapshot jsonb)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE r pp.demo_run; s pp.wo_identification_session; req jsonb; rid text;
BEGIN
 req=jsonb_build_object('session_id',p_session,'expected_version',p_version);
 PERFORM pg_advisory_xact_lock(hashtextextended('demo_start:'||p_session,0));
 SELECT * INTO r FROM pp.demo_run WHERE request_key=p_key;
 IF FOUND THEN
  IF r.request<>req THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
  RETURN r.id;
 END IF;
 SELECT * INTO s FROM pp.wo_identification_session WHERE id=p_session FOR SHARE;
 IF NOT FOUND OR s.company<>'SYN-COMPANY-01' OR s.state<>'identified' OR s.version<>p_version THEN
  RAISE EXCEPTION 'identity_or_version_conflict';
 END IF;
 SELECT * INTO r FROM pp.demo_run WHERE session_id=p_session AND session_version=p_version;
 IF FOUND THEN RAISE EXCEPTION 'run_already_exists'; END IF;
 IF NOT EXISTS (SELECT 1 FROM erp.item i JOIN erp.bin b ON b.item_code=i.item_code
   WHERE i.item_code=s.result->'identified_candidate'->>'item_code' AND b.warehouse=s.warehouse
     AND i.stock_uom='Nos' AND i.item_group='Bearing' AND i.is_stock_item AND NOT i.disabled) THEN
  RAISE EXCEPTION 'unsupported_source_unit'; END IF;
 IF jsonb_typeof(p_snapshot) IS DISTINCT FROM 'object' OR
    COALESCE(p_snapshot->>'status','') NOT IN ('fulfilled_source','sourcing') OR
    COALESCE((p_snapshot->>'quantity')::numeric,0)<=0 OR
    (p_snapshot->>'quantity')::numeric IS DISTINCT FROM (s.input->>'quantity')::numeric OR
    p_snapshot->>'destination_warehouse_id' IS DISTINCT FROM s.warehouse OR
    NOT COALESCE(p_snapshot->'identity' ?& ARRAY['brand','base','suffix'],false) OR
    p_snapshot->>'requested_at' IS NULL OR p_snapshot->>'expires_at' IS NULL THEN
  RAISE EXCEPTION 'invalid_source_snapshot';
 END IF;
 INSERT INTO pp.demo_run(session_id,session_version,company,request_key,request,snapshot)
 VALUES(p_session,p_version,s.company,p_key,req,p_snapshot) RETURNING id INTO rid;
 INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(rid,'run_created',req);
 RETURN rid;
END $$;

CREATE OR REPLACE FUNCTION pp.demo_enqueue(p_run text,p_vendor text,p_kind text,p_payload jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE r pp.demo_run; e pp.demo_outbox; rfq pp.demo_outbox;
BEGIN
 SELECT * INTO r FROM pp.demo_run WHERE id=p_run FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'run_not_found'; END IF;
 SELECT * INTO e FROM pp.demo_outbox WHERE run_id=p_run AND vendor_id=p_vendor AND kind=p_kind;
 IF FOUND THEN
  IF e.payload<>p_payload THEN RAISE EXCEPTION 'counteroffer_or_request_conflict'; END IF;
  RETURN to_jsonb(e);
 END IF;
 IF r.snapshot->>'status'<>'sourcing' OR EXISTS(SELECT 1 FROM pp.demo_decision WHERE run_id=p_run) THEN
  RAISE EXCEPTION 'run_not_sourcing'; END IF;
 IF p_kind NOT IN ('rfq','price_counteroffer') OR p_vendor NOT IN ('SIM-ENOUGH','SIM-SHORT','SIM-REFUSE','SIM-REVISE','SIM-SILENT') THEN
  RAISE EXCEPTION 'invalid_vendor_event'; END IF;
 IF p_payload - ARRAY['identity','quantity','destination_warehouse_id','currency','requested_at','expires_at','target_unit_price'] <> '{}'::jsonb OR
    p_payload->'identity' IS DISTINCT FROM r.snapshot->'identity' OR
    p_payload->>'quantity' IS DISTINCT FROM r.snapshot->>'quantity' OR
    p_payload->>'destination_warehouse_id' IS DISTINCT FROM r.snapshot->>'destination_warehouse_id' OR
    p_payload->>'currency' IS DISTINCT FROM 'IDR' OR
    p_payload->>'requested_at' IS DISTINCT FROM r.snapshot->>'requested_at' OR
    p_payload->>'expires_at' IS DISTINCT FROM r.snapshot->>'expires_at' OR
    (p_payload->>'expires_at')::timestamptz<=now() THEN RAISE EXCEPTION 'unsafe_outbound_payload'; END IF;
 IF p_kind='price_counteroffer' THEN
  SELECT * INTO rfq FROM pp.demo_outbox WHERE run_id=p_run AND vendor_id=p_vendor AND kind='rfq';
  IF rfq.response->>'outcome' IS DISTINCT FROM 'quoted' OR
     (rfq.response->'quote'->>'qty_available')::numeric < (r.snapshot->>'quantity')::numeric OR
     (rfq.response->'quote'->>'valid_until')::timestamptz<=now() OR
     (p_payload->>'target_unit_price')::numeric<0 OR
     (p_payload->>'target_unit_price')::numeric >= (rfq.response->'quote'->>'unit_price')::numeric OR
     p_payload->>'target_unit_price' IS NULL THEN RAISE EXCEPTION 'counteroffer_ineligible'; END IF;
 ELSE
  IF p_payload ? 'target_unit_price' THEN RAISE EXCEPTION 'rfq_cannot_negotiate'; END IF;
 END IF;
 INSERT INTO pp.demo_outbox(run_id,vendor_id,kind,payload) VALUES(p_run,p_vendor,p_kind,p_payload) RETURNING * INTO e;
 UPDATE pp.demo_run SET version=version+1 WHERE id=p_run;
 INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(p_run,'outbound_reserved',jsonb_build_object('event_id',e.id,'vendor_id',p_vendor,'kind',p_kind));
 RETURN to_jsonb(e);
END $$;

CREATE OR REPLACE FUNCTION pp.demo_receive(p_event text,p_response jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE e pp.demo_outbox; rid text;
BEGIN
 SELECT run_id INTO rid FROM pp.demo_outbox WHERE id=p_event;
 PERFORM 1 FROM pp.demo_run WHERE id=rid FOR UPDATE;
 SELECT * INTO e FROM pp.demo_outbox WHERE id=p_event FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'event_not_found'; END IF;
 IF e.response IS NOT NULL THEN
  IF e.response<>p_response THEN RAISE EXCEPTION 'response_conflict'; END IF;
  RETURN;
 END IF;
 IF p_response->>'event_id' IS DISTINCT FROM e.id OR p_response->>'run_id' IS DISTINCT FROM e.run_id OR
    p_response->>'vendor_id' IS DISTINCT FROM e.vendor_id OR
    COALESCE(p_response->>'outcome','') NOT IN ('quoted','revised_quote','negotiation_refused','no_response','no_stock','malformed') THEN
  RAISE EXCEPTION 'invalid_vendor_response'; END IF;
 UPDATE pp.demo_outbox SET response=p_response WHERE id=p_event;
 UPDATE pp.demo_run SET version=version+1 WHERE id=e.run_id;
 INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(e.run_id,'vendor_response',jsonb_build_object('event_id',e.id,'outcome',p_response->>'outcome'));
END $$;

CREATE OR REPLACE FUNCTION pp.demo_compare(p_run text,p_version bigint,p_key text,p_request jsonb,p_snapshot jsonb)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE r pp.demo_run; c pp.demo_comparison; cid text; opt jsonb; q jsonb; scope jsonb;
BEGIN
 SELECT * INTO r FROM pp.demo_run WHERE id=p_run FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'run_not_found'; END IF;
 SELECT * INTO c FROM pp.demo_comparison WHERE request_key=p_key;
 IF FOUND THEN
  IF c.run_id<>p_run OR c.request<>p_request THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
  RETURN c.id;
 END IF;
 IF r.version<>p_version THEN RAISE EXCEPTION 'version_conflict'; END IF;
 IF (p_snapshot->>'source_run_version')::bigint IS DISTINCT FROM r.version OR
    jsonb_typeof(p_snapshot->'eligible_complete_options') IS DISTINCT FROM 'array' OR
    p_snapshot->'source_snapshot'->>'id' IS DISTINCT FROM r.id OR
    p_snapshot->'source_snapshot'->'identity' IS DISTINCT FROM r.snapshot->'identity' THEN
  RAISE EXCEPTION 'invalid_comparison'; END IF;
 FOR opt IN SELECT value FROM jsonb_array_elements(p_snapshot->'eligible_complete_options') LOOP
  IF (opt->>'quantity')::numeric IS DISTINCT FROM (r.snapshot->>'quantity')::numeric OR
     opt->'quote'->'identity' IS DISTINCT FROM r.snapshot->'identity' OR
     opt->'quote'->>'destination_warehouse_id' IS DISTINCT FROM r.snapshot->>'destination_warehouse_id' OR
     opt->'quote'->>'quantity_unit' IS DISTINCT FROM 'Nos' OR opt->'quote'->>'currency' IS DISTINCT FROM 'IDR' OR
     COALESCE((opt->'quote'->>'qty_available')::numeric,0)<(r.snapshot->>'quantity')::numeric OR
     opt->>'valid_until' IS DISTINCT FROM opt->'quote'->>'valid_until' OR
     opt->>'valid_until' IS NULL OR (opt->>'valid_until')::timestamptz<=now() OR
     COALESCE(opt->'economics'->>'status','') NOT IN ('complete','complete_with_exclusions') OR
     opt->'economics'->>'future_relevant_option_total_unrounded' IS NULL OR
     opt->>'option_id' IS DISTINCT FROM (opt->>'source_kind')||':'||(opt->>'source_id') THEN
   RAISE EXCEPTION 'invalid_comparison'; END IF;
  IF opt->>'source_kind'='vendor' THEN
   SELECT response->'quote' INTO q FROM pp.demo_outbox
    WHERE run_id=p_run AND vendor_id=opt->>'source_id' AND jsonb_typeof(response->'quote')='object'
    ORDER BY CASE kind WHEN 'price_counteroffer' THEN 0 ELSE 1 END LIMIT 1;
   IF q IS NULL OR q IS DISTINCT FROM opt->'quote' THEN RAISE EXCEPTION 'invalid_comparison'; END IF;
  ELSIF opt->>'source_kind'='warehouse' THEN
   SELECT value INTO scope FROM jsonb_array_elements(
    jsonb_build_array(r.snapshot->'availability'->'origin') || (r.snapshot->'availability'->'alternatives'))
    WHERE value->>'warehouse_id'=opt->>'source_id';
   IF scope IS NULL OR scope->>'status' IS DISTINCT FROM 'sufficient' OR
      opt->>'item_code' IS DISTINCT FROM scope->>'item_code' OR
      opt->'item_evidence' IS DISTINCT FROM scope->'evidence'->0 THEN
    RAISE EXCEPTION 'invalid_comparison'; END IF;
  ELSE RAISE EXCEPTION 'invalid_comparison'; END IF;
 END LOOP;
 INSERT INTO pp.demo_comparison(run_id,request_key,request,snapshot) VALUES(p_run,p_key,p_request,p_snapshot) RETURNING id INTO cid;
 INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(p_run,'comparison_created',jsonb_build_object('comparison_id',cid,'run_version',p_version));
 RETURN cid;
END $$;

CREATE OR REPLACE FUNCTION pp.demo_choose(p_comparison text,p_version bigint,p_option text,p_key text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE c pp.demo_comparison; d pp.demo_decision; r pp.demo_run; opt jsonb; q jsonb; available numeric; evidence jsonb;
BEGIN
 SELECT * INTO c FROM pp.demo_comparison WHERE id=p_comparison;
 IF NOT FOUND THEN RAISE EXCEPTION 'comparison_not_found'; END IF;
 SELECT * INTO r FROM pp.demo_run WHERE id=c.run_id FOR UPDATE;
 IF p_version IS DISTINCT FROM c.version THEN RAISE EXCEPTION 'version_conflict'; END IF;
 SELECT * INTO d FROM pp.demo_decision WHERE run_id=c.run_id OR request_key=p_key;
 IF FOUND THEN
  IF d.comparison_id<>p_comparison OR d.option_id<>p_option OR d.request_key<>p_key THEN RAISE EXCEPTION 'decision_conflict'; END IF;
  RETURN to_jsonb(d);
 END IF;
 IF p_version<>c.version THEN RAISE EXCEPTION 'version_conflict'; END IF;
 SELECT x INTO opt FROM jsonb_array_elements(c.snapshot->'eligible_complete_options') x WHERE x->>'option_id'=p_option;
 IF opt IS NULL OR (opt->>'valid_until')::timestamptz<=now() THEN RAISE EXCEPTION 'option_ineligible_or_expired'; END IF;
 IF opt->>'source_kind'='vendor' THEN
  SELECT response->'quote' INTO q FROM pp.demo_outbox WHERE run_id=c.run_id AND vendor_id=opt->>'source_id' AND jsonb_typeof(response->'quote')='object'
   ORDER BY CASE kind WHEN 'price_counteroffer' THEN 0 ELSE 1 END LIMIT 1;
  IF q IS DISTINCT FROM opt->'quote' THEN RAISE EXCEPTION 'quote_changed'; END IF;
 ELSE
  SELECT greatest(b.actual_qty-b.reserved_qty,0),jsonb_build_object('item_code',i.item_code,'item_name',i.item_name,
    'brand',i.brand,'description',i.description,'stock_uom',i.stock_uom,'item_group',i.item_group)
   INTO available,evidence FROM erp.bin b JOIN erp.warehouse w ON w.name=b.warehouse JOIN erp.item i ON i.item_code=b.item_code
   WHERE b.warehouse=opt->>'source_id' AND b.item_code=opt->>'item_code' AND w.company='SYN-COMPANY-01' AND NOT w.disabled AND NOT w.is_group AND NOT i.disabled
   FOR SHARE OF b,w,i;
  IF available IS NULL OR available<(r.snapshot->>'quantity')::numeric THEN RAISE EXCEPTION 'stock_changed'; END IF;
  IF evidence IS DISTINCT FROM opt->'item_evidence' OR evidence->>'stock_uom' IS DISTINCT FROM 'Nos' OR
     evidence->>'item_group' IS DISTINCT FROM 'Bearing' THEN RAISE EXCEPTION 'item_changed'; END IF;
 END IF;
 INSERT INTO pp.demo_decision(run_id,comparison_id,option_id,request_key) VALUES(c.run_id,p_comparison,p_option,p_key) RETURNING * INTO d;
 INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(c.run_id,'manager_selected',to_jsonb(d));
 RETURN to_jsonb(d);
END $$;

REVOKE ALL ON pp.demo_run,pp.demo_outbox,pp.demo_comparison,pp.demo_decision,pp.demo_audit FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.demo_start(text,bigint,text,jsonb),pp.demo_enqueue(text,text,text,jsonb),pp.demo_receive(text,jsonb),pp.demo_compare(text,bigint,text,jsonb,jsonb),pp.demo_choose(text,bigint,text,text) FROM PUBLIC;
-- Grant SELECT and only the required EXECUTE functions to the deployment service role
-- explicitly; no grants to an LLM agent, no credentials or role creation in this migration.
