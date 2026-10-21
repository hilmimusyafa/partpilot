-- PartPilot v3: skema tiga lapis (PostgreSQL)
--   midea : staging, kolom persis seperti berkas Midea, satu katalog per gudang
--   erp   : inti berbentuk ERPNext 15 (nama tabel dan field mengikuti doctype yang dibaca)
--   pp    : ekstensi PartPilot, menunjuk ke lapis erp, tidak mengubah tabelnya

CREATE SCHEMA midea;
CREATE SCHEMA erp;
CREATE SCHEMA pp;

-- =====================================================================
-- LAPIS MIDEA (staging)
-- =====================================================================
CREATE TABLE midea.spare_parts_report (       -- Midea: Spare parts inventory report (37 kolom). Satu baris = satu batch penerimaan.
  line_id                       serial PRIMARY KEY,
  catalog_code                  text NOT NULL,            -- database gudang asal baris ini (B1, B2, W3, W4, W5)
  ou_organization               text,                     -- OU Organization
  warehouse_name                text,                     -- Warehouse Name
  storage_location_name         text,                     -- Storage Location Name
  item_code                     text,                     -- Item Code
  item_description              text,                     -- Item Description
  item_model                    text,                     -- Item Model
  brand                         text,                     -- Brand
  unit                          text,                     -- Unit
  inventory_type                text,                     -- Inventory Type (旧件 = barang lama)
  inventory_upper_limit         numeric,                  -- Inventory Upper Limit
  inventory_lower_limit         numeric,                  -- Inventory Lower Limit
  obsolete_time                 int,                      -- Obsolete Time (hari sejak diterima)
  inventory_quantity            numeric,                  -- Inventory Quantity
  tax_exclusive_price           numeric,
  tax_inclusive_price           numeric,
  tax_exclusive_amount          numeric,
  tax_inclusive_amount          numeric,
  wbs_number                    text,
  is_replacement                text,
  is_automatically_scrapped     text,
  is_zero_inventory             text,
  currency_code                 text,
  exchange_rate                 numeric,
  department_name               text,
  receiving_department          text,
  budget_item_name              text,
  delivery_cycle_days           int,                      -- Delivery Cycle (Days)
  receiving_time                date,                     -- Receiving Time
  receiving_batch_number        text,                     -- Receiving Batch Number
  supplier_code                 text,                     -- Supplier Code
  supplier_name                 text,                     -- Supplier Name
  purchase_requisition_number   text,
  purchase_requisition_creator  text,
  budget_organization           text,
  buyer                         text,
  material_scene_attribute      text,
  budget_unit_description       text
);

CREATE TABLE midea.aging_report_subinventory (   -- Midea: JC.Inventory aging report, diringkas per subinventory
  organization     text NOT NULL,
  report_date      date NOT NULL,
  subinventory     text NOT NULL,
  description      text,
  gl_account       text,
  item_rows        int NOT NULL,
  amount           numeric(20,2) NOT NULL,
  median_age_days  numeric(8,1),
  max_age_days     numeric(8,1),
  negative_rows    int NOT NULL DEFAULT 0,
  PRIMARY KEY (organization, subinventory)
);

-- =====================================================================
-- LAPIS ERP (bentuk ERPNext 15; kunci berupa nama dokumen seperti di ERPNext)
-- =====================================================================
CREATE TABLE erp.company (
  name              text PRIMARY KEY,
  default_currency  char(3) NOT NULL DEFAULT 'IDR'
);

CREATE TABLE erp.warehouse_type (name text PRIMARY KEY);

CREATE TABLE erp.warehouse (                -- ERPNext: Warehouse (pohon lewat parent_warehouse)
  name              text PRIMARY KEY,
  warehouse_name    text NOT NULL,
  parent_warehouse  text REFERENCES erp.warehouse,
  is_group          boolean NOT NULL DEFAULT false,
  company           text NOT NULL REFERENCES erp.company,
  disabled          boolean NOT NULL DEFAULT false,
  warehouse_type    text REFERENCES erp.warehouse_type,
  account           text                       -- Midea (laporan umur): Account
);

CREATE TABLE erp.item_group (               -- ERPNext: Item Group
  name               text PRIMARY KEY,
  parent_item_group  text REFERENCES erp.item_group,
  is_group           boolean NOT NULL DEFAULT false
);

