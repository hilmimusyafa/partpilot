"""Acceptance tests for database schema delta migration (008 contracts).

Validates master tables, entity hierarchies, multi-tenant organization bindings,
nomenclature rule versioning, clarification sessions, procurement handoffs,
and durable execution attempt tracking.
"""

import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_01_organization_table(migrator_conn):
    """A-DB-01: Verify pp.organization master table schema, keys, and defaults."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'organization'
            ORDER BY ordinal_position;
            """
        )
        rows = cur.fetchall()
        assert len(rows) > 0, "Table pp.organization must exist"

        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in rows}
        assert "org_id" in cols, "Column org_id missing in pp.organization"
        assert cols["org_id"]["type"] == "uuid"
        assert "org_code" in cols, "Column org_code missing in pp.organization"
        assert cols["org_code"]["nullable"] == "NO"
        assert "org_name" in cols, "Column org_name missing in pp.organization"
        assert cols["org_name"]["nullable"] == "NO"
        assert "default_currency" in cols, "Column default_currency missing in pp.organization"
        assert "created_at" in cols, "Column created_at missing in pp.organization"

        cur.execute(
            """
            SELECT c.conname, c.contype
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE n.nspname = 'pp' AND t.relname = 'organization';
            """
        )
        constraints = {r[0]: r[1] for r in cur.fetchall()}
        assert "p" in constraints.values(), "Primary key constraint missing on pp.organization"
        assert "u" in constraints.values(), "Unique constraint missing on pp.organization (org_code)"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_02_site_table(migrator_conn):
    """A-DB-02: Verify pp.site operational plant table schema and foreign keys."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'site'
            ORDER BY ordinal_position;
            """
        )
        rows = cur.fetchall()
        assert len(rows) > 0, "Table pp.site must exist"

        cols = {r[0]: {"type": r[1], "nullable": r[2]} for r in rows}
        assert "site_id" in cols, "Column site_id missing in pp.site"
        assert "org_id" in cols, "Column org_id missing in pp.site"
        assert cols["org_id"]["type"] == "uuid"
        assert cols["org_id"]["nullable"] == "NO"
        assert "site_name" in cols, "Column site_name missing in pp.site"
        assert "location_desc" in cols, "Column location_desc missing in pp.site"
        assert "created_at" in cols, "Column created_at missing in pp.site"

        cur.execute(
            """
            SELECT c.conname, c.contype
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE n.nspname = 'pp' AND t.relname = 'site' AND c.contype = 'f';
            """
        )
        fk_constraints = cur.fetchall()
        assert len(fk_constraints) > 0, "Foreign key constraint to pp.organization missing on pp.site"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_03_warehouse_ext_delta(migrator_conn):
    """A-DB-03: Verify pp.warehouse_ext contains org_id and site_id references."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'warehouse_ext';
            """
        )
        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in cur.fetchall()}
        assert "org_id" in cols, "Column org_id missing in pp.warehouse_ext"
        assert cols["org_id"]["type"] == "uuid"
        assert cols["org_id"]["nullable"] == "NO"
        assert "site_id" in cols, "Column site_id missing in pp.warehouse_ext"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_04_org_site_warehouse_hierarchy(migrator_conn):
    """A-DB-04: Verify relational hierarchy enforcement: Organization -> Site -> Warehouse."""
    with migrator_conn.cursor() as cur:
        test_org_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO pp.organization (org_id, org_code, org_name, default_currency)
            VALUES (%s, %s, %s, 'CNY');
            """,
            (test_org_id, f"ORG-TEST-{test_org_id[:8]}", "Hierarchy Test Org"),
        )

        test_site_id = f"SITE-TEST-{test_org_id[:8]}"
        cur.execute(
            """
            INSERT INTO pp.site (site_id, org_id, site_name, location_desc)
            VALUES (%s, %s, %s, 'Test Plant Site');
            """,
            (test_site_id, test_org_id, "Test Plant"),
        )

        invalid_org_id = str(uuid.uuid4())
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            cur.execute(
                """
                INSERT INTO pp.site (site_id, org_id, site_name)
                VALUES ('SITE-ORPHAN', %s, 'Orphan Site');
                """,
                (invalid_org_id,),
            )

        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            cur.execute(
                """
                INSERT INTO pp.warehouse_ext (warehouse_code, org_id, site_id)
                VALUES ('WH-NONEXISTENT', %s, 'SITE-NONEXISTENT');
                """,
                (test_org_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_05_pp_tables_org_id_columns(migrator_conn):
    """A-DB-05: Verify org_id column presence across all 14 domain tables in pp schema."""
    target_tables = [
        "source_catalog",
        "canonical_item",
        "item_canonical_map",
        "item_ext",
        "item_alias",
        "asset_ext",
        "work_order_ext",
        "wo_part_request",
        "transfer_lane",
        "transfer_ext",
        "decision_record",
        "approval_request",
        "agent_run",
        "agent_step",
    ]

    with migrator_conn.cursor() as cur:
        for tbl in target_tables:
            cur.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'pp' AND table_name = %s AND column_name = 'org_id';
                """,
                (tbl,),
            )
            row = cur.fetchone()
            assert row is not None, f"Table pp.{tbl} missing mandatory column org_id"
            assert row[1] == "uuid", f"Column pp.{tbl}.org_id must be uuid, found {row[1]}"
            assert row[2] == "NO", f"Column pp.{tbl}.org_id must be NOT NULL"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_06_approval_request_delta_columns(migrator_conn):
    """A-DB-06: Verify pp.approval_request delta columns for hash binding and policy mode."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'approval_request';
            """
        )
        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in cur.fetchall()}
        assert "doc_hash" in cols, "Column doc_hash missing in pp.approval_request"
        assert "policy_version" in cols, "Column policy_version missing in pp.approval_request"
        assert "approval_mode" in cols, "Column approval_mode missing in pp.approval_request"
        assert cols["approval_mode"]["nullable"] == "NO"
        assert "invalidation_reason" in cols, "Column invalidation_reason missing in pp.approval_request"

        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO pp.approval_request (doc_type, doc_name, status, approval_mode)
                VALUES ('Material Request', 'MR-TEST-INVALID-MODE', 'pending', 'unsupported_mode');
                """
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_07_nomenclature_rule_version_table(migrator_conn):
    """A-DB-07: Verify pp.nomenclature_rule_version schema, draft status, and governance defaults."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'nomenclature_rule_version'
            ORDER BY ordinal_position;
            """
        )
        rows = cur.fetchall()
        assert len(rows) > 0, "Table pp.nomenclature_rule_version must exist"

        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in rows}
        assert "rule_version_id" in cols
        assert "org_id" in cols
        assert "family_code" in cols
        assert "manufacturer" in cols
        assert "catalog_version" in cols
        assert "version_tag" in cols
        assert "status" in cols
        assert "draft" in str(cols["status"]["default"]), "Default status must be 'draft'"
        assert "raw_definition_yaml" in cols
        assert "approved_by" in cols
        assert cols["approved_by"]["nullable"] == "YES"
        assert "approved_at" in cols
        assert cols["approved_at"]["nullable"] == "YES"
        assert "created_at" in cols

        test_org_id = "00000000-0000-0000-0000-000000000001"
        cur.execute(
            """
            INSERT INTO pp.nomenclature_rule_version (
                org_id, family_code, manufacturer, catalog_version, version_tag, raw_definition_yaml
            ) VALUES (
                %s, 'TEST_FAMILY', 'Test Maker', 'CAT-V1', 'v1.0.0', 'schema: test'
            ) RETURNING status, approved_by, approved_at;
            """,
            (test_org_id,),
        )
        status, approved_by, approved_at = cur.fetchone()
        assert status == "draft", "Inserted rule version must default to status 'draft'"
        assert approved_by is None, "Draft rule version approved_by must be NULL"
        assert approved_at is None, "Draft rule version approved_at must be NULL"

        with pytest.raises(psycopg.errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO pp.nomenclature_rule_version (
                    org_id, family_code, manufacturer, catalog_version, version_tag, raw_definition_yaml
                ) VALUES (
                    %s, 'TEST_FAMILY', 'Test Maker', 'CAT-V1', 'v1.0.0', 'schema: duplicate'
                );
                """,
                (test_org_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_08_nomenclature_rule_pattern_and_attribute_tables(migrator_conn):
    """A-DB-08: Verify nomenclature pattern and attribute tables with cascade foreign keys."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'pp' AND table_name IN ('nomenclature_rule_pattern', 'nomenclature_rule_attribute');
            """
        )
        tables = {r[0] for r in cur.fetchall()}
        assert "nomenclature_rule_pattern" in tables
        assert "nomenclature_rule_attribute" in tables

        test_org_id = "00000000-0000-0000-0000-000000000001"
        cur.execute(
            """
            INSERT INTO pp.nomenclature_rule_version (
                org_id, family_code, manufacturer, catalog_version, version_tag, raw_definition_yaml
            ) VALUES (
                %s, 'CASCADE_FAMILY', 'Test Maker', 'CAT-CASCADE', 'v1.0.0', 'schema: test'
            ) RETURNING rule_version_id;
            """,
            (test_org_id,),
        )
        rule_version_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pp.nomenclature_rule_pattern (
                rule_version_id, position_idx, segment_name, regex_pattern, is_mandatory, attribute_mapped
            ) VALUES (%s, 1, 'SERIES', '^TEST-', true, 'series_name')
            RETURNING pattern_id;
            """,
            (rule_version_id,),
        )
        pattern_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pp.nomenclature_rule_attribute (
                rule_version_id, segment_name, symbol_value, decoded_meaning, is_verified_in_source
            ) VALUES (%s, 'SERIES', 'TEST', 'Test Meaning', true)
            RETURNING attr_id;
            """,
            (rule_version_id,),
        )
        attr_id = cur.fetchone()[0]

        cur.execute("DELETE FROM pp.nomenclature_rule_version WHERE rule_version_id = %s;", (rule_version_id,))

        cur.execute("SELECT COUNT(*) FROM pp.nomenclature_rule_pattern WHERE pattern_id = %s;", (pattern_id,))
        assert cur.fetchone()[0] == 0, "Pattern record must be cascade deleted"

        cur.execute("SELECT COUNT(*) FROM pp.nomenclature_rule_attribute WHERE attr_id = %s;", (attr_id,))
        assert cur.fetchone()[0] == 0, "Attribute record must be cascade deleted"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_09_clarification_session_and_turn_tables(migrator_conn):
    """A-DB-09: Verify clarification session and turn tables with 3-turn bound and idempotency."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'pp' AND table_name IN ('clarification_session', 'clarification_turn');
            """
        )
        tables = {r[0] for r in cur.fetchall()}
        assert "clarification_session" in tables
        assert "clarification_turn" in tables

        test_org_id = "00000000-0000-0000-0000-000000000001"
        cur.execute(
            """
            INSERT INTO erp.asset_repair (name, asset, failure_date, repair_status)
            VALUES ('WO-CLARIFY-TEST', 'AST-0001', now(), 'Pending')
            ON CONFLICT (name) DO NOTHING;
            """
        )
        cur.execute(
            """
            INSERT INTO pp.work_order_ext (work_order, org_id, maintenance_type, status)
            VALUES ('WO-CLARIFY-TEST', %s, 'corrective', 'open')
            ON CONFLICT (work_order) DO NOTHING;
            """,
            (test_org_id,),
        )
        cur.execute(
            """
            INSERT INTO pp.wo_part_request (work_order, org_id, requested_text, match_status)
            VALUES ('WO-CLARIFY-TEST', %s, 'Servo motor needing clarification', 'pending')
            RETURNING wo_part_id;
            """,
            (test_org_id,),
        )
        wo_part_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pp.clarification_session (org_id, wo_part_id, status, current_turn, max_turns)
            VALUES (%s, %s, 'active', 0, 3)
            RETURNING session_id;
            """,
            (test_org_id, wo_part_id),
        )
        session_id = cur.fetchone()[0]

        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                UPDATE pp.clarification_session
                SET current_turn = 4
                WHERE session_id = %s;
                """,
                (session_id,),
            )

        cur.execute(
            """
            INSERT INTO pp.clarification_turn (
                session_id, turn_number, condition_kind, target_attribute, question_text,
                system_rationale, turn_idempotency_key
            ) VALUES (
                %s, 1, 'MISSING_USER_INFO', 'brake', 'Does the motor have brake?',
                'Need brake spec', 'clarify-idemp-key-1'
            );
            """,
            (session_id,),
        )

        with pytest.raises(psycopg.errors.UniqueViolation):
            cur.execute(
                """
                INSERT INTO pp.clarification_turn (
                    session_id, turn_number, condition_kind, target_attribute, question_text,
                    system_rationale, turn_idempotency_key
                ) VALUES (
                    %s, 1, 'MISSING_USER_INFO', 'brake', 'Duplicate question?',
                    'Duplicate rationale', 'clarify-idemp-key-1'
                );
                """,
                (session_id,),
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_10_procurement_handoff_and_quote_tables(migrator_conn):
    """A-DB-10: Verify procurement handoff and vendor quote stub tables with quantity constraints."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'pp' AND table_name IN ('procurement_handoff', 'procurement_quote_stub');
            """
        )
        tables = {r[0] for r in cur.fetchall()}
        assert "procurement_handoff" in tables
        assert "procurement_quote_stub" in tables

        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO pp.procurement_handoff (
                    org_id, correlation_id, work_order_ref, wo_part_id, canonical_id,
                    manufacturer, complete_mpn, mandatory_specs, quantity, uom,
                    target_site, required_deadline, approved_proposal_ver
                ) VALUES (
                    '00000000-0000-0000-0000-000000000001', gen_random_uuid(), 'WO-INVALID-QTY',
                    1, 1, 'Maker', 'MPN-1', '{}'::jsonb, 0, 'Unit', 'SITE-B1', CURRENT_DATE + 7, 'v1'
                );
                """
            )


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_11_tool_execution_attempt_table_and_indexes(migrator_conn):
    """A-DB-11: Verify pp.tool_execution_attempt audit table schema and performance indexes."""
    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'pp' AND table_name = 'tool_execution_attempt';
            """
        )
        cols = {r[0]: {"type": r[1], "nullable": r[2], "default": r[3]} for r in cur.fetchall()}
        assert len(cols) > 0, "Table pp.tool_execution_attempt must exist"
        assert "attempt_id" in cols
        assert "tool_name" in cols
        assert "caller_role" in cols
        assert "input_payload" in cols
        assert "status" in cols
        assert "attempt_at" in cols
        assert "error_code" in cols
        assert "error_message" in cols
        assert "duration_ms" in cols

        cur.execute(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'pp' AND tablename = 'tool_execution_attempt';
            """
        )
        indexes = {r[0] for r in cur.fetchall()}
        assert "idx_tool_attempt_time" in indexes, "Index idx_tool_attempt_time missing"
        assert "idx_tool_attempt_status" in indexes, "Index idx_tool_attempt_status missing"

        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                """
                INSERT INTO pp.tool_execution_attempt (tool_name, caller_role, input_payload, status)
                VALUES ('tool_test', 'pp_worker', '{}'::jsonb, 'unsupported_status');
                """
            )
