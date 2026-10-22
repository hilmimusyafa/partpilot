"""Acceptance tests for concurrent stock reservation (ACC-TEST-08).

Verifies atomic stock reservation under race conditions where two parallel connections
attempt to reserve the last remaining stock unit simultaneously. Exactly one must succeed.
"""

import threading
import uuid
import psycopg
import pytest
from tests.acceptance.db.conftest import create_role_connection


@pytest.mark.acceptance
@pytest.mark.db_layer
def test_a_db_12_concurrent_stock_reservation_race_condition(migrator_conn):
    """A-DB-12 (ACC-TEST-08): Two parallel connections race for last unit of stock.

    Invariant:
    - Exactly one reservation succeeds.
    - One reservation is rejected with insufficient stock indication.
    - erp.bin.reserved_qty equals 1 and never exceeds actual_qty (anti-over-reservation).
    """
    test_org_id = "00000000-0000-0000-0000-000000000001"
    item_code = f"ITEM-RACE-{uuid.uuid4().hex[:6].upper()}"
    warehouse = f"WH-RACE-{uuid.uuid4().hex[:4].upper()}"

    # Step 1: Seed minimal synthetic fixtures as pp_migrator
    with migrator_conn.cursor() as cur:
        # Warehouse type and warehouse
        cur.execute(
            """
            INSERT INTO erp.warehouse_type (name) VALUES ('Stores')
            ON CONFLICT (name) DO NOTHING;
            """
        )
        cur.execute(
            """
            INSERT INTO erp.warehouse (name, warehouse_name, warehouse_type, company)
            VALUES (%s, %s, 'Stores', 'Midea Indonesia')
            ON CONFLICT (name) DO NOTHING;
            """,
            (warehouse, warehouse),
        )

        # Item group and item
        cur.execute(
            """
            INSERT INTO erp.item_group (name) VALUES ('All Item Groups')
            ON CONFLICT (name) DO NOTHING;
            """
        )
        cur.execute(
            """
            INSERT INTO erp.item (item_code, item_name, item_group, stock_uom)
            VALUES (%s, 'Race Test Item', 'All Item Groups', 'Unit')
            ON CONFLICT (item_code) DO NOTHING;
            """,
            (item_code,),
        )

        # erp.bin with exactly 1 unit of actual stock and 0 reserved
        cur.execute(
            """
            INSERT INTO erp.bin (item_code, warehouse, actual_qty, reserved_qty, ordered_qty, indented_qty)
            VALUES (%s, %s, 1.000, 0.000, 0.000, 0.000)
            ON CONFLICT (item_code, warehouse) DO UPDATE
            SET actual_qty = 1.000, reserved_qty = 0.000;
            """,
            (item_code, warehouse),
        )

        # Two distinct work orders and part requests
        wo_1 = f"WO-RACE-1-{uuid.uuid4().hex[:4]}"
        wo_2 = f"WO-RACE-2-{uuid.uuid4().hex[:4]}"
        for wo in [wo_1, wo_2]:
            cur.execute(
                """
                INSERT INTO erp.asset_repair (name, asset, failure_date, repair_status)
                VALUES (%s, 'AST-0001', now(), 'Pending')
                ON CONFLICT (name) DO NOTHING;
                """,
                (wo,),
            )
            cur.execute(
                """
                INSERT INTO pp.work_order_ext (work_order, maintenance_type)
                VALUES (%s, 'corrective')
                ON CONFLICT (work_order) DO NOTHING;
                """,
                (wo,),
            )

        cur.execute(
            """
            INSERT INTO pp.wo_part_request (work_order, requested_text)
            VALUES (%s, 'Need 1 unit race item')
            RETURNING wo_part_id;
            """,
            (wo_1,),
        )
        wo_part_1 = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO pp.wo_part_request (work_order, requested_text)
            VALUES (%s, 'Need 1 unit race item')
            RETURNING wo_part_id;
            """,
            (wo_2,),
        )
        wo_part_2 = cur.fetchone()[0]

    # Step 2: Concurrent execution of pp.tool_reserve_stock across two parallel connections
    results = []
    errors = []
    barrier = threading.Barrier(2)

    def worker_reserve(part_id):
        conn = None
        try:
            conn = create_role_connection("pp_app", autocommit=True)
            barrier.wait(timeout=5)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pp.tool_reserve_stock(%s, %s, %s, 1.0);
                    """,
                    (test_org_id, part_id, warehouse),
                )
                res = cur.fetchone()[0]
                results.append((part_id, res))
        except Exception as ex:
            errors.append((part_id, ex))
        finally:
            if conn:
                conn.close()

    try:
        t1 = threading.Thread(target=worker_reserve, args=(wo_part_1,))
        t2 = threading.Thread(target=worker_reserve, args=(wo_part_2,))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        # Step 3: Assertions on results and final stock integrity
        # If 008 is not yet implemented, execution will raise UndefinedFunction or error
        if errors:
            # Re-raise first database error to reflect implementation state
            raise errors[0][1]

        assert len(results) == 2, "Both workers must complete"

        # Analyze outcomes: exactly one must report success: true
        successes = [r for r in results if isinstance(r[1], dict) and r[1].get("success") is True]
        rejections = [r for r in results if isinstance(r[1], dict) and r[1].get("success") is False]

        assert len(successes) == 1, f"Expected exactly 1 successful reservation, got {len(successes)}"
        assert len(rejections) == 1, f"Expected exactly 1 rejected reservation, got {len(rejections)}"

        rejected_code = rejections[0][1].get("code")
        assert rejected_code in ("INSUFFICIENT_STOCK", "REJECTED_STOCK_UNAVAILABLE"), (
            f"Rejection code must indicate insufficient stock, got {rejected_code}"
        )

        # Verify database state in erp.bin
        with migrator_conn.cursor() as cur:
            cur.execute(
                """
                SELECT actual_qty, reserved_qty
                FROM erp.bin
                WHERE item_code = %s AND warehouse = %s;
                """,
                (item_code, warehouse),
            )
            actual_qty, reserved_qty = cur.fetchone()
            assert reserved_qty == 1.000, f"reserved_qty must be exactly 1.000, found {reserved_qty}"
            assert reserved_qty <= actual_qty, f"Anti-over-reservation violated: reserved {reserved_qty} > actual {actual_qty}"
    finally:
        with migrator_conn.cursor() as cur:
            cur.execute("DELETE FROM erp.bin WHERE item_code = %s;", (item_code,))
            cur.execute("DELETE FROM pp.wo_part_request WHERE wo_part_id IN (%s, %s);", (wo_part_1, wo_part_2))
            cur.execute("DELETE FROM pp.work_order_ext WHERE work_order IN (%s, %s);", (wo_1, wo_2))
            cur.execute("DELETE FROM erp.asset_repair WHERE name IN (%s, %s);", (wo_1, wo_2))
            cur.execute("DELETE FROM erp.item WHERE item_code = %s;", (item_code,))
            cur.execute("DELETE FROM erp.warehouse WHERE name = %s;", (warehouse,))