CREATE TABLE erp.item (                     -- ERPNext: Item
  item_code               text PRIMARY KEY,
  item_name               text NOT NULL,
  item_group              text REFERENCES erp.item_group,
  stock_uom               text NOT NULL,
  is_stock_item           boolean NOT NULL DEFAULT true,
  disabled                boolean NOT NULL DEFAULT false,
  allow_alternative_item  boolean NOT NULL DEFAULT true,
  safety_stock            numeric(14,3) NOT NULL DEFAULT 0,
  min_order_qty           numeric(14,3) NOT NULL DEFAULT 0,
  lead_time_days          int,
  brand                   text,
  description             text
);

CREATE TABLE erp.item_manufacturer (        -- ERPNext: Item Manufacturer
  item_code             text NOT NULL REFERENCES erp.item,
  manufacturer          text NOT NULL,
  manufacturer_part_no  text NOT NULL,
  is_default            boolean NOT NULL DEFAULT false,
  PRIMARY KEY (item_code, manufacturer, manufacturer_part_no)
);

CREATE TABLE erp.item_alternative (         -- ERPNext: Item Alternative
  item_code              text NOT NULL REFERENCES erp.item,
  alternative_item_code  text NOT NULL REFERENCES erp.item,
  two_way                boolean NOT NULL DEFAULT false,
  PRIMARY KEY (item_code, alternative_item_code),
  CHECK (item_code <> alternative_item_code)
);

CREATE TABLE erp.item_reorder (             -- ERPNext: Item Reorder
  item_code                text NOT NULL REFERENCES erp.item,
  warehouse                text NOT NULL REFERENCES erp.warehouse,
  warehouse_reorder_level  numeric(14,3),
  warehouse_reorder_qty    numeric(14,3),
  material_request_type    text NOT NULL CHECK (material_request_type IN ('Purchase', 'Material Transfer', 'Material Issue', 'Manufacture')),
  PRIMARY KEY (item_code, warehouse)
);

CREATE TABLE erp.batch (                    -- ERPNext: Batch
  batch_id           text PRIMARY KEY,
  item               text NOT NULL REFERENCES erp.item,
  manufacturing_date date,
  expiry_date        date,
  supplier           text,
  disabled           boolean NOT NULL DEFAULT false
);

CREATE TABLE erp.stock_ledger_entry (       -- ERPNext: Stock Ledger Entry. Hanya INSERT.
  name                   bigserial PRIMARY KEY,
  item_code              text NOT NULL REFERENCES erp.item,
  warehouse              text NOT NULL REFERENCES erp.warehouse,
  batch_no               text REFERENCES erp.batch,
  posting_datetime       timestamptz NOT NULL DEFAULT now(),
  voucher_type           text NOT NULL,
  voucher_no             text NOT NULL,
  actual_qty             numeric(14,3) NOT NULL,
  qty_after_transaction  numeric(14,3) NOT NULL CHECK (qty_after_transaction >= 0),
  valuation_rate         numeric(16,4),
  is_cancelled           boolean NOT NULL DEFAULT false
);
CREATE INDEX sle_item_wh_time ON erp.stock_ledger_entry (item_code, warehouse, posting_datetime);

CREATE TABLE erp.bin (                      -- ERPNext: Bin
  item_code      text NOT NULL REFERENCES erp.item,
  warehouse      text NOT NULL REFERENCES erp.warehouse,
  actual_qty     numeric(14,3) NOT NULL DEFAULT 0,
  reserved_qty   numeric(14,3) NOT NULL DEFAULT 0,
  ordered_qty    numeric(14,3) NOT NULL DEFAULT 0,
  indented_qty   numeric(14,3) NOT NULL DEFAULT 0,
  PRIMARY KEY (item_code, warehouse),
  CHECK (actual_qty >= 0),
  CHECK (reserved_qty >= 0 AND reserved_qty <= actual_qty)
);

CREATE TABLE erp.stock_reservation_entry (  -- ERPNext: Stock Reservation Entry
  name            text PRIMARY KEY,
  item_code       text NOT NULL REFERENCES erp.item,
  warehouse       text NOT NULL REFERENCES erp.warehouse,
  reserved_qty    numeric(14,3) NOT NULL CHECK (reserved_qty > 0),
  delivered_qty   numeric(14,3) NOT NULL DEFAULT 0,
  voucher_type    text,
  voucher_no      text,
  status          text NOT NULL DEFAULT 'Reserved'
                  CHECK (status IN ('Draft', 'Partially Reserved', 'Reserved', 'Partially Delivered', 'Delivered', 'Cancelled'))
);

