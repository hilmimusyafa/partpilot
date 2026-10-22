"""Owned PostgreSQL16 integration; never opens a configured production DSN."""
import copy
from pathlib import Path
import sys
import uuid

import psycopg
import pytest
from psycopg import sql

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isolated import Cluster
from test_maintenance_agent import CALLS, complete_sequence, final_reply, records, tool_reply

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def database():
    cluster = Cluster()
    try:
        cluster.sql((ROOT / 'backend/db/020_maintenance_evidence.sql').read_text())
        yield cluster
    finally:
        cluster.close()


def test_ingestion_is_idempotent_and_rejects_silent_source_rewrites(database):
    from backend.maintenance.ingest import digest
    from backend.maintenance.repository import seed_records
    with database.connection() as conn:
        assert seed_records(conn, records()) == 10
        assert seed_records(conn, records()) == 0
    modified = copy.deepcopy(records())
    modified[0]['facts']['historical_original_sku'] = 'invented'
    modified[0]['content_sha256'] = digest(modified[0]['facts'])
    with pytest.raises(ValueError, match='different facts'):
        with database.connection() as conn:
            seed_records(conn, modified)
    persisted = database.sql("SELECT facts FROM pp.maintenance_evidence WHERE id='history:NSK-SS-E-2003'")[0]['facts']
    assert persisted['historical_original_sku'] is None


def test_real_database_trace_is_durable_and_cannot_be_rewritten(database):
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    from backend.maintenance.repository import PostgresStore, seed_records
    with database.connection() as conn:
        seed_records(conn, records())
    store = PostgresStore(database.connection)
    assessment = assess(AssessmentInput(symptoms='Conveyor corrosion after washdown', quantity='2'), store=store,
                        complete=complete_sequence(tool_reply(CALLS), final_reply()))
    recovered = PostgresStore(database.connection).get_assessment(assessment['id'])
    assert recovered['status'] == 'completed'
    assert len(recovered['tool_trace']) == 4
    assert recovered['tool_trace'][0]['result']['evidence'][0]['source_refs'][0]['sha256']
    assert recovered['result']['engineering_candidate']['procurement_eligible'] is False
    with pytest.raises(psycopg.Error, match='immutable'):
        database.sql('UPDATE pp.maintenance_tool_trace SET status=\'rejected\' WHERE assessment_id=%s', (assessment['id'],))
    with pytest.raises(psycopg.Error, match='immutable'):
        database.sql('UPDATE pp.maintenance_assessment SET result=\'{}\' WHERE id=%s', (assessment['id'],))


def test_runtime_role_can_assess_but_cannot_rewrite_or_seed_evidence(database):
    from backend.maintenance.agent import assess
    from backend.maintenance.models import AssessmentInput
    from backend.maintenance.repository import PostgresStore, seed_records
    role = 'maintenance_runtime_' + uuid.uuid4().hex[:12]
    with database.connection() as conn:
        seed_records(conn, records())
        conn.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA pp TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT SELECT ON pp.maintenance_evidence TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE ON pp.maintenance_assessment TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT SELECT,INSERT ON pp.maintenance_tool_trace TO {}').format(sql.Identifier(role)))
    def runtime():
        conn = database.connection()
        conn.execute(sql.SQL('SET ROLE {}').format(sql.Identifier(role)))
        return conn
    assessment = assess(AssessmentInput(symptoms='Conveyor corrosion after washdown'), store=PostgresStore(runtime),
                        complete=complete_sequence(tool_reply(CALLS), final_reply()))
    assert assessment['status'] == 'completed'
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with runtime() as conn:
            conn.execute("DELETE FROM pp.maintenance_evidence")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with runtime() as conn:
            seed_records(conn, records())
