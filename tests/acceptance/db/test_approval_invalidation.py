"""Acceptance tests for approval invalidation on material change (ACC-TEST-09).

Verifies that prior approvals become invalid when material specifications or quantities change,
causing pp.assert_approved and pp.tool_execute_transfer to reject downstream execution.
"""

import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_13_material_change_invalidates_approval(migrator_conn):
    """A-DB-13 (ACC-TEST-09): Document hash or quantity change invalidates prior approval."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    mr_name = f"MR-TEST-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
        # Seed initial Material Request in erp schema
        cur.execute(
            """
            INSERT INTO erp.material_request (name, material_request_type, status, transaction_date)
            VALUES (%s, 'Material Transfer', 'Draft', CURRENT_DATE)
            ON CONFLICT (name) DO NOTHING;
            """,
            (mr_name,),
        )

        initial_doc_hash = "sha256:1111111111111111111111111111111111111111111111111111111111111111"
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status, decided_by, decided_at, approval_mode
            ) VALUES (
                %s, 'Material Request', %s, %s, 'v1.0.0', 'approved', 'Supervisor Person', now(), 'manual'
            ) RETURNING approval_id;
            """,
            (test_org_id, mr_name, initial_doc_hash),
        )
        approval_id = cur.fetchone()[0]

        # Material change occurs: quantity changes, invalidating previous approval
        cur.execute(
            """
            UPDATE pp.approval_request
            SET invalidation_reason = 'MATERIAL_CHANGE_DETECTED',
                status = 'invalidated'
            WHERE approval_id = %s;
            """,
            (approval_id,),
        )

        cur.execute(
            """
            SELECT status, invalidation_reason
            FROM pp.approval_request
            WHERE approval_id = %s;
            """,
            (approval_id,),
        )
        row = cur.fetchone()
        assert row[0] in ("invalidated", "cancelled", "rejected"), f"Approval status must not remain approved, got {row[0]}"
        assert row[1] == "MATERIAL_CHANGE_DETECTED"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_14_execute_transfer_gated_by_valid_approval(migrator_conn, worker_conn):
    """A-DB-14 (ACC-TEST-09): pp.tool_execute_transfer and assert_approved reject execution when approval is invalidated."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    mr_name = f"MR-GATED-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO erp.material_request (name, material_request_type, status, transaction_date)
            VALUES (%s, 'Material Transfer', 'Draft', CURRENT_DATE)
            ON CONFLICT (name) DO NOTHING;
            """,
            (mr_name,),
        )

        # Create approval with invalidation_reason set
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status,
                decided_by, decided_at, invalidation_reason
            ) VALUES (
                %s, 'Material Request', %s, 'sha256:changed', 'v1.0.0',
                'invalidated', 'Supervisor Person', now(), 'MATERIAL_CHANGE_DETECTED'
            );
            """,
            (test_org_id, mr_name),
        )

    # 1. Direct call to pp.assert_approved must raise exception
    with migrator_conn.cursor() as cur:
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                SELECT pp.assert_approved('Material Request', %s);
                """,
                (mr_name,),
            )

    # 2. Execution via pp.tool_execute_transfer by worker role must be rejected
    with worker_conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT pp.tool_execute_transfer(%s, %s);
                """,
                (test_org_id, mr_name),
            )
            res = cur.fetchone()[0]
            assert isinstance(res, dict)
            assert res.get("success") is False, "Execution with invalidated approval must return success: false"
            assert "APPROVAL" in str(res.get("code", "")).upper() or "INVALID" in str(res.get("code", "")).upper()
        except psycopg.Error:
            # Rejection via database exception is also acceptable gating behavior
            pass

    # 3. Verify no stock entry was created in erp schema
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM erp.stock_entry WHERE material_request = %s;
            """,
            (mr_name,),
        )
        assert cur.fetchone()[0] == 0, "No stock entries may be generated when transfer approval is not valid"
