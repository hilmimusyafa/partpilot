-- One immutable cost basis per run; retained across demo reset (no resettable FK).
CREATE TABLE pp.demo_negotiation_round (
 run_id text PRIMARY KEY, comparison_id text NOT NULL,
 policy text NOT NULL DEFAULT 'best-total-minus-10pct-v1', round integer NOT NULL DEFAULT 1 CHECK(round=1),
 best_option_id text NOT NULL, best_total numeric NOT NULL CHECK(best_total>=0),
 target_total numeric NOT NULL CHECK(target_total>=0), basis jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), CHECK(target_total=best_total*0.90)
);
CREATE TABLE pp.demo_negotiation_vendor (
 run_id text NOT NULL REFERENCES pp.demo_negotiation_round(run_id), vendor_id text NOT NULL,
 comparison_id text NOT NULL, status text NOT NULL CHECK(status IN ('planned','skipped')),
 reason text, target_unit_price numeric, quantity numeric NOT NULL CHECK(quantity>0),
 non_item_total numeric NOT NULL CHECK(non_item_total>=0), quote jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(run_id,vendor_id),
 CHECK((status='planned' AND target_unit_price>0 AND reason IS NULL) OR
       (status='skipped' AND target_unit_price IS NULL AND reason IS NOT NULL))
);
CREATE TRIGGER demo_negotiation_round_immutable BEFORE UPDATE OR DELETE ON pp.demo_negotiation_round FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();
CREATE TRIGGER demo_negotiation_vendor_immutable BEFORE UPDATE OR DELETE ON pp.demo_negotiation_vendor FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();

CREATE FUNCTION pp.demo_plan_negotiation(p_comparison text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE c pp.demo_comparison; r pp.demo_run; b pp.demo_negotiation_round; best jsonb; opt jsonb;
 qty numeric; other numeric; target numeric; why text;
BEGIN
 SELECT * INTO c FROM pp.demo_comparison WHERE id=p_comparison;
 IF NOT FOUND THEN RAISE EXCEPTION 'comparison_not_found'; END IF;
 SELECT * INTO r FROM pp.demo_run WHERE id=c.run_id FOR UPDATE;
 IF NOT FOUND OR r.snapshot->>'status'<>'sourcing' OR EXISTS(SELECT 1 FROM pp.demo_decision WHERE run_id=r.id) THEN RAISE EXCEPTION 'run_not_sourcing'; END IF;
 IF (c.snapshot->>'source_run_version')::bigint<>r.version OR c.created_at<now()-interval '60 seconds' THEN RAISE EXCEPTION 'version_conflict'; END IF;
 qty=(r.snapshot->>'quantity')::numeric;
 SELECT * INTO b FROM pp.demo_negotiation_round WHERE run_id=r.id;
 IF NOT FOUND THEN
  SELECT value INTO best FROM jsonb_array_elements(c.snapshot->'eligible_complete_options')
   WHERE (value->>'valid_until')::timestamptz>now()
   ORDER BY (value->'economics'->>'future_relevant_option_total_unrounded')::numeric,value->>'option_id' LIMIT 1;
  IF best IS NULL THEN RETURN NULL; END IF;
  INSERT INTO pp.demo_negotiation_round(run_id,comparison_id,best_option_id,best_total,target_total,basis)
  VALUES(r.id,c.id,best->>'option_id',(best->'economics'->>'future_relevant_option_total_unrounded')::numeric,
   (best->'economics'->>'future_relevant_option_total_unrounded')::numeric*0.90,c.snapshot) RETURNING * INTO b;
  INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(r.id,'negotiation_basis_frozen',to_jsonb(b)-'basis');
 END IF;
 FOR opt IN SELECT value FROM jsonb_array_elements(c.snapshot->'eligible_complete_options') WHERE value->>'source_kind'='vendor' LOOP
  IF EXISTS(SELECT 1 FROM pp.demo_negotiation_vendor WHERE run_id=r.id AND vendor_id=opt->>'source_id') THEN CONTINUE; END IF;
  IF (opt->>'valid_until')::timestamptz<=now() THEN CONTINUE; END IF;
  other=(opt->'economics'->>'future_relevant_option_total_unrounded')::numeric-qty*(opt->'quote'->>'unit_price')::numeric;
  target=floor((b.target_total-other)/qty); why=NULL;
  IF EXISTS(SELECT 1 FROM jsonb_array_elements(b.basis->'eligible_complete_options') x WHERE x->>'option_id'=b.best_option_id AND (x->>'valid_until')::timestamptz<=now()) THEN why='benchmark_expired';
  ELSIF EXISTS(SELECT 1 FROM pp.demo_outbox WHERE run_id=r.id AND vendor_id=opt->>'source_id' AND kind='price_counteroffer') THEN why='already_negotiated';
  ELSIF target<=0 THEN why='non_item_cost_exceeds_target';
  ELSIF target>=(opt->'quote'->>'unit_price')::numeric THEN why='already_below_target'; END IF;
  INSERT INTO pp.demo_negotiation_vendor(run_id,vendor_id,comparison_id,status,reason,target_unit_price,quantity,non_item_total,quote)
   VALUES(r.id,opt->>'source_id',c.id,CASE WHEN why IS NULL THEN 'planned' ELSE 'skipped' END,why,
          CASE WHEN why IS NULL THEN target ELSE NULL END,qty,other,opt->'quote');
  INSERT INTO pp.demo_audit(run_id,event_type,payload) VALUES(r.id,'negotiation_vendor_planned',jsonb_build_object('vendor_id',opt->>'source_id','target_unit_price',CASE WHEN why IS NULL THEN target ELSE NULL END,'skip_reason',why));
 END LOOP;
 RETURN to_jsonb(b)-'basis';
END $$;

CREATE FUNCTION pp.demo_guard_negotiation_target() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE plan pp.demo_negotiation_vendor; b pp.demo_negotiation_round; current_quote jsonb;
BEGIN
 IF NEW.kind<>'price_counteroffer' THEN RETURN NEW; END IF;
 SELECT * INTO plan FROM pp.demo_negotiation_vendor WHERE run_id=NEW.run_id AND vendor_id=NEW.vendor_id;
 SELECT * INTO b FROM pp.demo_negotiation_round WHERE run_id=NEW.run_id;
 SELECT response->'quote' INTO current_quote FROM pp.demo_outbox WHERE run_id=NEW.run_id AND vendor_id=NEW.vendor_id AND kind='rfq';
 IF plan.run_id IS NULL OR plan.status<>'planned' OR
   (NEW.payload->>'target_unit_price')::numeric IS DISTINCT FROM plan.target_unit_price OR
   plan.target_unit_price IS DISTINCT FROM floor((b.target_total-plan.non_item_total)/plan.quantity) OR
   current_quote IS DISTINCT FROM plan.quote OR (current_quote->>'valid_until')::timestamptz<=now() OR
   EXISTS(SELECT 1 FROM jsonb_array_elements(b.basis->'eligible_complete_options') x WHERE x->>'option_id'=b.best_option_id AND (x->>'valid_until')::timestamptz<=now())
 THEN RAISE EXCEPTION 'negotiation_plan_mismatch'; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER demo_validate_negotiation BEFORE INSERT ON pp.demo_outbox FOR EACH ROW EXECUTE FUNCTION pp.demo_guard_negotiation_target();
REVOKE ALL ON pp.demo_negotiation_round,pp.demo_negotiation_vendor FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.demo_plan_negotiation(text),pp.demo_guard_negotiation_target() FROM PUBLIC;
