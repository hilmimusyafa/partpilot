-- Additive exact lookup function and indexes for Bearing MVP
-- STABLE, SECURITY INVOKER, pure SQL, zero external dependencies or fuzzy matching.

CREATE OR REPLACE FUNCTION pp.lookup_bearing_exact(
    p_company text,
    p_category text,
    p_warehouse text,
    p_item_name text
)
RETURNS TABLE (
    item_code text,
    item_name text,
    description text,
    warehouse text,
    actual_qty numeric,
    reserved_qty numeric,
    available_qty numeric
)
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
SELECT i.item_code, i.item_name, i.description, b.warehouse,
       b.actual_qty, b.reserved_qty,
       b.actual_qty - b.reserved_qty AS available_qty
FROM erp.bin AS b
JOIN erp.item AS i ON i.item_code = b.item_code
JOIN erp.warehouse AS w ON w.name = b.warehouse
WHERE w.company = p_company
  AND b.warehouse = p_warehouse
  AND i.item_group = p_category
  AND i.item_group = 'Bearing'
  AND i.item_name = p_item_name
  AND NOT i.disabled AND NOT w.disabled AND NOT w.is_group
ORDER BY i.item_code;
$$;

CREATE INDEX IF NOT EXISTS pp_bearing_item_group_name_code_idx
  ON erp.item (item_group, item_name, item_code);

CREATE INDEX IF NOT EXISTS pp_bearing_bin_warehouse_item_idx
  ON erp.bin (warehouse, item_code);
