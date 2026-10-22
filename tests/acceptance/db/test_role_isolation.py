"""Acceptance tests for database role isolation and privilege boundaries (ACC-TEST-10).

Verifies that pp_agent is strictly blocked from direct table modifications,
approval decisions, and administrative actions; pp_console is authorized for approvals;
pp_worker is constrained to background tasks without direct access to decision tables;
and positive controls confirm permitted execution and outbox/handoff paths.
"""

import json
import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_15_agent_role_cannot_modify_erp_tables(agent_conn):
    """A-DB-15 (ACC-TEST-10): Role pp_agent is denied direct INSERT/UPDATE/DELETE on erp tables."""
    # Attempt direct INSERT into erp.stock_entry
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO erp.stock_entry (name, purpose)
                VALUES ('SE-ILLEGAL-DIRECT', 'Material Transfer');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("stock_entry" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )

    # Attempt direct UPDATE on erp.purchase_order
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE erp.purchase_order
                SET status = 'To Receive and Bill'
                WHERE name = 'PO-DUMMY';
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("purchase_order" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )

    # Attempt direct DELETE on erp.bin
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM erp.bin WHERE item_code = 'ITEM-DUMMY';
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("bin" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_16_agent_role_cannot_modify_pp_tables(agent_conn):
    """A-DB-16 (ACC-TEST-10): Role pp_agent is denied direct INSERT/UPDATE/DELETE on pp tables."""
    # Attempt direct UPDATE on pp.approval_policy
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pp.approval_policy SET min_value = 0 WHERE level = 1;
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("approval_policy" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )

    # Attempt direct INSERT into pp.work_order_ext
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pp.work_order_ext (work_order, maintenance_type)
                VALUES ('WO-DIRECT-ILLEGAL', 'corrective');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("work_order_ext" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_17_agent_role_cannot_execute_decide_approval(agent_conn):
    """A-DB-17 (ACC-TEST-10): Role pp_agent is denied execute permission on pp.decide_approval."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with agent_conn.cursor() as cur:
            cur.execute(
                """
                SELECT pp.decide_approval(1, 'approved', 'Unauthorized Actor', 'Bypass test');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("decide_approval" in err_msg or "function" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target function object specifically, got: {exc_info.value}"
    )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_18_agent_role_cannot_access_secrets_or_ddl(agent_conn):
    """A-DB-18 (ACC-TEST-10): Role pp_agent is denied DDL and administrative privileges."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with agent_conn.cursor() as cur:
            cur.execute("CREATE TABLE pp.temp_leak (id int);")

    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with agent_conn.cursor() as cur:
            cur.execute("ALTER TABLE pp.work_order_ext ADD COLUMN leak_col text;")


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_19_console_role_can_execute_decide_approval(migrator_conn, console_conn):
    """A-DB-19 (ACC-TEST-10): Role pp_console is authorized to execute pp.decide_approval."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    doc_name = f"DOC-CONSOLE-{uuid.uuid4().hex[:6]}"

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

    # Execute decide_approval as pp_console
    with console_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pp.decide_approval(%s, 'approved', 'Operator Alpha', 'Console authorized note');
            """,
            (approval_id,),
        )

    # Verify decision recorded
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT status, decided_by, note
            FROM pp.approval_request
            WHERE approval_id = %s;
            """,
            (approval_id,),
        )
        status, decided_by, note = cur.fetchone()
        assert status == "approved"
        assert decided_by == "Operator Alpha"
        assert note == "Console authorized note"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_20_worker_role_has_restricted_permissions(worker_conn):
    """A-DB-20 (ACC-TEST-10): Role pp_worker cannot decide approvals or modify decision/erp tables."""
    # Worker cannot execute decide_approval
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with worker_conn.cursor() as cur:
            cur.execute(
                """
                SELECT pp.decide_approval(1, 'approved', 'Worker Process', 'Attempt');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("decide_approval" in err_msg or "function" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target function object specifically, got: {exc_info.value}"
    )

    # Worker cannot directly insert into erp tables
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with worker_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO erp.stock_entry (name, purpose)
                VALUES ('SE-WORKER-ILLEGAL', 'Material Transfer');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("stock_entry" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target table object specifically, got: {exc_info.value}"
    )

    # Worker cannot directly modify decision tables (pp.approval_request or pp.decision_record)
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with worker_conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pp.approval_request SET status = 'approved' WHERE approval_id = 1;
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("approval_request" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target decision table specifically, got: {exc_info.value}"
    )

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc_info:
        with worker_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pp.decision_record (wo_part_id, chosen)
                VALUES (1, 'bypass_attempt');
                """
            )
    err_msg = str(exc_info.value).lower()
    assert ("decision_record" in err_msg or "table" in err_msg) and "schema" not in err_msg, (
        f"Rejection must target decision table specifically, got: {exc_info.value}"
    )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_36_agent_role_can_execute_contract_tools_with_audit(agent_conn, migrator_conn):
    """A-DB-36 (ACC-TEST-10 Positive Control): pp_agent can execute contract tools and record audit attempts."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    item_code = "SYN-HGKN-0001"
    wo_name = f"WO-AGENT-EXEC-{uuid.uuid4().hex[:6].upper()}"

    # Step 1: Pre-seed test work order as migrator
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO erp.item (item_code, item_name, item_group, stock_uom)
            VALUES (%s, 'Synthetic Servo Motor HG-KN73BJ-S100', 'All Item Groups', 'Unit')
            ON CONFLICT (item_code) DO NOTHING;
            """,
            (item_code,),
        )
        cur.execute(
            """
            INSERT INTO erp.asset_repair (name, asset, failure_date, repair_status)
            VALUES (%s, 'AST-0001', now(), 'Pending')
            ON CONFLICT (name) DO NOTHING;
            """,
            (wo_name,),
        )
        cur.execute(
            """
            INSERT INTO pp.work_order_ext (work_order, maintenance_type)
            VALUES (%s, 'corrective')
            ON CONFLICT (work_order) DO NOTHING;
            """,
            (wo_name,),
        )
        cur.execute(
            """
            INSERT INTO pp.wo_part_request (work_order, requested_text)
            VALUES (%s, 'Motor servo HG-KN73BJ-S100 tripping')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

    # Step 2: Positive control for pp_agent execution of pp.tool_start_run
    with agent_conn.cursor() as cur:
        cur.execute(
            """
            SELECT pp.tool_start_run(%s, %s, 'manual_start', 'pp_agent_worker');
            """,
            (test_org_id, wo_name),
        )
        run_id = cur.fetchone()[0]
        assert run_id is not None and run_id > 0

        # Positive control for pp_agent execution of pp.tool_apply_part_match
        cur.execute(
            """
            SELECT pp.tool_apply_part_match(%s, %s, %s, 0.95, 'Positive control match verification');
            """,
            (test_org_id, wo_part_id, item_code),
        )
        match_res = cur.fetchone()[0]
        assert isinstance(match_res, dict)
        assert match_res.get("success") is True

        # Positive control for pp_agent recording audit attempt
        cur.execute(
            """
            INSERT INTO pp.tool_execution_attempt (
                org_id, run_id, tool_name, caller_role, input_payload, status
            ) VALUES (
                %s, %s, 'pp.tool_start_run', 'pp_agent', '{"step": 1}'::jsonb, 'attempted'
            ) RETURNING attempt_id;
            """,
            (test_org_id, run_id),
        )
        attempt_id = cur.fetchone()[0]
        assert attempt_id is not None and attempt_id > 0


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_37_worker_role_can_write_outbox_handoff_path(worker_conn, migrator_conn):
    """A-DB-37 (ACC-TEST-10 Positive Control): pp_worker can write to outbox and procurement handoff paths."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    item_code = "SYN-HGKN-0001"
    wo_name = f"WO-WORKER-OUT-{uuid.uuid4().hex[:6].upper()}"
    corr_id = str(uuid.uuid4())

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO erp.item (item_code, item_name, item_group, stock_uom)
            VALUES (%s, 'Synthetic Servo Motor HG-KN73BJ-S100', 'All Item Groups', 'Unit')
            ON CONFLICT (item_code) DO NOTHING;
            """,
            (item_code,),
        )
        cur.execute(
            """
            INSERT INTO erp.asset_repair (name, asset, failure_date, repair_status)
            VALUES (%s, 'AST-0001', now(), 'Pending')
            ON CONFLICT (name) DO NOTHING;
            """,
            (wo_name,),
        )
        cur.execute(
            """
            INSERT INTO pp.work_order_ext (work_order, maintenance_type)
            VALUES (%s, 'corrective')
            ON CONFLICT (work_order) DO NOTHING;
            """,
            (wo_name,),
        )
        cur.execute(
            """
            INSERT INTO pp.wo_part_request (work_order, requested_text)
            VALUES (%s, 'Worker procurement part need')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT canonical_id FROM pp.canonical_item LIMIT 1;
            """
        )
        row = cur.fetchone()
        canonical_id = row[0] if row else 1

    with worker_conn.cursor() as cur:
        # 1. Positive control: pp_worker writes to vendor message outbox
        cur.execute(
            """
            INSERT INTO pp.vendor_message (
                contact_id, direction, channel, kind, template_name, body, status
            ) VALUES (
                1, 'out', 'whatsapp', 'template', 'rfq_request_v1',
                'RFQ Outbox dispatch test', 'queued'
            ) RETURNING message_id;
            """
        )
        msg_id = cur.fetchone()[0]
        assert msg_id is not None and msg_id > 0

        # 2. Positive control: pp_worker writes to procurement handoff path
        cur.execute(
            """
            INSERT INTO pp.procurement_handoff (
                org_id, correlation_id, work_order_ref, wo_part_id, canonical_id,
                manufacturer, complete_mpn, mandatory_specs, quantity, uom,
                target_site, required_deadline, approved_proposal_ver, status
            ) VALUES (
                %s, %s, %s, %s, %s,
                'Mitsubishi Electric', 'HG-KN73BJ-S100', '{"brake": true}'::jsonb, 1.0, 'Unit',
                'SITE-B2', CURRENT_DATE + interval '7 days', 'v1.0.0', 'dispatched'
            ) RETURNING handoff_id;
            """,
            (test_org_id, corr_id, wo_name, wo_part_id, canonical_id),
        )
        handoff_id = cur.fetchone()[0]
        assert handoff_id is not None
