-- Immutable demo PO, created only in the manager decision transaction.
-- Deliberately no FK to resettable workflow tables: decisions are archived by
-- demo_reset, while the PO and its approval evidence remain readable by ID.
CREATE TABLE IF NOT EXISTS pp.demo_purchase_order (
 id text PRIMARY KEY DEFAULT gen_random_uuid()::text,
 number text NOT NULL UNIQUE,
 decision_id text NOT NULL UNIQUE,
 run_id text NOT NULL UNIQUE,
 created_at timestamptz NOT NULL,
 snapshot jsonb NOT NULL CHECK(jsonb_typeof(snapshot)='object')
);
CREATE TRIGGER demo_purchase_order_immutable BEFORE UPDATE OR DELETE ON pp.demo_purchase_order
 FOR EACH ROW EXECUTE FUNCTION pp.demo_immutable();
CREATE TRIGGER demo_purchase_order_no_truncate BEFORE TRUNCATE ON pp.demo_purchase_order
 FOR EACH STATEMENT EXECUTE FUNCTION pp.demo_immutable();

CREATE FUNCTION pp.demo_create_purchase_order() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pp AS $$
DECLARE r pp.demo_run; c pp.demo_comparison; opt jsonb; q jsonb; current_quote jsonb;
 qty numeric; unit_price numeric; shipping numeric; tax numeric; subtotal numeric; supplier_name text;
