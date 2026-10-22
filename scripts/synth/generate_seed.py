#!/usr/bin/env python3
"""
Generator seed fixture sintetis deterministik untuk PartPilot.
Membaca JSON fixture:
- db/seed/catalog_hgkn.json
- db/seed/crosswalk_sites.json
- db/seed/work_orders.json

Menghasilkan file SQL seed:
- db/seed/008_seed_synth.sql

Semua query menggunakan sintaks INSERT ... ON CONFLICT DO NOTHING.
Idempoten, deterministik, tanpa koneksi jaringan dan tanpa database runtime.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SEED_DIR = REPO_ROOT / "db" / "seed"
CATALOG_PATH = SEED_DIR / "catalog_hgkn.json"
CROSSWALK_PATH = SEED_DIR / "crosswalk_sites.json"
WORK_ORDERS_PATH = SEED_DIR / "work_orders.json"
OUTPUT_SQL_PATH = SEED_DIR / "008_seed_synth.sql"


def escape_sql_string(val: str) -> str:
    if val is None:
        return "NULL"
    escaped = val.replace("'", "''")
    return f"'{escaped}'"


def format_sql_literal(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, dict):
        escaped = json.dumps(val, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'::jsonb"
    return escape_sql_string(str(val))


def extract_yaml_contract(design_path: Path) -> str:
    """Mengekstrak blok YAML kontrak aturan dari dokumen desain secara deterministik."""
    if not design_path.exists():
        return 'schema_version: "partpilot/nomenclature/v1"\nfamily_code: "MITSUBISHI_HG_KN"\n'

    with open(design_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ekstrak blok antara ```yaml dan ```
    marker_start = "```yaml"
    marker_end = "```"
    start_idx = content.find(marker_start)
    if start_idx != -1:
        start_idx += len(marker_start)
        end_idx = content.find(marker_end, start_idx)
        if end_idx != -1:
            return content[start_idx:end_idx].strip() + "\n"

    return 'schema_version: "partpilot/nomenclature/v1"\nfamily_code: "MITSUBISHI_HG_KN"\n'


def generate_seed() -> str:
    # Memuat berkas JSON masukan
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog_data = json.load(f)

    with open(CROSSWALK_PATH, "r", encoding="utf-8") as f:
        crosswalk_data = json.load(f)

    with open(WORK_ORDERS_PATH, "r", encoding="utf-8") as f:
        wo_data = json.load(f)

    org_id = crosswalk_data.get("org_id", "00000000-0000-0000-0000-000000000001")
    org_code = crosswalk_data.get("org_code", "ORG-SYNTH-01")
    org_name = crosswalk_data.get("org_name", "Midea Synthetic Industrial Corp")

    lines = []
    lines.append("-- =====================================================================")
    lines.append("-- PLACEHOLDER SINTETIS - akan diganti")
    lines.append("-- Provenance: synthetic")
    lines.append("-- Generator: scripts/synth/generate_seed.py")
    lines.append("-- Master Item: 36 Model Sah Mitsubishi HG-KN (8 S100 + 28 Non-S100)")
    lines.append("-- Lokasi: 5 Site (B1, B2, W3, W4, W5) dengan crosswalk lokal & stok awal")
    lines.append("-- Work Order: 30 Kasus Pengujian Uji 01-16 (Hasil Diharapkan Terdefinisi)")
    lines.append("-- =====================================================================")
    lines.append("")
    lines.append("SET search_path = pg_catalog, pp, erp, public;")
    lines.append("")

    # 1. Master Organisasi (Tenant Pasif)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 1. Master Organisasi (Multi-tenancy)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append(
        f"INSERT INTO pp.organization (org_id, org_code, org_name, default_currency) "
        f"VALUES ({format_sql_literal(org_id)}::uuid, {format_sql_literal(org_code)}, {format_sql_literal(org_name)}, 'CNY') "
        f"ON CONFLICT (org_id) DO NOTHING;"
    )
    lines.append("")

    # 2. Master Site (5 Lokasi Pabrik)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 2. Master Site Pabrik (5 Lokasi B1, B2, W3, W4, W5)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.site (site_id, org_id, site_name, location_desc) VALUES")
    site_values = []
    for s in crosswalk_data["sites"]:
        s_id = format_sql_literal(s["site_id"])
        s_name = format_sql_literal(s["site_name"])
        s_desc = format_sql_literal(s["location_desc"])
        site_values.append(f"  ({s_id}, {format_sql_literal(org_id)}::uuid, {s_name}, {s_desc})")
    lines.append(",\n".join(site_values))
    lines.append("ON CONFLICT (site_id) DO NOTHING;")
    lines.append("")

    # 3. Master Perusahaan ERP
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 3. Master Perusahaan ERP Simulator")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.company (name, default_currency) VALUES")
    lines.append(f"  ({format_sql_literal(org_name)}, 'CNY'),")
    lines.append("  ('Midea Indonesia', 'IDR')")
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    # 4. Pohon Gudang ERP (Stores, Transit, Receiving)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 4. Master Gudang ERP Simulator (Tiap site memiliki Stores & Transit/Receiving)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.warehouse (name, warehouse_name, parent_warehouse, is_group, company, warehouse_type) VALUES")
    group_whs = [
        "('WH-B1', 'Indonesian Assembly Branch Factory', 'All Warehouses - MID', true, 'Midea Indonesia', NULL)",
        "('WH-B2', 'Indonesian Assembly Branch Two Factory', 'All Warehouses - MID', true, 'Midea Indonesia', NULL)",
        "('WH-W3', 'Central MRO Store (sintetis)', 'All Warehouses - MID', true, 'Midea Indonesia', NULL)",
        "('WH-W4', 'Indonesian Assembly Branch Three Factory (sintetis)', 'All Warehouses - MID', true, 'Midea Indonesia', NULL)",
        "('WH-W5', 'Karawang Parts Hub (sintetis)', 'All Warehouses - MID', true, 'Midea Indonesia', NULL)",
        "('WH-TRANSIT', 'Barang dalam perjalanan (sintetis)', 'All Warehouses - MID', false, 'Midea Indonesia', 'Transit')",
    ]
    lines.append(",\n".join(f"  {w}" for w in group_whs))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO erp.warehouse (name, warehouse_name, parent_warehouse, is_group, company, warehouse_type) VALUES")
    wh_leaf_values = []
    for w in crosswalk_data["warehouses"]:
        w_name = format_sql_literal(w["name"])
        w_sub = format_sql_literal(w["warehouse_name"])
        w_par = format_sql_literal(w["parent_warehouse"])
        w_type = format_sql_literal(w["warehouse_type"])
        wh_leaf_values.append(f"  ({w_name}, {w_sub}, {w_par}, false, 'Midea Indonesia', {w_type})")
    lines.append(",\n".join(wh_leaf_values))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    # 5. Ekstensi Gudang PartPilot (pp.warehouse_ext)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 5. Ekstensi Gudang PartPilot (pp.warehouse_ext)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.warehouse_ext (warehouse, org_id, site_id, source_name) VALUES")
    wh_ext_values = []
    for w in crosswalk_data["warehouses"]:
        w_name = format_sql_literal(w["name"])
        s_id = format_sql_literal(w["site_id"])
        src_name = format_sql_literal(f"Subinventory {w['warehouse_name']} pada {w['site_id']}")
        wh_ext_values.append(f"  ({w_name}, {format_sql_literal(org_id)}::uuid, {s_id}, {src_name})")
    lines.append(",\n".join(wh_ext_values))
    lines.append("ON CONFLICT (warehouse) DO UPDATE SET org_id = EXCLUDED.org_id, site_id = EXCLUDED.site_id;")
    lines.append("")

    # 6. Katalog Sumber (pp.source_catalog)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 6. Katalog Sumber per Gudang (pp.source_catalog)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.source_catalog (code, name, site_warehouse, code_prefix, shares_master, naming_profile, is_real, org_id) VALUES")
    cat_rows = [
        "('B1', 'Branch One Assembly Plant', 'WH-B1/Stores', NULL, false, 'Kode master, huruf kapital, deskripsi Inggris campur', false)",
        "('B2', 'Branch Two Assembly Plant', 'WH-B2/Stores', NULL, false, 'Kode master, Title Case, nama resmi pabrikan', false)",
        "('W3', 'Central MRO Store', 'WH-W3/Stores', 'W3:', false, 'Kode SP-nnnnnn, deskripsi format KOMPONEN, TIPE, MODEL, huruf besar', false)",
        "('W4', 'Branch Three Assembly Plant', 'WH-W4/Stores', 'W4:', true, 'Kode internal Nnnnn, deskripsi Indonesia-Inggris huruf kecil campur', false)",
        "('W5', 'Karawang Parts Hub', 'WH-W5/Stores', 'W5:', false, 'Model sebagai kode item, format katalog vendor internasional', false)",
    ]
    lines.append(",\n".join(f"  ({r[:-1]}, {format_sql_literal(org_id)}::uuid)" for r in cat_rows))
    lines.append("ON CONFLICT (code) DO NOTHING;")
    lines.append("")

    # 7. Master Item ERP (erp.item)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 7. Master Item ERP (erp.item) - 36 Master Item & Item Lokal 5 Lokasi")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.item (item_code, item_name, item_group, stock_uom, brand, description) VALUES")
    item_rows = []
    seen_item_codes = set()

    for item in catalog_data["items"]:
        code = item["item_code"]
        name = f"AC Servo Motor {item['model']}"
        desc = f"Mitsubishi AC Servo Motor {item['model']} ({item['rated_power_kw']} kW, 3000 rpm, rem={'Ya' if item['has_electromagnetic_brake'] else 'Tidak'}, seal={'Ya' if item['has_oil_seal'] else 'Tidak'}, poros={item['shaft_shape']})"
        if code not in seen_item_codes:
            item_rows.append(
                f"  ({format_sql_literal(code)}, {format_sql_literal(name)}, 'Kelistrikan', 'Set', 'Mitsubishi Electric', {format_sql_literal(desc)})"
            )
            seen_item_codes.add(code)

    for entry in crosswalk_data["crosswalk"]:
        for site_key, mapping in entry["sites"].items():
            loc_code = mapping["local_item_code"]
            if loc_code not in seen_item_codes:
                loc_name = mapping["local_description"]
                loc_brand = mapping["local_brand"]
                item_rows.append(
                    f"  ({format_sql_literal(loc_code)}, {format_sql_literal(loc_name)}, 'Kelistrikan', 'Set', {format_sql_literal(loc_brand)}, {format_sql_literal(loc_name)})"
                )
                seen_item_codes.add(loc_code)

    lines.append(",\n".join(item_rows))
    lines.append("ON CONFLICT (item_code) DO NOTHING;")
    lines.append("")

    # 8. Catatan Induk PartPilot (pp.canonical_item)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 8. Catatan Induk Golden Record (pp.canonical_item) - 36 Model Sah HG-KN")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.canonical_item (canonical_id, canonical_name, leading_item_code, status, org_id) VALUES")
    canon_rows = []
    for item in catalog_data["items"]:
        c_id = item["canonical_id"]
        c_name = format_sql_literal(f"Mitsubishi {item['model']} AC Servo Motor")
        c_lead = format_sql_literal(item["item_code"])
        canon_rows.append(f"  ({c_id}, {c_name}, {c_lead}, 'active', {format_sql_literal(org_id)}::uuid)")
    lines.append(",\n".join(canon_rows))
    lines.append("ON CONFLICT (canonical_id) DO NOTHING;")
    lines.append("SELECT setval(pg_get_serial_sequence('pp.canonical_item', 'canonical_id'), 200, false);")
    lines.append("")

    # 9. Ekstensi Item PartPilot (pp.item_ext)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 9. Ekstensi Item PartPilot (pp.item_ext)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.item_ext (item_code, model, brand_raw, abc_class, ved_class, default_buyer, provenance, org_id) VALUES")
    item_ext_rows = []
    for item in catalog_data["items"]:
        code = format_sql_literal(item["item_code"])
        model = format_sql_literal(item["model"])
        item_ext_rows.append(
            f"  ({code}, {model}, 'Mitsubishi Electric', 'A', 'V', 'Buyer-01', 'synthetic', {format_sql_literal(org_id)}::uuid)"
        )

    for entry in crosswalk_data["crosswalk"]:
        model = format_sql_literal(entry["model"])
        for site_key, mapping in entry["sites"].items():
            loc_code = mapping["local_item_code"]
            if loc_code != entry["master_item_code"]:
                code_lit = format_sql_literal(loc_code)
                brand_lit = format_sql_literal(mapping["local_brand"])
                item_ext_rows.append(
                    f"  ({code_lit}, {model}, {brand_lit}, 'A', 'V', 'Buyer-01', 'synthetic', {format_sql_literal(org_id)}::uuid)"
                )
    lines.append(",\n".join(item_ext_rows))
    lines.append("ON CONFLICT (item_code) DO NOTHING;")
    lines.append("")

    # 10. Pemetaan Kanonik Crosswalk (pp.item_canonical_map)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 10. Crosswalk Item Lokal ke Catatan Induk (pp.item_canonical_map)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.item_canonical_map (item_code, canonical_id, score, method, status, evidence, decided_by, decided_at, org_id) VALUES")
    map_rows = []
    for entry in crosswalk_data["crosswalk"]:
        c_id = entry["canonical_id"]
        ev = format_sql_literal({"source": "synthetic_seed_fixture", "model": entry["model"]})
        m_code = format_sql_literal(entry["master_item_code"])
        map_rows.append(
            f"  ({m_code}, {c_id}, 1.000, 'exact_model', 'confirmed', {ev}, 'human_verifier', '2026-10-21T09:00:00+07:00'::timestamptz, {format_sql_literal(org_id)}::uuid)"
        )
        for site_key, mapping in entry["sites"].items():
            loc_code = mapping["local_item_code"]
            if loc_code != entry["master_item_code"]:
                l_code = format_sql_literal(loc_code)
                ev_loc = format_sql_literal({"source": "synthetic_seed_crosswalk", "site": site_key, "model": entry["model"]})
                map_rows.append(
                    f"  ({l_code}, {c_id}, 1.000, 'exact_model', 'confirmed', {ev_loc}, 'human_verifier', '2026-10-21T09:00:00+07:00'::timestamptz, {format_sql_literal(org_id)}::uuid)"
                )
    lines.append(",\n".join(map_rows))
    lines.append("ON CONFLICT (item_code) DO NOTHING;")
    lines.append("")

    # 11. Saldo Stok Awal (erp.bin)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 11. Saldo Stok Awal Gudang (erp.bin)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.bin (item_code, warehouse, actual_qty, reserved_qty) VALUES")
    bin_rows = []
    for entry in crosswalk_data["crosswalk"]:
        for site_key, mapping in entry["sites"].items():
            wh = format_sql_literal(mapping["warehouse"])
            code = format_sql_literal(mapping["local_item_code"])
            act_qty = mapping["stock_qty"]
            res_qty = mapping["reserved_qty"]
            bin_rows.append(f"  ({code}, {wh}, {act_qty}, {res_qty})")
    lines.append(",\n".join(bin_rows))
    lines.append("ON CONFLICT (item_code, warehouse) DO UPDATE SET actual_qty = EXCLUDED.actual_qty, reserved_qty = EXCLUDED.reserved_qty;")
    lines.append("")

    # 12. Batch Bertanggal (erp.batch & pp.batch_ext)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 12. Batch Bertanggal Inventori (erp.batch & pp.batch_ext)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.batch (batch_id, item, manufacturing_date, supplier) VALUES")
    batch_rows = []
    batch_ext_rows = []
    seen_batches = set()

    for entry in crosswalk_data["crosswalk"]:
        for site_key, mapping in entry["sites"].items():
            b_id = mapping["batch_number"]
            if b_id not in seen_batches:
                seen_batches.add(b_id)
                b_code = format_sql_literal(mapping["local_item_code"])
                mfg_date = format_sql_literal(mapping["batch_manufacturing_date"])
                rec_date = format_sql_literal(mapping["batch_received_date"])
                supp = format_sql_literal(mapping["supplier_code"])
                u_price = mapping["unit_price_cny"]
                b_lit = format_sql_literal(b_id)

                batch_rows.append(f"  ({b_lit}, {b_code}, {mfg_date}::date, {supp})")
                batch_ext_rows.append(
                    f"  ({b_lit}, false, 'Maintenance', 'Production Device', 'CNY', {u_price}, {rec_date}::date)"
                )

    lines.append(",\n".join(batch_rows))
    lines.append("ON CONFLICT (batch_id) DO NOTHING;")
    lines.append("")
    lines.append("INSERT INTO pp.batch_ext (batch_id, auto_scrap, owner_dept, receiving_dept, currency, unit_price, received_at) VALUES")
    lines.append(",\n".join(batch_ext_rows))
    lines.append("ON CONFLICT (batch_id) DO NOTHING;")
    lines.append("")

    # 13. Rute Antar Gudang (pp.transfer_lane)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 13. Rute Antar Pabrik (pp.transfer_lane)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO pp.transfer_lane (from_site, to_site, mode, freight_cost, eta_hours, currency, org_id) VALUES")
    lanes = [
        ("WH-B1", "WH-B2", 400.0, 3.0),
        ("WH-B1", "WH-W3", 900.0, 6.0),
        ("WH-B1", "WH-W4", 250.0, 2.0),
        ("WH-B1", "WH-W5", 1100.0, 8.0),
        ("WH-B2", "WH-W3", 800.0, 5.0),
        ("WH-B2", "WH-W4", 300.0, 2.0),
        ("WH-B2", "WH-W5", 1100.0, 8.0),
        ("WH-W3", "WH-W4", 900.0, 6.0),
        ("WH-W3", "WH-W5", 500.0, 3.0),
        ("WH-W4", "WH-W5", 1000.0, 7.0),
    ]
    lane_rows = []
    for f_site, t_site, cost, hours in lanes:
        lane_rows.append(
            f"  ('{f_site}', '{t_site}', 'truk', {cost}, {hours}, 'CNY', {format_sql_literal(org_id)}::uuid)"
        )
        lane_rows.append(
            f"  ('{t_site}', '{f_site}', 'truk', {cost}, {hours}, 'CNY', {format_sql_literal(org_id)}::uuid)"
        )
    lines.append(",\n".join(lane_rows))
    lines.append("ON CONFLICT (from_site, to_site, mode) DO NOTHING;")
    lines.append("")

    # 14. Master Lokasi & Aset (erp.location, erp.asset, pp.asset_ext)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 14. Master Lokasi & Aset Sumbu Servo (erp.location, erp.asset, pp.asset_ext)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.location (name, is_group) VALUES")
    locs = ["('LOC-B1', false)", "('LOC-B2', false)", "('LOC-W3', false)", "('LOC-W4', false)", "('LOC-W5', false)"]
    lines.append(",\n".join(f"  {l}" for l in locs))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO erp.asset (name, asset_name, asset_category, location, company, status) VALUES")
    asset_rows = []
    asset_ext_rows = []
    for wo in wo_data["work_orders"]:
        a_id = wo["asset"]
        site = wo["site_id"]
        loc = site.replace("SITE-", "LOC-")
        wh = f"WH-{site.replace('SITE-', '')}/Stores"
        a_name = f"Sumbu servo perakitan mesin {a_id} ({site})"
        asset_rows.append(
            f"  ({format_sql_literal(a_id)}, {format_sql_literal(a_name)}, 'servo', '{loc}', 'Midea Indonesia', 'Submitted')"
        )
        downtime = 60000.0 if site == "SITE-B2" else 40000.0
        asset_ext_rows.append(
            f"  ({format_sql_literal(a_id)}, '{wh}', NULL, 'V', {downtime}, 25000, {format_sql_literal(org_id)}::uuid)"
        )
    lines.append(",\n".join(asset_rows))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO pp.asset_ext (asset, site_warehouse, parent_asset, criticality, downtime_cost_per_hour, expected_mtbf_hours, org_id) VALUES")
    lines.append(",\n".join(asset_ext_rows))
    lines.append("ON CONFLICT (asset) DO NOTHING;")
    lines.append("")

    # 15. Work Order & Permintaan Part (erp.asset_repair, pp.work_order_ext, pp.wo_part_request)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 15. Skenario Work Order Sintetis (30 Kasus Pengujian Hasil Diharapkan Uji 01-16)")
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("INSERT INTO erp.asset_repair (name, asset, failure_date, repair_status, description) VALUES")
    asr_rows = []
    wo_ext_rows = []
    wo_part_rows = []

    for idx, wo in enumerate(wo_data["work_orders"], start=1):
        wo_name = format_sql_literal(wo["name"])
        asset_lit = format_sql_literal(wo["asset"])
        f_date = format_sql_literal(wo["failure_date"])
        desc_lit = format_sql_literal(wo["requested_text"])
        m_type = format_sql_literal(wo["maintenance_type"])
        prio = wo["priority"]

        asr_rows.append(f"  ({wo_name}, {asset_lit}, {f_date}::timestamptz, 'Pending', {desc_lit})")
        wo_ext_rows.append(
            f"  ({wo_name}, {m_type}, {prio}, 'waiting_part', {f_date}::timestamptz, {format_sql_literal(org_id)}::uuid)"
        )

        wo_part_id = 100 + idx
        qty = wo["qty_needed"]
        expected = wo.get("expected_result", {})
        canon_model = expected.get("expected_canonical_model")
        matched_item = expected.get("expected_item_code")
        b_status = expected.get("business_status", "pending")
        match_score = expected.get("match_score", 0.0)

        canon_id_val = "NULL"
        if canon_model:
            for cat_item in catalog_data["items"]:
                if cat_item["model"] == canon_model:
                    canon_id_val = str(cat_item["canonical_id"])
                    break

        m_item_val = format_sql_literal(matched_item) if matched_item else "NULL"
        match_status_val = format_sql_literal(b_status if b_status in ("matched", "needs_confirmation", "pending", "confirmed", "rejected") else "pending")

        wo_part_rows.append(
            f"  ({wo_part_id}, {wo_name}, {desc_lit}, {canon_id_val}, {m_item_val}, {qty}, {match_score}, {match_status_val}, 0, {format_sql_literal(org_id)}::uuid)"
        )

    lines.append(",\n".join(asr_rows))
    lines.append("ON CONFLICT (name) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO pp.work_order_ext (work_order, maintenance_type, priority, status, created_at, org_id) VALUES")
    lines.append(",\n".join(wo_ext_rows))
    lines.append("ON CONFLICT (work_order) DO NOTHING;")
    lines.append("")

    lines.append("INSERT INTO pp.wo_part_request (wo_part_id, work_order, requested_text, canonical_id, matched_item_code, qty_needed, match_score, match_status, consumed_qty, org_id) VALUES")
    lines.append(",\n".join(wo_part_rows))
    lines.append("ON CONFLICT (wo_part_id) DO NOTHING;")
    lines.append("SELECT setval(pg_get_serial_sequence('pp.wo_part_request', 'wo_part_id'), 200, false);")
    lines.append("")

    # 16. Aturan Nomenklatur Terstruktur (pp.nomenclature_rule_*)
    lines.append("-- ---------------------------------------------------------------------")
    lines.append("-- 16. Header Aturan Nomenklatur Terstruktur (Draft Status / Tata Kelola)")
    lines.append("-- ---------------------------------------------------------------------")
    raw_yaml_path = REPO_ROOT.parent.parent / "private" / "partpilot" / "design" / "kontrak-aturan-nomenklatur.md"
    raw_yaml_content = extract_yaml_contract(raw_yaml_path)

    lines.append("INSERT INTO pp.nomenclature_rule_version (rule_version_id, org_id, family_code, manufacturer, catalog_version, version_tag, status, raw_definition_yaml, approved_by, approved_at) VALUES")
    lines.append(
        f"  (1, {format_sql_literal(org_id)}::uuid, 'MITSUBISHI_HG_KN', 'Mitsubishi Electric', 'MELSERVO-JE / SH(NA)030135ENG-E', 'v1.1.0-draft', 'draft', {format_sql_literal(raw_yaml_content)}, NULL, NULL)"
    )
    lines.append("ON CONFLICT (org_id, family_code, version_tag) DO NOTHING;")
    lines.append("SELECT setval(pg_get_serial_sequence('pp.nomenclature_rule_version', 'rule_version_id'), 10, false);")
    lines.append("")

    lines.append("-- Pola Segmen Posisi Aturan Nomenklatur")
    lines.append("INSERT INTO pp.nomenclature_rule_pattern (rule_version_id, position_idx, segment_name, regex_pattern, is_mandatory, attribute_mapped, notes) VALUES")
    patterns = [
        (1, 1, "SERIES", "^HG-KN", True, "series_name", "Low inertia, small capacity rotary AC servo motor series (100W - 750W)"),
        (1, 2, "RATED_OUTPUT", "^[1247]", True, "rated_power_kw", "1=100W, 2=200W, 4=400W, 7=750W"),
        (1, 3, "RATED_SPEED", "^3", True, "rated_speed_rpm", "3=3000 rpm rated speed"),
        (1, 4, "BRAKE_OPTION", "^B?", False, "has_electromagnetic_brake", "B=With electromagnetic brake 24V DC"),
        (1, 5, "OIL_SEAL_OPTION", "^J?", False, "has_oil_seal", "J=With oil seal (Wajib untuk kapasitas 73)"),
        (1, 6, "SHAFT_SHAPE_OPTION", "^[KD]?", False, "shaft_shape", "K=Keyway (23-73), D=D-cut (13), kosong=Straight"),
        (1, 7, "SPECIAL_SUFFIX", "^(-S100)?", False, "special_specification_suffix", "Sufiks varian katalog JE. Preservasi identitas penuh tanpa interpretasi spekulatif."),
    ]
    pattern_rows = []
    for p in patterns:
        pattern_rows.append(
            f"  ({p[0]}, {p[1]}, {format_sql_literal(p[2])}, {format_sql_literal(p[3])}, {format_sql_literal(p[4])}, {format_sql_literal(p[5])}, {format_sql_literal(p[6])})"
        )
    lines.append(",\n".join(pattern_rows))
    lines.append("ON CONFLICT (rule_version_id, position_idx) DO NOTHING;")
    lines.append("")

    lines.append("-- Simbol dan Makna Atribut Terverifikasi (is_verified_in_source = false untuk -S100)")
    lines.append("INSERT INTO pp.nomenclature_rule_attribute (rule_version_id, segment_name, symbol_value, decoded_meaning, is_verified_in_source) VALUES")
    attrs = [
        (1, "RATED_OUTPUT", "1", "0.10 kW (100W rated output, Flange 40 mm)", True),
        (1, "RATED_OUTPUT", "2", "0.20 kW (200W rated output, Flange 60 mm)", True),
        (1, "RATED_OUTPUT", "4", "0.40 kW (400W rated output, Flange 60 mm)", True),
        (1, "RATED_OUTPUT", "7", "0.75 kW (750W rated output, Flange 80 mm)", True),
        (1, "RATED_SPEED", "3", "3000 rpm rated speed", True),
        (1, "BRAKE_OPTION", "", "Without electromagnetic brake (Standar)", True),
        (1, "BRAKE_OPTION", "B", "With electromagnetic brake (Rem 24V DC)", True),
        (1, "OIL_SEAL_OPTION", "", "Without oil seal (Valid hanya 13, 23, 43; dilarang 73)", True),
        (1, "OIL_SEAL_OPTION", "J", "With oil seal (Wajib untuk 73, opsional untuk 13, 23, 43)", True),
        (1, "SHAFT_SHAPE_OPTION", "", "Standard straight shaft", True),
        (1, "SHAFT_SHAPE_OPTION", "K", "Keyway shaft with 2 round end key (Hanya untuk 23, 43, 73)", True),
        (1, "SHAFT_SHAPE_OPTION", "D", "D-cut shaft (Hanya untuk 13)", True),
        (1, "SPECIAL_SUFFIX", "-S100", "Special specification suffix in MELSERVO-JE catalog. Semantic meaning unverified in primary manufacturer literature. Mandatory identity preservation.", False),
    ]
    attr_rows = []
    for a in attrs:
        attr_rows.append(
            f"  ({a[0]}, {format_sql_literal(a[1])}, {format_sql_literal(a[2])}, {format_sql_literal(a[3])}, {format_sql_literal(a[4])})"
        )
    lines.append(",\n".join(attr_rows))
    lines.append("ON CONFLICT (rule_version_id, segment_name, symbol_value) DO NOTHING;")
    lines.append("")

    sql_content = "\n".join(lines) + "\n"

    with open(OUTPUT_SQL_PATH, "w", encoding="utf-8") as f:
        f.write(sql_content)

    return sql_content


def main():
    print(f"Menghasilkan {OUTPUT_SQL_PATH} dari berkas JSON...")
    content = generate_seed()
    sha256_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    line_count = len(content.splitlines())
    byte_count = len(content.encode("utf-8"))
    print(f"Selesai: {OUTPUT_SQL_PATH}")
    print(f"Ukuran: {byte_count:,} byte, Baris: {line_count:,}")
    print(f"SHA-256: {sha256_hash}")


if __name__ == "__main__":
    main()