CREATE TABLE erp.material_request (         -- ERPNext: Material Request
  name                   text PRIMARY KEY,
  material_request_type  text NOT NULL CHECK (material_request_type IN ('Purchase', 'Material Transfer', 'Material Issue', 'Manufacture', 'Customer Provided')),
  status                 text NOT NULL DEFAULT 'Draft'
                         CHECK (status IN ('Draft', 'Submitted', 'Stopped', 'Cancelled', 'Pending', 'Partially Ordered', 'Partially Received', 'Ordered', 'Issued', 'Transferred', 'Received')),
  transaction_date       date NOT NULL,
  schedule_date          date,
  set_from_warehouse     text REFERENCES erp.warehouse,
  set_warehouse          text REFERENCES erp.warehouse,
  transfer_status        text CHECK (transfer_status IN ('Not Started', 'In Transit', 'Completed'))
);

CREATE TABLE erp.material_request_item (    -- ERPNext: Material Request Item
  name            bigserial PRIMARY KEY,
  parent          text NOT NULL REFERENCES erp.material_request,
  item_code       text NOT NULL REFERENCES erp.item,
  qty             numeric(14,3) NOT NULL CHECK (qty > 0),
  uom             text NOT NULL,
  warehouse       text REFERENCES erp.warehouse,
  from_warehouse  text REFERENCES erp.warehouse,
  schedule_date   date NOT NULL
);

CREATE TABLE erp.stock_entry (              -- ERPNext: Stock Entry
  name                  text PRIMARY KEY,
  purpose               text NOT NULL CHECK (purpose IN ('Material Issue', 'Material Receipt', 'Material Transfer')),
  from_warehouse        text REFERENCES erp.warehouse,
  to_warehouse          text REFERENCES erp.warehouse,
  add_to_transit        boolean NOT NULL DEFAULT false,
  outgoing_stock_entry  text REFERENCES erp.stock_entry,
  posting_date          date NOT NULL
);

CREATE TABLE erp.stock_entry_detail (       -- ERPNext: Stock Entry Detail
  name         bigserial PRIMARY KEY,
  parent       text NOT NULL REFERENCES erp.stock_entry,
  item_code    text NOT NULL REFERENCES erp.item,
  qty          numeric(14,3) NOT NULL CHECK (qty > 0),
  s_warehouse  text REFERENCES erp.warehouse,
  t_warehouse  text REFERENCES erp.warehouse,
  batch_no     text REFERENCES erp.batch
);

CREATE TABLE erp.supplier (                 -- ERPNext: Supplier
  name              text PRIMARY KEY,
  supplier_name     text NOT NULL,
  supplier_group    text,
  supplier_type     text NOT NULL DEFAULT 'Company' CHECK (supplier_type IN ('Company', 'Individual', 'Partnership')),
  disabled          boolean NOT NULL DEFAULT false,
  on_hold           boolean NOT NULL DEFAULT false,
  prevent_rfqs      boolean NOT NULL DEFAULT false,
  prevent_pos       boolean NOT NULL DEFAULT false,
  default_currency  char(3)
);

CREATE TABLE erp.item_price (               -- ERPNext: Item Price
  name             bigserial PRIMARY KEY,
  item_code        text NOT NULL REFERENCES erp.item,
  price_list       text NOT NULL DEFAULT 'Standard Buying',
  supplier         text REFERENCES erp.supplier,
  buying           boolean NOT NULL DEFAULT true,
  currency         char(3),
  price_list_rate  numeric(16,2) NOT NULL,
  valid_from       date,
  valid_upto       date,
  lead_time_days   int,
  uom              text
);

CREATE TABLE erp.request_for_quotation (    -- ERPNext: Request for Quotation
  name                  text PRIMARY KEY,
  transaction_date      date NOT NULL,
  status                text NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
  message_for_supplier  text,
  schedule_date         date
);

CREATE TABLE erp.request_for_quotation_item (      -- ERPNext: Request for Quotation Item
  name              bigserial PRIMARY KEY,
  parent            text NOT NULL REFERENCES erp.request_for_quotation,
  item_code         text NOT NULL REFERENCES erp.item,
  qty               numeric(14,3) NOT NULL CHECK (qty > 0),
  schedule_date     date NOT NULL,
  uom               text NOT NULL,
  warehouse         text REFERENCES erp.warehouse,
  material_request  text REFERENCES erp.material_request
);

CREATE TABLE erp.request_for_quotation_supplier (  -- ERPNext: Request for Quotation Supplier
  name          bigserial PRIMARY KEY,
  parent        text NOT NULL REFERENCES erp.request_for_quotation,
  supplier      text NOT NULL REFERENCES erp.supplier,
  quote_status  text NOT NULL DEFAULT 'Pending' CHECK (quote_status IN ('Pending', 'Received')),
  send_email    boolean NOT NULL DEFAULT true,
  email_sent    boolean NOT NULL DEFAULT false,
  email_id      text,
  UNIQUE (parent, supplier)
);

