"""Acceptance tests for durable execution attempt audit (ACC-TEST-11).

Verifies that execution attempt audit logs in pp.tool_execution_attempt remain preserved
with status 'rejected_policy' or 'failed_exception' even when the associated business
operation fails or its transaction is aborted.
"""

import json
import uuid
import psycopg
import pytest
from tests.acceptance.db.conftest import create_role_connection


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_21_rejected_attempt_recorded_despite_rollback(migrator_conn):
    """A-DB-21 (ACC-TEST-11): Rejected operations preserve durable audit log in pp.tool_execution_attempt."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    tool_name = "pp.tool_plan_transfer"
    caller_role = "pp_agent"
    input_payload = {
        "org_id": test_org_id,
        "wo_part_id": 9999,
        "from_warehouse": "WH-B1/Stores",
        "to_warehouse": "WH-B1/Transit",
        "notes": "Invalid intra-site transfer violating invariant",
    }

    # Step 1: Pre-log attempt on dedicated connection (autocommit=True)
    audit_conn = create_role_connection("pp_agent", autocommit=True)
    try:
        with audit_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pp.tool_execution_attempt (
                    org_id, tool_name, caller_role, input_payload, status
                ) VALUES (
                    %s, %s, %s, %s::jsonb, 'attempted'
                ) RETURNING attempt_id;
                """,
                (test_org_id, tool_name, caller_role, json.dumps(input_payload)),
            )
            attempt_id = cur.fetchone()[0]
    finally:
        audit_conn.close()

    # Step 2: Attempt business transaction that violates invariant and aborts
    business_conn = create_role_connection("pp_agent", autocommit=False)
    try:
        with business_conn.cursor() as cur:
            # Intra-site transfer where from_site == to_site violates transfer_lane invariant
            cur.execute(
                """
                INSERT INTO pp.transfer_lane (org_id, lane_code, from_site, to_site, transit_hours, standard_cost)
                VALUES (%s, 'LANE-ILLEGAL-SAME-SITE', 'SITE-B1', 'SITE-B1', 1.0, 100.00);
                """,
                (test_org_id,),
            )
            business_conn.commit()
    except psycopg.Error as ex:
        business_conn.rollback()
        # Step 3: Record rejection in durable attempt table on separate audit connection
        rejection_conn = create_role_connection("pp_agent", autocommit=True)
        try:
            with rejection_conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE pp.tool_execution_attempt
                    SET status = 'rejected_policy',
                        error_code = %s,
                        error_message = %s
                    WHERE attempt_id = %s;
                    """,
                    (type(ex).__name__, str(ex)[:200], attempt_id),
                )
        finally:
            rejection_conn.close()
    finally:
        business_conn.close()

    # Step 4: Verify audit log survived and business table remained clean
    with migrator_conn.cursor() as cur:
        # Business table must NOT contain the aborted row
        cur.execute(
            """
            SELECT COUNT(*) FROM pp.transfer_lane WHERE lane_code = 'LANE-ILLEGAL-SAME-SITE';
            """
        )
        assert cur.fetchone()[0] == 0, "Aborted business row must not persist"

        # Attempt log must exist with status 'rejected_policy'
        cur.execute(
            """
            SELECT status, tool_name, caller_role, error_code
            FROM pp.tool_execution_attempt
            WHERE attempt_id = %s;
            """,
            (attempt_id,),
        )
        row = cur.fetchone()
        assert row is not None, "Durable attempt audit row must exist"
        assert row[0] == "rejected_policy", f"Expected status 'rejected_policy', got {row[0]}"
        assert row[1] == tool_name
        assert row[2] == caller_role
        assert row[3] is not None, "Error code must be recorded in durable attempt"
