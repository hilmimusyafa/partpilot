"""Acceptance tests for database nomenclature validation and physical invariants.

Covers:
- ACC-TEST-01 (Valid complete model extraction)
- ACC-TEST-05 & ACC-TEST-16 (Special suffix preservation & anti-merge)
- ACC-TEST-13 (Asymmetric invariant: capacity 73 requires oil seal J)
- ACC-TEST-14 (Asymmetric invariant: D-cut shaft forbidden on capacity 73)
- ACC-TEST-15 (Asymmetric invariant: Keyway shaft forbidden on capacity 13)
- Governance invariant (Draft rule cannot be activated without human approval)
"""

import uuid
import psycopg
import pytest


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_22_valid_complete_model_matched(migrator_conn):
    """A-DB-22 (ACC-TEST-01): Valid complete model HG-KN73BJ-S100 is recognized with score >= 0.90."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    item_code = "SYN-HGKN-0001"
    wo_name = f"WO-MATCH-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
        # Ensure synthetic item exists in erp.item
        cur.execute(
            """
            INSERT INTO erp.item (item_code, item_name, item_group, stock_uom)
            VALUES (%s, 'Synthetic Servo Motor HG-KN73BJ-S100', 'All Item Groups', 'Unit')
            ON CONFLICT (item_code) DO NOTHING;
            """,
            (item_code,),
        )
        # Seed asset repair, work order, and part request
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
            VALUES (%s, 'Servo motor HG-KN73BJ-S100 tripping line 2')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

        # Call pp.tool_apply_part_match with valid match
        cur.execute(
            """
            SELECT pp.tool_apply_part_match(%s, %s, %s, 0.95, 'model number present in text');
            """,
            (test_org_id, wo_part_id, item_code),
        )
        res = cur.fetchone()[0]
        assert isinstance(res, dict)
        assert res.get("success") is True, f"Matching valid part must succeed, got {res}"

        # Verify updated row in pp.wo_part_request
        cur.execute(
            """
            SELECT matched_item_code, match_score, match_status, evidence
            FROM pp.wo_part_request
            WHERE wo_part_id = %s;
            """,
            (wo_part_id,),
        )
        matched_item, score, status, evidence = cur.fetchone()
        assert matched_item == item_code
        assert float(score) >= 0.90
        assert status == "matched"
        assert evidence is not None and "model" in str(evidence).lower()


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_23_negative_capacity_73_without_oil_seal_rejected(migrator_conn):
    """A-DB-23 (ACC-TEST-13): Capacity 73 without oil seal 'J' (HG-KN73 or HG-KN73B) is physically invalid."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    wo_name = f"WO-NO-SEAL-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
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
            VALUES (%s, 'Butuh servo HG-KN73B tanpa seal')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

        # Attempt to apply invalid model HG-KN73B (lacks 'J')
        cur.execute(
            """
            SELECT pp.tool_apply_part_match(%s, %s, 'HG-KN73B', 0.50, 'Invalid model lacking required oil seal J');
            """,
            (test_org_id, wo_part_id),
        )
        res = cur.fetchone()[0]
        assert isinstance(res, dict)

        cur.execute(
            """
            SELECT match_status, matched_item_code
            FROM pp.wo_part_request
            WHERE wo_part_id = %s;
            """,
            (wo_part_id,),
        )
        status, matched_item = cur.fetchone()
        assert status != "matched", "HG-KN73B lacking oil seal 'J' must NOT be marked matched"
        assert status in ("needs_confirmation", "pending", "rejected_invalid_nomenclature")


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_24_negative_capacity_73_d_cut_shaft_rejected(migrator_conn):
    """A-DB-24 (ACC-TEST-14): D-cut shaft on capacity 73 (HG-KN73BD) is physically invalid."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    wo_name = f"WO-DCUT-73-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
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
            VALUES (%s, 'Penggantian motor servo HG-KN73BD poros D-cut')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT pp.tool_apply_part_match(%s, %s, 'HG-KN73BD', 0.40, 'Poros D-cut dilarang pada kapasitas 73');
            """,
            (test_org_id, wo_part_id),
        )

        cur.execute(
            """
            SELECT match_status FROM pp.wo_part_request WHERE wo_part_id = %s;
            """,
            (wo_part_id,),
        )
        status = cur.fetchone()[0]
        assert status != "matched", "HG-KN73BD with D-cut shaft on 750W must not be matched"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_25_negative_capacity_13_keyway_shaft_rejected(migrator_conn):
    """A-DB-25 (ACC-TEST-15): Keyway shaft on capacity 13 (HG-KN13K) is physically invalid."""
    test_org_id = "00000000-0000-0000-0000-000000000001"
    wo_name = f"WO-KEYWAY-13-{uuid.uuid4().hex[:6].upper()}"

    with migrator_conn.cursor() as cur:
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
            VALUES (%s, 'Motor servo HG-KN13K 100W poros pasak aus')
            RETURNING wo_part_id;
            """,
            (wo_name,),
        )
        wo_part_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT pp.tool_apply_part_match(%s, %s, 'HG-KN13K', 0.40, 'Poros pasak K dilarang untuk kapasitas 13');
            """,
            (test_org_id, wo_part_id),
        )

        cur.execute(
            """
            SELECT match_status FROM pp.wo_part_request WHERE wo_part_id = %s;
            """,
            (wo_part_id,),
        )
        status = cur.fetchone()[0]
        assert status != "matched", "HG-KN13K with keyway shaft on 100W must not be matched"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_26_special_suffix_s100_identity_preserved(migrator_conn):
    """A-DB-26 (ACC-TEST-05 & ACC-TEST-16): Suffix -S100 is preserved and not merged into base items."""
    test_org_id = "00000000-0000-0000-0000-000000000001"

    with migrator_conn.cursor() as cur:
        # Create canonical items for both S100 and base versions
        cur.execute(
            """
            INSERT INTO pp.canonical_item (org_id, canonical_code, canonical_name, manufacturer, mpn)
            VALUES
                (%s, 'CANON-KN13BJ-S100', 'Servo Motor 100W Brake Seal S100', 'Mitsubishi Electric', 'HG-KN13BJ-S100'),
                (%s, 'CANON-KN13BJ-BASE', 'Servo Motor 100W Brake Seal Base', 'Mitsubishi Electric', 'HG-KN13BJ')
            ON CONFLICT (org_id, canonical_code) DO NOTHING;
            """,
            (test_org_id, test_org_id),
        )

        cur.execute(
            """
            SELECT canonical_id, mpn
            FROM pp.canonical_item
            WHERE org_id = %s AND mpn IN ('HG-KN13BJ-S100', 'HG-KN13BJ');
            """,
            (test_org_id,),
        )
        items = {r[1]: r[0] for r in cur.fetchall()}
        assert "HG-KN13BJ-S100" in items
        assert "HG-KN13BJ" in items
        assert items["HG-KN13BJ-S100"] != items["HG-KN13BJ"], "S100 variant must have distinct canonical identity"

        # Verify propose_mapping with -S100 does not auto-merge
        cur.execute(
            """
            SELECT pp.tool_propose_mapping(%s, 'HG-KN13BJ-S100', 'HG-KN13BJ', 0.85, 'nomenclature_crosswalk', '{"note": "Unverified suffix variation"}'::jsonb);
            """,
            (test_org_id,),
        )
        approval_id = cur.fetchone()[0]

        cur.execute(
            """
            SELECT status, doc_type, doc_name FROM pp.approval_request WHERE approval_id = %s;
            """,
            (approval_id,),
        )
        status, doc_type, doc_name = cur.fetchone()
        assert status == "pending", "Proposed mapping with -S100 must remain pending and not auto-approved"
        assert doc_type == "Item Mapping"


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_27_draft_nomenclature_rule_cannot_be_activated_without_approval(migrator_conn):
    """A-DB-27: Rule version in 'draft' status cannot be transitioned to 'active' without approved_by and approved_at."""
    test_org_id = "00000000-0000-0000-0000-000000000001"

    with migrator_conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pp.nomenclature_rule_version (
                org_id, family_code, manufacturer, catalog_version, version_tag,
                status, raw_definition_yaml, approved_by, approved_at
            ) VALUES (
                %s, 'GOV_TEST_FAMILY', 'Maker', 'CAT-GOV', 'v1.0.0',
                'draft', 'schema: test', NULL, NULL
            ) RETURNING rule_version_id;
            """,
            (test_org_id,),
        )
        rule_version_id = cur.fetchone()[0]

        # Direct transition to 'active' without approved_by/approved_at must be rejected by invariant
        with pytest.raises(psycopg.Error):
            cur.execute(
                """
                UPDATE pp.nomenclature_rule_version
                SET status = 'active'
                WHERE rule_version_id = %s;
                """,
                (rule_version_id,),
            )