CREATE TABLE erp.supplier_quotation (       -- ERPNext: Supplier Quotation
  name              text PRIMARY KEY,
  supplier          text NOT NULL REFERENCES erp.supplier,
  transaction_date  date NOT NULL,
  valid_till        date,
  status            text NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft', 'Submitted', 'Stopped', 'Cancelled', 'Expired')),
  currency          char(3) NOT NULL,
  grand_total       numeric(16,2)
);

CREATE TABLE erp.supplier_quotation_item (  -- ERPNext: Supplier Quotation Item
  name                   bigserial PRIMARY KEY,
  parent                 text NOT NULL REFERENCES erp.supplier_quotation,
  item_code              text NOT NULL REFERENCES erp.item,
  qty                    numeric(14,3) NOT NULL,
  rate                   numeric(16,2) NOT NULL,
  lead_time_days         int,
  request_for_quotation  text REFERENCES erp.request_for_quotation
);

CREATE TABLE erp.purchase_order (           -- ERPNext: Purchase Order
  name              text PRIMARY KEY,
  supplier          text NOT NULL REFERENCES erp.supplier,
  transaction_date  date NOT NULL,
  schedule_date     date,
  currency          char(3) NOT NULL,
  grand_total       numeric(16,2) NOT NULL DEFAULT 0,
  status            text NOT NULL DEFAULT 'Draft'
                    CHECK (status IN ('Draft', 'On Hold', 'To Receive and Bill', 'To Bill', 'To Receive', 'Completed', 'Cancelled', 'Closed', 'Delivered')),
  per_received      numeric(5,2) NOT NULL DEFAULT 0
);

CREATE TABLE erp.purchase_order_item (      -- ERPNext: Purchase Order Item
  name                bigserial PRIMARY KEY,
  parent              text NOT NULL REFERENCES erp.purchase_order,
  item_code           text NOT NULL REFERENCES erp.item,
  qty                 numeric(14,3) NOT NULL CHECK (qty > 0),
  rate                numeric(16,2) NOT NULL,
  schedule_date       date,
  received_qty        numeric(14,3) NOT NULL DEFAULT 0 CHECK (received_qty >= 0),
  material_request    text REFERENCES erp.material_request,
  supplier_quotation  text REFERENCES erp.supplier_quotation,
  warehouse           text REFERENCES erp.warehouse
);

CREATE TABLE erp.location (                 -- ERPNext: Location
  name             text PRIMARY KEY,
  parent_location  text REFERENCES erp.location,
  is_group         boolean NOT NULL DEFAULT false,
  latitude         numeric(9,6),
  longitude        numeric(9,6)
);

CREATE TABLE erp.asset (                    -- ERPNext: Asset
  name           text PRIMARY KEY,
  asset_name     text NOT NULL,
  asset_category text,
  location       text REFERENCES erp.location,
  company        text NOT NULL REFERENCES erp.company,
  status         text NOT NULL DEFAULT 'Submitted'
                 CHECK (status IN ('Draft', 'Submitted', 'Cancelled', 'Partially Depreciated', 'Fully Depreciated', 'Sold', 'Scrapped', 'In Maintenance', 'Out of Order', 'Issue', 'Receipt', 'Capitalized', 'Work In Progress'))
);

CREATE TABLE erp.asset_repair (             -- ERPNext: Asset Repair
  name             text PRIMARY KEY,
  asset            text NOT NULL REFERENCES erp.asset,
  failure_date     timestamptz NOT NULL,
  completion_date  timestamptz,
  repair_status    text NOT NULL DEFAULT 'Pending' CHECK (repair_status IN ('Pending', 'Completed', 'Cancelled')),
  description      text,
  CHECK (completion_date IS NULL OR completion_date >= failure_date)
);

CREATE TABLE erp.asset_repair_consumed_item (  -- ERPNext: Asset Repair Consumed Item
  name               bigserial PRIMARY KEY,
  parent             text NOT NULL REFERENCES erp.asset_repair,
  item_code          text NOT NULL REFERENCES erp.item,
  warehouse          text NOT NULL REFERENCES erp.warehouse,
  consumed_quantity  numeric(14,3) NOT NULL,
  valuation_rate     numeric(16,4)
);

