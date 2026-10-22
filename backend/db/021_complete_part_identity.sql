-- Closed exact-part identities. Complete units retain their whole designation
-- and scope; no insert substitution or CR -> /LP99 upgrade is implicit.
CREATE OR REPLACE FUNCTION pp.valid_part_identity(p_identity jsonb)
RETURNS boolean LANGUAGE sql IMMUTABLE PARALLEL SAFE
SET search_path=pg_catalog AS $$
 SELECT CASE WHEN jsonb_typeof(p_identity) IS DISTINCT FROM 'object' THEN false ELSE
  COALESCE(
   p_identity = '{"brand":"RHP","base":"PSF20","suffix":"CR","manufacturer":"RHP","full_designation":"PSF20CR","unit_scope":"complete_housed_unit"}'::jsonb
   OR p_identity = '{"brand":"RHP","base":"PSF20","suffix":"/LP99","manufacturer":"RHP","full_designation":"PSF20/LP99","unit_scope":"complete_housed_unit"}'::jsonb
   OR (p_identity ?& ARRAY['brand','base','suffix']
       AND p_identity - ARRAY['brand','base','suffix'] = '{}'::jsonb
       AND p_identity->>'brand' IN ('NTN','NSK','SKF','KOYO','FAG','NACHI')
       AND p_identity->>'base' ~ '^6[0-9]{3}$'
       AND p_identity->>'suffix' IN ('LLU','LLB','LLF','LLH','ZZ','2RS','DDU','OPEN')), false)
 END;
$$;

ALTER TABLE pp.demo_run ADD CONSTRAINT demo_run_exact_part_identity
 CHECK (pp.valid_part_identity(snapshot->'identity'));
ALTER TABLE pp.demo_purchase_order ADD CONSTRAINT demo_po_exact_part_identity
 CHECK (pp.valid_part_identity(snapshot->'identity'));

CREATE OR REPLACE FUNCTION pp.guard_complete_part_source()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,pp,erp AS $$
BEGIN
 IF NOT pp.valid_part_identity(NEW.snapshot->'identity') THEN
  RAISE EXCEPTION 'invalid_source_snapshot';
 END IF;
 IF NEW.snapshot->'identity' ? 'full_designation' AND NOT EXISTS (
  SELECT 1 FROM pp.wo_identification_session s
   JOIN erp.item i ON i.item_code=s.result->'identified_candidate'->>'item_code'
   JOIN erp.bin b ON b.item_code=i.item_code AND b.warehouse=s.warehouse
   JOIN erp.warehouse w ON w.name=b.warehouse AND w.company=s.company
  WHERE s.id=NEW.session_id AND s.version=NEW.session_version AND s.state='identified'
    AND s.company=NEW.company AND NOT w.disabled AND NOT w.is_group
    AND i.brand='RHP' AND NOT i.disabled AND i.is_stock_item
    AND i.item_group='Bearing' AND i.stock_uom='Nos'
    AND upper(btrim(i.item_name))='RHP '||(NEW.snapshot->'identity'->>'full_designation')
 ) THEN
  RAISE EXCEPTION 'identity_or_version_conflict';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER demo_run_complete_part_source BEFORE INSERT ON pp.demo_run
 FOR EACH ROW EXECUTE FUNCTION pp.guard_complete_part_source();
REVOKE ALL ON FUNCTION pp.guard_complete_part_source() FROM PUBLIC;