BEGIN
 SELECT * INTO r FROM pp.demo_run WHERE id=NEW.run_id FOR UPDATE;
 SELECT * INTO c FROM pp.demo_comparison WHERE id=NEW.comparison_id AND run_id=NEW.run_id;
 SELECT value INTO opt FROM jsonb_array_elements(c.snapshot->'eligible_complete_options')
  WHERE value->>'option_id'=NEW.option_id;
 IF opt IS NULL THEN RAISE EXCEPTION 'option_ineligible_or_expired'; END IF;
 IF opt->>'source_kind'='warehouse' THEN RETURN NEW; END IF;
 q=opt->'quote';
 IF opt->>'source_kind' IS DISTINCT FROM 'vendor' OR r.company IS DISTINCT FROM 'SYN-COMPANY-01'
  OR NEW.procurement_executed OR opt->>'valid_until' IS NULL
  OR (opt->>'valid_until')::timestamptz<=now()
  OR q->>'valid_until' IS DISTINCT FROM opt->>'valid_until'
  OR q->'identity' IS DISTINCT FROM r.snapshot->'identity'
  OR NOT COALESCE(q->'identity' ?& ARRAY['brand','base','suffix'],false)
  OR q->>'currency' IS DISTINCT FROM 'IDR' OR q->>'quantity_unit' IS DISTINCT FROM 'Nos'
  OR q->>'destination_warehouse_id' IS DISTINCT FROM r.snapshot->>'destination_warehouse_id'
  OR opt->>'source_id' IS NULL
  OR NOT COALESCE(q ?& ARRAY['unit_price','shipping_amount','tax_amount','qty_available'],false)
 THEN RAISE EXCEPTION 'invalid_comparison'; END IF;
 SELECT response->'quote' INTO current_quote FROM pp.demo_outbox
  WHERE run_id=NEW.run_id AND vendor_id=opt->>'source_id' AND jsonb_typeof(response->'quote')='object'
  ORDER BY CASE kind WHEN 'price_counteroffer' THEN 0 ELSE 1 END LIMIT 1;
 IF current_quote IS DISTINCT FROM q THEN RAISE EXCEPTION 'quote_changed'; END IF;
 qty=(r.snapshot->>'quantity')::numeric;
 unit_price=(q->>'unit_price')::numeric; shipping=(q->>'shipping_amount')::numeric; tax=(q->>'tax_amount')::numeric;
 IF qty IS NULL OR qty<=0 OR qty::text IN ('NaN','Infinity','-Infinity')
  OR (opt->>'quantity')::numeric IS DISTINCT FROM qty
  OR COALESCE((q->>'qty_available')::numeric,0)<qty
  OR unit_price IS NULL OR shipping IS NULL OR tax IS NULL
  OR unit_price<0 OR shipping<0 OR tax<0
  OR unit_price::text IN ('NaN','Infinity','-Infinity') OR shipping::text IN ('NaN','Infinity','-Infinity') OR tax::text IN ('NaN','Infinity','-Infinity')
 THEN RAISE EXCEPTION 'invalid_comparison'; END IF;
 subtotal=qty*unit_price;
 IF opt->>'source_id' LIKE 'WA-%' THEN
  SELECT label INTO supplier_name FROM pp.wa_recipient WHERE id=opt->>'source_id';
 END IF;
 INSERT INTO pp.demo_purchase_order(number,decision_id,run_id,created_at,snapshot)
 VALUES('PO-DEMO-'||to_char(NEW.created_at AT TIME ZONE 'Asia/Jakarta','YYYYMMDD')||'-'||upper(left(replace(NEW.id,'-',''),12)),
  NEW.id,NEW.run_id,NEW.created_at,jsonb_build_object(
   'schema_version','purchase-order-v1','simulated',true,'status','generated','currency','IDR',
   'issuer',jsonb_build_object('name','PT PartPilot','address','Jl. Contoh Industri No. 123, Cikarang - ALAMAT DUMMY',
    'email','purchasing@partpilot.example','phone','Nomor telepon dummy: 000-0000-0000'),
   'supplier',jsonb_build_object('id',opt->>'source_id','name',COALESCE(supplier_name,opt->>'source_id'),
    'address','Alamat pemasok belum diberikan (dummy untuk demo)'),
   'ship_to',jsonb_build_object('warehouse_id',r.snapshot->>'destination_warehouse_id',
    'name','PT PartPilot - Gudang Penerima','address','Jl. Contoh Gudang No. 45, Cikarang - ALAMAT DUMMY'),
   'identity',q->'identity','quantity',qty::text,'quantity_unit',q->>'quantity_unit',
   'unit_price',unit_price::text,'line_subtotal',subtotal::text,'shipping_amount',shipping::text,
   'tax_amount',tax::text,'total',(subtotal+shipping+tax)::text,
   'quote_id',q->>'quote_id','quote_revision',q->'revision','delivered_eta',q->>'delivered_eta',
   'quote_valid_until',q->>'valid_until','comparison_id',NEW.comparison_id,'option_id',NEW.option_id,
   'approval',jsonb_build_object('decision_id',NEW.id,'approved_at',NEW.created_at,'method','manager_selection','request_key',NEW.request_key),
   'terms',jsonb_build_array('Dokumen simulasi; tidak dikirim kepada pemasok dan bukan pesanan pembelian nyata.',
    'Pembayaran: NET 30 hari (ketentuan dummy untuk demo).',
    'Pengiriman: sesuai estimasi penawaran; alamat dan kontak perusahaan adalah dummy.',
    'Pajak mengikuti nominal penawaran; dokumen ini bukan faktur pajak.'),
   'procurement_executed',false));
 INSERT INTO pp.demo_audit(run_id,event_type,payload)
  SELECT NEW.run_id,'purchase_order_generated',jsonb_build_object('purchase_order_id',id,'number',number,'decision_id',NEW.id)
  FROM pp.demo_purchase_order WHERE decision_id=NEW.id;
 RETURN NEW;
END $$;
CREATE TRIGGER demo_purchase_order_on_decision AFTER INSERT ON pp.demo_decision
 FOR EACH ROW EXECUTE FUNCTION pp.demo_create_purchase_order();
REVOKE ALL ON pp.demo_purchase_order FROM PUBLIC;
REVOKE ALL ON FUNCTION pp.demo_create_purchase_order() FROM PUBLIC;
-- Deployment: GRANT SELECT ON pp.demo_purchase_order TO pp_demo_api;
-- Do NOT grant INSERT/UPDATE/DELETE/TRUNCATE, or EXECUTE on the trigger function.
-- Existing EXECUTE on pp.demo_choose is the sole manager approval entry point.