-- =====================================================================
-- LAPIS PARTPILOT (ekstensi)
-- =====================================================================
-- ----- gudang, katalog lokal, dan pemetaan kanonik -----
CREATE TABLE pp.source_catalog (            -- [PartPilot] satu baris per database gudang
  catalog_id       serial PRIMARY KEY,
  code             text NOT NULL UNIQUE,
  name             text NOT NULL,
  site_warehouse   text NOT NULL REFERENCES erp.warehouse,
  code_prefix      text,                    -- awalan agar kode lokal unik di lapis ERP
  shares_master    boolean NOT NULL DEFAULT false,   -- true: kode yang sama dengan master Midea dianggap barang yang sama
  naming_profile   text,
  is_real          boolean NOT NULL DEFAULT false
);

CREATE TABLE pp.warehouse_ext (
  warehouse      text PRIMARY KEY REFERENCES erp.warehouse,
  catalog_id     int REFERENCES pp.source_catalog,
  source_name    text                       -- nama rak asli sebelum dirapikan
);

CREATE TABLE pp.item_source (               -- bagaimana tiap katalog gudang menulis item ini
  item_code      text NOT NULL REFERENCES erp.item,
  catalog_id     int NOT NULL REFERENCES pp.source_catalog,
  source_code    text NOT NULL,
  source_name    text,
  source_model   text,
  source_brand   text,
  source_uom     text,
  PRIMARY KEY (item_code, catalog_id)
);

CREATE TABLE pp.canonical_item (            -- catatan induk (golden record)
  canonical_id       serial PRIMARY KEY,
  canonical_name     text NOT NULL,
  leading_item_code  text REFERENCES erp.item,
  status             text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'merged'))
);

CREATE TABLE pp.item_canonical_map (        -- crosswalk item lokal -> catatan induk
  item_code              text PRIMARY KEY REFERENCES erp.item,
  canonical_id           int NOT NULL REFERENCES pp.canonical_item,
  proposed_canonical_id  int REFERENCES pp.canonical_item,
  score                  numeric(4,3) CHECK (score BETWEEN 0 AND 1),
  method                 text,
  status                 text NOT NULL DEFAULT 'singleton' CHECK (status IN ('singleton', 'proposed', 'confirmed', 'rejected')),
  evidence               jsonb,
  decided_by             text,
  decided_at             timestamptz
);

CREATE TABLE pp.item_ext (
  item_code      text PRIMARY KEY REFERENCES erp.item,
  model          text,                      -- Midea: Item Model
  brand_raw      text,                      -- Midea: Brand apa adanya
  abc_class      char(1) CHECK (abc_class IN ('A', 'B', 'C')),
  ved_class      char(1) CHECK (ved_class IN ('V', 'E', 'D')),
  default_buyer  text,
  provenance     text NOT NULL DEFAULT 'real' CHECK (provenance IN ('real', 'derived', 'synthetic'))
);

CREATE TABLE pp.item_alias (
  alias_id         serial PRIMARY KEY,
  item_code        text NOT NULL REFERENCES erp.item,
  alias_text       text NOT NULL,
  alias_type       text NOT NULL CHECK (alias_type IN ('local', 'abbr', 'typo', 'oem', 'equivalent', 'free_text')),
  catalog_id       int REFERENCES pp.source_catalog,
  provenance       text NOT NULL CHECK (provenance IN ('real', 'derived', 'synthetic')),
  is_test_holdout  boolean NOT NULL DEFAULT false,
  UNIQUE (item_code, alias_text)
);

CREATE TABLE pp.batch_ext (                 -- atribut batch dari Midea yang tidak ada di Batch ERPNext
  batch_id             text PRIMARY KEY REFERENCES erp.batch,
  auto_scrap           boolean NOT NULL DEFAULT false,
  owner_dept           text,
  receiving_dept       text,
  source_location_raw  text,
  currency             char(3),
  unit_price           numeric(16,4),
  received_at          date
);

CREATE TABLE pp.stock_count (
  count_id      serial PRIMARY KEY,
  item_code     text NOT NULL REFERENCES erp.item,
  warehouse     text NOT NULL REFERENCES erp.warehouse,
  system_qty    numeric(14,3) NOT NULL,
  counted_qty   numeric(14,3) NOT NULL,
  counted_at    timestamptz NOT NULL,
  counted_by    text
);

CREATE TABLE pp.staff (
  staff_id      serial PRIMARY KEY,
  display_name  text NOT NULL,
  role          text NOT NULL CHECK (role IN ('buyer', 'planner', 'technician', 'supervisor', 'manager'))
);

