"""Acceptance tests for human approval console decision function (pp.decide_approval).

Verifies invariants:
- Mandatory valid personnel name (not empty, no automated machine strings)
- Decision status restricted to 'approved' or 'rejected'
- Anti-double-decision protection on previously resolved requests
- Emits audit event to pp.vault_event
"""

import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_32_decide_approval_requires_valid_personnel_name(migrator_conn):
    """A-DB-32: pp.decide_approval rejects null/blank decider or automated/agent names."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (doc_type, doc_name, status)
            VALUES ('Material Request', 'MR-DECIDE-NAME-TEST', 'pending')
            RETURNING approval_id;
            """
        )
        approval_id = cur.fetchone()[0]

        # 1. Null decider must raise exception
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.decide_approval(%s, 'approved', NULL, 'Empty decider test');
                """,
                (approval_id,),
            )

        # 2. Whitespace-only decider must raise exception
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.decide_approval(%s, 'approved', '   ', 'Whitespace decider test');
                """,
                (approval_id,),
            )

        # 3. Automated/agent substring in decider must raise exception (008 requirement)
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.decide_approval(%s, 'approved', 'bot_agent_runner', 'Automated decider test');
                """,
                (approval_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_33_decide_approval_validates_decision_status(migrator_conn):
    """A-DB-33: pp.decide_approval accepts only 'approved' or 'rejected'."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (doc_type, doc_name, status)
            VALUES ('Material Request', 'MR-DECIDE-VAL-TEST', 'pending')
            RETURNING approval_id;
            """
        )
        approval_id = cur.fetchone()[0]

        # Invalid decision status must raise exception
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.decide_approval(%s, 'maybe', 'Operator Supervisor', 'Invalid status test');
                """,
                (approval_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_34_decide_approval_rejects_second_decision(migrator_conn):
    """A-DB-34: pp.decide_approval rejects subsequent decisions on already decided requests."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (doc_type, doc_name, status)
            VALUES ('Material Request', 'MR-DECIDE-DOUBLE-TEST', 'pending')
            RETURNING approval_id;
            """
        )
        approval_id = cur.fetchone()[0]

        # First decision succeeds
        cur.execute(
            """
            SELECT pp.decide_approval(%s, 'approved', 'Operator Supervisor', 'First decision');
            """,
            (approval_id,),
        )

        # Second decision on the same request must be rejected
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.decide_approval(%s, 'rejected', 'Another Operator', 'Second decision attempt');
                """,
                (approval_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_35_decide_approval_emits_vault_event(migrator_conn):
    """A-DB-35: pp.decide_approval emits audit event record to pp.vault_event."""
    doc_name = f"DOC-VAULT-{uuid.uuid4().hex[:6]}"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (doc_type, doc_name, status)
            VALUES ('Material Request', %s, 'pending')
            RETURNING approval_id;
            """,
            (doc_name,),
        )
        approval_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT pp.decide_approval(%s, 'approved', 'Operator VaultAuditor', 'Audit event check');
            """,
            (approval_id,),
        )

        cur.execute(
            """
            SELECT kind, ref_type, ref_id, payload
            FROM pp.vault_event
            WHERE ref_type = 'pp.approval_request' AND ref_id = %s;
            """,
            (str(approval_id),),
        )
        row = cur.fetchone()
        assert row is not None, "Audit event row must be emitted in pp.vault_event"
        assert row[0] == "approval", f"Expected kind 'approval', got {row[0]}"
        assert row[1] == "pp.approval_request"
        assert row[2] == str(approval_id)
        assert row[3] is not None
        assert row[3].get("decision") == "approved"
        assert row[3].get("by") == "Operator VaultAuditor"
