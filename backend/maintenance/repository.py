"""PostgreSQL persistence; model never receives database credentials or SQL access."""
from psycopg import Error
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from backend.wo.repository import RepositoryError, get_db_connection


class MaintenanceError(RepositoryError):
    pass


class PostgresStore:
    def __init__(self, connection_factory=None):
        self.connect = connection_factory or get_db_connection

    def _query(self, sql, params=()):
        try:
            with self.connect() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute('SET LOCAL statement_timeout = 3000')
                    cur.execute(sql, params)
                    return cur.fetchall() if cur.description else []
        except Error:
            raise MaintenanceError('maintenance_storage_unavailable', 'Maintenance evidence storage unavailable', 503) from None

    def list_evidence(self, kind=None):
        return self._query('SELECT * FROM pp.maintenance_evidence WHERE (%s::text IS NULL OR kind=%s) ORDER BY id LIMIT 100', (kind, kind))

    def get_evidence(self, evidence_id):
        rows = self._query('SELECT * FROM pp.maintenance_evidence WHERE id=%s', (evidence_id,))
        return rows[0] if rows else None

    def create_assessment(self, request):
        return self._query('INSERT INTO pp.maintenance_assessment(request) VALUES(%s) RETURNING id', (Jsonb(request),))[0]['id']

    def append_trace(self, ident, trace):
        self._query('''INSERT INTO pp.maintenance_tool_trace
          (assessment_id,sequence,turn,tool_call_id,tool_name,arguments,status,evidence_ids,result,duration_ms)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',
          (ident, trace['sequence'], trace['turn'], trace['tool_call_id'], trace['tool_name'], Jsonb(trace['arguments']),
           trace['status'], Jsonb(trace['evidence_ids']), Jsonb(trace['result']), trace['duration_ms']))

    def finish_assessment(self, ident, status, result, metadata):
        rows = self._query('''UPDATE pp.maintenance_assessment SET status=%s,result=%s,model_metadata=%s,completed_at=now()
                             WHERE id=%s AND status='running' RETURNING id''',
                           (status, Jsonb(result), Jsonb(metadata), ident))
        if not rows:
            raise MaintenanceError('assessment_state_conflict', 'Assessment already completed', 409)

    def get_assessment(self, ident):
        rows = self._query('SELECT * FROM pp.maintenance_assessment WHERE id=%s', (ident,))
        if not rows:
            raise MaintenanceError('assessment_not_found', 'Assessment not found', 404)
        row = rows[0]
        row['tool_trace'] = self._query('SELECT * FROM pp.maintenance_tool_trace WHERE assessment_id=%s ORDER BY sequence', (ident,))
        return row


def seed_records(conn, records):
    """Owner-only ingestion. Idempotent for identical extracts; never overwrites history."""
    inserted = 0
    with conn.transaction():
        for row in records:
            result = conn.execute('''INSERT INTO pp.maintenance_evidence
              (id,kind,title,facts,source_refs,default_retrieval,is_local_asset_history,content_sha256)
              VALUES(%s,%s,%s,%s,%s,%s,false,%s) ON CONFLICT(id) DO NOTHING RETURNING id''',
              (row['id'], row['kind'], row['title'], Jsonb(row['facts']), Jsonb(row['source_refs']),
               row['default_retrieval'], row['content_sha256'])).fetchone()
            if result:
                inserted += 1
            existing = conn.execute('SELECT content_sha256 FROM pp.maintenance_evidence WHERE id=%s', (row['id'],)).fetchone()
            actual = existing['content_sha256'] if isinstance(existing, dict) else existing[0]
            if actual != row['content_sha256']:
                raise ValueError('Evidence ID already exists with different facts; publish a new evidence version')
    return inserted