-- ----- aset dan work order -----
CREATE TABLE pp.asset_ext (
  asset                   text PRIMARY KEY REFERENCES erp.asset,
  site_warehouse          text NOT NULL REFERENCES erp.warehouse,
  parent_asset            text REFERENCES erp.asset,
  criticality             char(1) NOT NULL CHECK (criticality IN ('V', 'E', 'D')),
  downtime_cost_per_hour  numeric(16,2) NOT NULL DEFAULT 0,
  expected_mtbf_hours     int
);

CREATE TABLE pp.asset_bom (                 -- hubungan peralatan ke barang, pada tingkat kanonik
  asset          text NOT NULL REFERENCES erp.asset,
  canonical_id   int NOT NULL REFERENCES pp.canonical_item,
  qty_installed  numeric(10,3) NOT NULL DEFAULT 1,
  PRIMARY KEY (asset, canonical_id)
);

CREATE TABLE pp.work_order_ext (
  work_order        text PRIMARY KEY REFERENCES erp.asset_repair,
  maintenance_type  text NOT NULL CHECK (maintenance_type IN ('corrective', 'preventive')),
  priority          smallint NOT NULL DEFAULT 2 CHECK (priority BETWEEN 0 AND 3),
  status            text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'waiting_part', 'in_progress', 'done', 'cancelled')),
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE pp.wo_part_request (
  wo_part_id         serial PRIMARY KEY,
  work_order         text NOT NULL REFERENCES erp.asset_repair,
  requested_text     text NOT NULL,
  canonical_id       int REFERENCES pp.canonical_item,
  matched_item_code  text REFERENCES erp.item,
  qty_needed         numeric(14,3) NOT NULL DEFAULT 1,
  match_score        numeric(4,3) CHECK (match_score BETWEEN 0 AND 1),
  match_status       text NOT NULL DEFAULT 'pending' CHECK (match_status IN ('pending', 'matched', 'needs_confirmation', 'confirmed', 'rejected')),
  consumed_qty       numeric(14,3) NOT NULL DEFAULT 0
);

CREATE TABLE pp.reservation_ext (
  reservation    text PRIMARY KEY REFERENCES erp.stock_reservation_entry,
  wo_part_id     int NOT NULL REFERENCES pp.wo_part_request,
  priority_rank  int NOT NULL DEFAULT 0
);

CREATE TABLE pp.transfer_lane (             -- rute antar gudang (grup gudang)
  from_site     text NOT NULL REFERENCES erp.warehouse,
  to_site       text NOT NULL REFERENCES erp.warehouse,
  mode          text NOT NULL,
  freight_cost  numeric(16,2) NOT NULL CHECK (freight_cost >= 0),
  eta_hours     numeric(8,2) NOT NULL CHECK (eta_hours > 0),
  currency      char(3) NOT NULL DEFAULT 'CNY',
  PRIMARY KEY (from_site, to_site, mode),
  CHECK (from_site <> to_site)
);

CREATE TABLE pp.transfer_ext (
  material_request     text PRIMARY KEY REFERENCES erp.material_request,
  canonical_id         int REFERENCES pp.canonical_item,
  from_item_code       text NOT NULL REFERENCES erp.item,
  to_item_code         text NOT NULL REFERENCES erp.item,
  qty                  numeric(14,3) NOT NULL,
  work_order           text REFERENCES erp.asset_repair,
  issue_stock_entry    text REFERENCES erp.stock_entry,
  receipt_stock_entry  text REFERENCES erp.stock_entry
);

-- ----- vendor -----
CREATE TABLE pp.vendor_ext (                -- Midea: Supplier Code, Delivery Cycle (Days), Buyer
  supplier             text PRIMARY KEY REFERENCES erp.supplier,
  supplier_code        text UNIQUE,
  approval_status      text NOT NULL DEFAULT 'pending' CHECK (approval_status IN ('approved', 'pending', 'blocked')),
  tkdn_pct             numeric(5,2) CHECK (tkdn_pct BETWEEN 0 AND 100),
  rating               numeric(3,2),
  delivery_cycle_days  int,
  default_buyer        text
);

CREATE TABLE pp.vendor_contact (
  contact_id          serial PRIMARY KEY,
  supplier            text NOT NULL REFERENCES erp.supplier,
  contact_name        text,
  channel             text NOT NULL CHECK (channel IN ('whatsapp', 'email')),
  address             text NOT NULL,
  language            text NOT NULL DEFAULT 'id',
  opt_in_status       text NOT NULL DEFAULT 'unknown' CHECK (opt_in_status IN ('opted_in', 'unknown', 'opted_out')),
  opt_in_at           timestamptz,
  window_open_until   timestamptz,           -- jendela layanan 24 jam WhatsApp
  is_primary          boolean NOT NULL DEFAULT false
);

