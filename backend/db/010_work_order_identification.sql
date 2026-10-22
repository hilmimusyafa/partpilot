-- 010_work_order_identification.sql
-- Additive persistence for Work Order Text Identification MVP
-- Normative source: private/wo-v1/DECISIONS.md (Minimal additive persistence)

CREATE TABLE IF NOT EXISTS pp.wo_identification_session (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    company TEXT NOT NULL REFERENCES erp.company(name),
    asset TEXT REFERENCES erp.asset(name),
    warehouse TEXT REFERENCES erp.warehouse(name),
    input JSONB NOT NULL,
    raw_submission JSONB,
    context_source JSONB,
    state TEXT NOT NULL CHECK (state IN ('draft', 'queued', 'processing', 'awaiting_clarification', 'identified', 'no_match', 'knowledge_unavailable', 'needs_review', 'failed')),
    version BIGINT NOT NULL DEFAULT 1 CHECK (version >= 1),
    input_revision INT NOT NULL DEFAULT 1,
    clarification_round INT NOT NULL DEFAULT 0 CHECK (clarification_round BETWEEN 0 AND 3),
    explicit_retries INT NOT NULL DEFAULT 0 CHECK (explicit_retries BETWEEN 0 AND 2),
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pp.wo_identification_event (
    session_id TEXT NOT NULL REFERENCES pp.wo_identification_session(id) ON DELETE CASCADE,
    seq INT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT to_char(now() at time zone 'utc', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
    event_type TEXT NOT NULL,
    input_revision INT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (session_id, seq)
);

CREATE TABLE IF NOT EXISTS pp.wo_identification_job (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    session_id TEXT NOT NULL REFERENCES pp.wo_identification_session(id) ON DELETE CASCADE,
    input_revision INT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed')),
    attempts INT NOT NULL DEFAULT 0 CHECK (attempts <= 2),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_until TIMESTAMPTZ,
    fence BIGINT NOT NULL DEFAULT 0,
    worker_id TEXT,
    error JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_wo_job_session_revision UNIQUE (session_id, input_revision)
);

CREATE INDEX IF NOT EXISTS pp_wo_job_status_avail_idx ON pp.wo_identification_job (status, available_at);
CREATE UNIQUE INDEX IF NOT EXISTS pp_wo_job_running_per_session_idx ON pp.wo_identification_job (session_id) WHERE status = 'running';

CREATE TABLE IF NOT EXISTS pp.wo_identification_idempotency (
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    request_hash TEXT NOT NULL,
    response_status INT NOT NULL,
    response JSONB NOT NULL,
    session_id TEXT REFERENCES pp.wo_identification_session(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (scope, key)
);
