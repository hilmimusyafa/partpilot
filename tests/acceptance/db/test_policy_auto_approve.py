"""Acceptance tests for policy auto-approval engine.

Verifies deterministic automated approval evaluation:
- Demo mode requirement
- Audit trail recording with policy version in decided_by (no human impersonation)
- Rejection on conflicting mappings, scores < 0.90, and unverified suffixes
- Rejection on document hash mismatches
"""

import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_28_policy_auto_approve_requires_demo_mode(migrator_conn, worker_conn):
    """A-DB-28: pp.policy_auto_approve rejects execution when demo mode is not enabled."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    doc_hash = "sha256:validhash123"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status, approval_mode
            ) VALUES (
                %s, 'Item Mapping', 'MAP-DEMO-TEST', %s, 'v1.0.0', 'pending', 'manual'
            ) RETURNING approval_id;
            """,
            (test_org_id, doc_hash),
        )
        approval_id = cur.fetchone()[0]

    # In non-demo mode (default), auto approval must be rejected
    with worker_conn.cursor() as cur:
        try:
            cur.execute(
                """
                SELECT pp.policy_auto_approve(%s, %s, 'v1.0.0', %s);
                """,
                (test_org_id, approval_id, doc_hash),
            )
            res = cur.fetchone()[0]
            assert isinstance(res, dict)
            assert res.get("success") is False, "Auto-approve must fail when demo mode is disabled"
        except psycopg.Error:
            pass


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_29_policy_auto_approve_records_policy_audit_trail(migrator_conn, worker_conn):
    """A-DB-29: Auto-approved requests record decided_by as 'policy:<version>' and approval_mode='policy_auto'."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    doc_hash = "sha256:eligible_clean_mapping"
    policy_ver = "v1.0.0"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status, approval_mode
            ) VALUES (
                %s, 'Item Mapping', 'MAP-ELIGIBLE-CLEAN', %s, %s, 'pending', 'manual'
            ) RETURNING approval_id;
            """,
            (test_org_id, doc_hash, policy_ver),
        )
        approval_id = cur.fetchone()[0]

    # Execute policy_auto_approve
    with worker_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pp.policy_auto_approve(%s, %s, %s, %s);
            """,
            (test_org_id, approval_id, policy_ver, doc_hash),
        )
        res = cur.fetchone()[0]
        assert isinstance(res, dict)

    # Check approval record audit fields
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, decided_by, approval_mode
            FROM pp.approval_request
            WHERE approval_id = %s;
            """,
            (approval_id,),
        )
        status, decided_by, mode = cur.fetchone()
        assert status == "approved", "Eligible request must be approved"
        assert decided_by == f"policy:{policy_ver}", f"decided_by must record policy version, got {decided_by}"
        assert mode == "policy_auto", f"approval_mode must be 'policy_auto', got {mode}"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_30_policy_auto_approve_rejects_conflict_and_unverified_suffix(migrator_conn, worker_conn):
    """A-DB-30: Auto-approve rejects requests with scores < 0.90, conflicts, or -S100 suffixes."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    doc_hash = "sha256:s100_unverified_hash"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status, note
            ) VALUES (
                %s, 'Item Mapping', 'MAP-S100-CONFLICT', %s, 'v1.0.0', 'pending',
                '{"suffix": "-S100", "score": 0.85, "conflicting": true}'
            ) RETURNING approval_id;
            """,
            (test_org_id, doc_hash),
        )
        approval_id = cur.fetchone()[0]

    with worker_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pp.policy_auto_approve(%s, %s, 'v1.0.0', %s);
            """,
            (test_org_id, approval_id, doc_hash),
        )
        res = cur.fetchone()[0]
        assert isinstance(res, dict)
        assert res.get("success") is False, "Auto-approve must reject unverified suffix or score < 0.90"

    with migrator_conn.cursor() as cur:
        cur.execute("SELECT status FROM pp.approval_request WHERE approval_id = %s;", (approval_id,))
        status = cur.fetchone()[0]
        assert status != "approved", "Status must not transition to approved"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_31_policy_auto_approve_rejects_hash_mismatch(migrator_conn, worker_conn):
    """A-DB-31: Auto-approve rejects requests when document hash does not match expected hash."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    actual_hash = "sha256:hash_original_doc_xyz"
    tampered_expected_hash = "sha256:hash_different_doc_abc"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.approval_request (
                org_id, doc_type, doc_name, doc_hash, policy_version, status
            ) VALUES (
                %s, 'Material Request', 'MR-HASH-MISMATCH', %s, 'v1.0.0', 'pending'
            ) RETURNING approval_id;
            """,
            (test_org_id, actual_hash),
        )
        approval_id = cur.fetchone()[0]

    with worker_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pp.policy_auto_approve(%s, %s, 'v1.0.0', %s);
            """,
            (test_org_id, approval_id, tampered_expected_hash),
        )
        res = cur.fetchone()[0]
        assert isinstance(res, dict)
        assert res.get("success") is False, "Auto-approve must reject when hash does not match expected hash"
        assert "HASH" in str(res.get("code", "")).upper() or "MISMATCH" in str(res.get("code", "")).upper()