CREATE TABLE pp.vendor_price_ext (
  item_price    bigint PRIMARY KEY REFERENCES erp.item_price,
  min_qty       numeric(14,3) NOT NULL DEFAULT 1,
  shipping_cost numeric(16,2) NOT NULL DEFAULT 0
);

CREATE TABLE pp.quotation_ext (
  supplier_quotation  text PRIMARY KEY REFERENCES erp.supplier_quotation,
  raw_reply           text,
  received_at         timestamptz
);

CREATE TABLE pp.rfq_requirement (           -- data apa yang wajib didapat dari tiap vendor
  rfq        text NOT NULL REFERENCES erp.request_for_quotation,
  field_code text NOT NULL CHECK (field_code IN ('price', 'lead_time_days', 'moq', 'availability_qty', 'valid_until', 'shipping_cost', 'payment_terms')),
  required   boolean NOT NULL DEFAULT true,
  PRIMARY KEY (rfq, field_code)
);

CREATE TABLE pp.vendor_message (
  message_id      serial PRIMARY KEY,
  contact_id      int NOT NULL REFERENCES pp.vendor_contact,
  rfq             text REFERENCES erp.request_for_quotation,
  purchase_order  text REFERENCES erp.purchase_order,
  direction       text NOT NULL CHECK (direction IN ('out', 'in')),
  channel         text NOT NULL CHECK (channel IN ('whatsapp', 'email')),
  kind            text NOT NULL CHECK (kind IN ('template', 'free_form', 'document')),
  template_name   text,
  body            text,
  sent_at         timestamptz NOT NULL DEFAULT now(),
  in_reply_to     int REFERENCES pp.vendor_message,
  attachment_ref  text,
  injection_flag  boolean NOT NULL DEFAULT false,
  extracted       jsonb
);

CREATE TABLE pp.vendor_fact (               -- status tiap data yang ditanyakan ke vendor
  fact_id           serial PRIMARY KEY,
  rfq               text NOT NULL REFERENCES erp.request_for_quotation,
  supplier          text NOT NULL REFERENCES erp.supplier,
  field_code        text NOT NULL,
  value_text        text,
  value_num         numeric,
  status            text NOT NULL DEFAULT 'unknown' CHECK (status IN ('unknown', 'asked', 'answered', 'stale', 'conflicting')),
  source_message_id int REFERENCES pp.vendor_message,
  confidence        numeric(4,3),
  asked_count       int NOT NULL DEFAULT 0,
  last_asked_at     timestamptz,
  answered_at       timestamptz,
  next_followup_at  timestamptz,
  UNIQUE (rfq, supplier, field_code)
);

CREATE TABLE pp.po_ext (
  purchase_order     text PRIMARY KEY REFERENCES erp.purchase_order,
  created_by_type    text NOT NULL CHECK (created_by_type IN ('agent', 'human')),
  emailed_at         timestamptz,
  email_message_id   int REFERENCES pp.vendor_message
);

-- ----- kebijakan, keputusan, jejak agen -----
CREATE TABLE pp.approval_policy (
  level                 int PRIMARY KEY,
  min_value             numeric(16,2) NOT NULL,
  max_value             numeric(16,2),
  approver_role         text NOT NULL,
  min_quotes            int NOT NULL DEFAULT 1,
  max_negotiation_pct   numeric(5,2) NOT NULL DEFAULT 0
);

CREATE TABLE pp.approval_request (
  approval_id  serial PRIMARY KEY,
  doc_type     text NOT NULL CHECK (doc_type IN ('Material Request', 'Purchase Order', 'Item Mapping')),
  doc_name     text NOT NULL,
  level        int REFERENCES pp.approval_policy,
  status       text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  decided_by   text,
  decided_at   timestamptz,
  note         text
);

CREATE TABLE pp.decision_record (
  decision_id        serial PRIMARY KEY,
  wo_part_id         int NOT NULL REFERENCES pp.wo_part_request,
  decided_at         timestamptz NOT NULL DEFAULT now(),
  chosen             text NOT NULL CHECK (chosen IN ('transfer', 'buy', 'mixed', 'escalate')),
  options            jsonb NOT NULL,
  inputs_snapshot    jsonb NOT NULL,
  reason             text NOT NULL,
  requires_approval  boolean NOT NULL DEFAULT true,
  model_version      text
);

