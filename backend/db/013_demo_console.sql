-- Explicitly disabled until the dedicated-demo installer enables it.
CREATE TABLE IF NOT EXISTS pp.demo_control (
 singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
 database_name text NOT NULL DEFAULT current_database(),
 dataset_tag text NOT NULL CHECK(dataset_tag='synthetic-bearing-demo-v1'),
 reset_enabled boolean NOT NULL DEFAULT false,
 generation bigint NOT NULL DEFAULT 1,
 stock_baseline jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS pp.demo_reset_audit (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 request_key text NOT NULL UNIQUE,
 old_generation bigint NOT NULL,
 new_generation bigint NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(),
 archived_workflow jsonb NOT NULL,
 result jsonb NOT NULL
);
DROP TRIGGER IF EXISTS demo_reset_audit_immutable ON pp.demo_reset_audit;
CREATE TRIGGER demo_reset_audit_immutable BEFORE UPDATE OR DELETE ON pp.demo_reset_audit
 FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();

CREATE OR REPLACE FUNCTION pp.demo_reset(p_generation bigint,p_key text,p_confirmation text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp,erp AS $$
DECLARE c pp.demo_control; old pp.demo_reset_audit; archive jsonb; result jsonb;
BEGIN
 -- Shared by all authenticated demo mutations; fences stale browser retries.
 PERFORM pg_advisory_xact_lock(72490122);
 SELECT * INTO c FROM pp.demo_control WHERE singleton FOR UPDATE;
 IF NOT FOUND OR NOT c.reset_enabled OR c.database_name<>current_database()
    OR c.dataset_tag<>'synthetic-bearing-demo-v1'
    OR EXISTS(SELECT 1 FROM erp.company WHERE name<>'SYN-COMPANY-01') THEN
   RAISE EXCEPTION 'reset_disabled';
 END IF;
 IF p_confirmation IS DISTINCT FROM 'RESET DEMO' OR p_key IS NULL OR length(p_key) NOT BETWEEN 1 AND 128 THEN
   RAISE EXCEPTION 'reset_confirmation_required';
 END IF;
 SELECT * INTO old FROM pp.demo_reset_audit WHERE request_key=p_key;
 IF FOUND THEN
   IF old.old_generation<>p_generation THEN RAISE EXCEPTION 'idempotency_conflict'; END IF;
   RETURN old.result;
 END IF;
 IF c.generation<>p_generation THEN RAISE EXCEPTION 'generation_conflict'; END IF;
 SET LOCAL lock_timeout='3s';
 -- Lock before checking jobs, so no new worker claim can race the reset.
 LOCK TABLE pp.wo_identification_job,pp.wo_identification_session,
   pp.wo_identification_event,pp.wo_identification_idempotency,
   pp.demo_run,pp.demo_outbox,pp.demo_comparison,pp.demo_decision,pp.demo_audit IN ACCESS EXCLUSIVE MODE;
 IF EXISTS(SELECT 1 FROM pp.wo_identification_job WHERE status='running' AND lease_until>now()) THEN
   RAISE EXCEPTION 'demo_busy';
 END IF;
 SELECT jsonb_build_object(
   'sessions',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.wo_identification_session t),
   'jobs',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.wo_identification_job t),
   'events',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.wo_identification_event t),
   'requests',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.wo_identification_idempotency t),
   'runs',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.demo_run t),
   'outbox',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.demo_outbox t),
   'comparisons',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.demo_comparison t),
   'decisions',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.demo_decision t),
   'audit',(SELECT coalesce(jsonb_agg(to_jsonb(t)),'[]') FROM pp.demo_audit t)) INTO archive;
 -- Explicit workflow-only table list, no CASCADE and no ERP truncate.
 TRUNCATE pp.demo_audit,pp.demo_decision,pp.demo_comparison,pp.demo_outbox,pp.demo_run,
   pp.wo_identification_event,pp.wo_identification_job,pp.wo_identification_idempotency,pp.wo_identification_session;
 UPDATE erp.bin b SET actual_qty=(v->>'actual_qty')::numeric,reserved_qty=(v->>'reserved_qty')::numeric
 FROM jsonb_array_elements(c.stock_baseline) v
 WHERE b.item_code=v->>'item_code' AND b.warehouse=v->>'warehouse';
 UPDATE pp.demo_control SET generation=generation+1 WHERE singleton;
 result=jsonb_build_object('reset',true,'generation',c.generation+1,'audit_preserved',true);
 INSERT INTO pp.demo_reset_audit(request_key,old_generation,new_generation,archived_workflow,result)
 VALUES(p_key,c.generation,c.generation+1,archive,result);
 RETURN result;
END $$;
REVOKE ALL ON pp.demo_control,pp.demo_reset_audit FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.demo_reset(bigint,text,text) FROM PUBLIC;
