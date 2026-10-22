-- Reviewed external evidence and auditable read-only agent assessments.
CREATE TABLE IF NOT EXISTS pp.maintenance_evidence (
 id text PRIMARY KEY,
 kind text NOT NULL CHECK(kind IN ('published_case','catalog_part','troubleshooting','economic_case')),
 title text NOT NULL,
 facts jsonb NOT NULL CHECK(jsonb_typeof(facts)='object'),
 source_refs jsonb NOT NULL CHECK(jsonb_typeof(source_refs)='array' AND jsonb_array_length(source_refs)>0),
 default_retrieval boolean NOT NULL DEFAULT true,
 is_local_asset_history boolean NOT NULL DEFAULT false CHECK(NOT is_local_asset_history),
 content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
 ingested_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pp.maintenance_assessment (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 status text NOT NULL DEFAULT 'running' CHECK(status IN ('running','completed','needs_review','failed')),
 request jsonb NOT NULL CHECK(jsonb_typeof(request)='object'),
 result jsonb,
 model_metadata jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now(),
 completed_at timestamptz,
 CHECK((status='running' AND result IS NULL AND completed_at IS NULL) OR
       (status<>'running' AND jsonb_typeof(result)='object' AND completed_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS pp.maintenance_tool_trace (
 assessment_id text NOT NULL REFERENCES pp.maintenance_assessment(id),
 sequence integer NOT NULL CHECK(sequence BETWEEN 1 AND 8),
 turn integer NOT NULL CHECK(turn BETWEEN 1 AND 4),
 tool_call_id text NOT NULL,
 tool_name text NOT NULL,
 arguments jsonb NOT NULL,
 status text NOT NULL CHECK(status IN ('ok','not_found','rejected')),
 evidence_ids jsonb NOT NULL,
 result jsonb NOT NULL,
 duration_ms integer NOT NULL CHECK(duration_ms>=0),
 created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(assessment_id,sequence)
);

CREATE OR REPLACE FUNCTION pp.maintenance_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN RAISE EXCEPTION 'maintenance_evidence_or_trace_immutable'; END $$;
DROP TRIGGER IF EXISTS maintenance_evidence_immutable ON pp.maintenance_evidence;
CREATE TRIGGER maintenance_evidence_immutable BEFORE UPDATE OR DELETE ON pp.maintenance_evidence
 FOR EACH ROW EXECUTE FUNCTION pp.maintenance_immutable();
DROP TRIGGER IF EXISTS maintenance_trace_immutable ON pp.maintenance_tool_trace;
CREATE TRIGGER maintenance_trace_immutable BEFORE UPDATE OR DELETE ON pp.maintenance_tool_trace
 FOR EACH ROW EXECUTE FUNCTION pp.maintenance_immutable();

CREATE OR REPLACE FUNCTION pp.maintenance_assessment_transition() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog AS $$
BEGIN
 IF OLD.status<>'running' OR NEW.request IS DISTINCT FROM OLD.request OR NEW.id<>OLD.id
    OR NEW.created_at<>OLD.created_at OR NEW.status='running' THEN
   RAISE EXCEPTION 'maintenance_assessment_immutable';
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS maintenance_assessment_transition ON pp.maintenance_assessment;
CREATE TRIGGER maintenance_assessment_transition BEFORE UPDATE ON pp.maintenance_assessment
 FOR EACH ROW EXECUTE FUNCTION pp.maintenance_assessment_transition();

REVOKE ALL ON pp.maintenance_evidence,pp.maintenance_assessment,pp.maintenance_tool_trace FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.maintenance_immutable(),pp.maintenance_assessment_transition() FROM PUBLIC;