CREATE TABLE pp.agent_run (
  run_id       serial PRIMARY KEY,
  work_order   text NOT NULL REFERENCES erp.asset_repair,
  trigger      text NOT NULL,
  status       text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'waiting_human', 'done', 'failed', 'stopped')),
  started_at   timestamptz NOT NULL DEFAULT now(),
  ended_at     timestamptz
);

CREATE TABLE pp.agent_step (
  step_id     bigserial PRIMARY KEY,
  run_id      int NOT NULL REFERENCES pp.agent_run,
  seq         int NOT NULL,
  agent_name  text NOT NULL,
  tool_name   text,
  input       jsonb,
  output      jsonb,
  reason      text,
  score       numeric(4,3),
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, seq)
);

CREATE TABLE pp.eval_case (
  eval_id   serial PRIMARY KEY,
  kind      text NOT NULL CHECK (kind IN ('matching', 'crosswalk', 'route', 'injection', 'duplicate')),
  input     jsonb NOT NULL,
  expected  jsonb NOT NULL,
  split     text NOT NULL CHECK (split IN ('train', 'dev', 'test'))
);

CREATE TABLE pp.report_setting (
  key    text PRIMARY KEY,
  value  text NOT NULL
);

-- =====================================================================
-- ATURAN DI DATABASE
-- =====================================================================
-- Pesan vendor: aturan WhatsApp (opt-in, jendela 24 jam, template) dan PO hanya boleh dikirim setelah disetujui
CREATE FUNCTION pp.check_vendor_message() RETURNS trigger AS $$
DECLARE c pp.vendor_contact%ROWTYPE; po_status text;
BEGIN
  SELECT * INTO c FROM pp.vendor_contact WHERE contact_id = NEW.contact_id;
  IF NEW.channel = 'whatsapp' AND c.channel <> 'whatsapp' THEN
    RAISE EXCEPTION 'Kontak % bukan kontak WhatsApp', NEW.contact_id;
  END IF;
  IF NEW.direction = 'out' AND NEW.channel = 'whatsapp' THEN
    IF c.opt_in_status <> 'opted_in' THEN
      RAISE EXCEPTION 'Vendor belum opt-in WhatsApp: pesan keluar ditolak';
    END IF;
    IF NEW.kind = 'free_form' AND (c.window_open_until IS NULL OR c.window_open_until < NEW.sent_at) THEN
      RAISE EXCEPTION 'Jendela layanan 24 jam sudah tutup: pesan WhatsApp bebas ditolak, gunakan template';
    END IF;
    IF NEW.kind = 'template' AND NEW.template_name IS NULL THEN
      RAISE EXCEPTION 'Pesan template WhatsApp wajib menyebut nama template';
    END IF;
  END IF;
  IF NEW.direction = 'in' AND NEW.channel = 'whatsapp' THEN
    UPDATE pp.vendor_contact SET window_open_until = NEW.sent_at + interval '24 hours' WHERE contact_id = NEW.contact_id;
  END IF;
  IF NEW.purchase_order IS NOT NULL AND NEW.direction = 'out' THEN
    SELECT status INTO po_status FROM erp.purchase_order WHERE name = NEW.purchase_order;
    IF po_status IS NULL OR po_status IN ('Draft', 'Cancelled', 'On Hold') THEN
      RAISE EXCEPTION 'PO % belum disetujui: dokumen PO tidak boleh dikirim ke vendor', NEW.purchase_order;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER vendor_message_rules BEFORE INSERT ON pp.vendor_message
  FOR EACH ROW EXECUTE FUNCTION pp.check_vendor_message();

-- PO tidak bisa keluar dari Draft tanpa persetujuan manusia yang tercatat
CREATE FUNCTION pp.guard_po_status() RETURNS trigger AS $$
BEGIN
  IF NEW.status NOT IN ('Draft', 'Cancelled', 'On Hold') AND OLD.status IS DISTINCT FROM NEW.status THEN
    IF NOT EXISTS (SELECT 1 FROM pp.approval_request
                    WHERE doc_type = 'Purchase Order' AND doc_name = NEW.name AND status = 'approved' AND decided_by IS NOT NULL) THEN
      RAISE EXCEPTION 'PO % tidak bisa melewati Draft tanpa persetujuan yang tercatat', NEW.name;
    END IF;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER po_status_guard BEFORE UPDATE OF status ON erp.purchase_order
  FOR EACH ROW EXECUTE FUNCTION pp.guard_po_status();
