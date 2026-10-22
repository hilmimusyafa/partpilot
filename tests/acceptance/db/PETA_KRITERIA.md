# Pemetaan Kriteria Tes Penerimaan Lapisan Database (A-DB-01 s.d. A-DB-37)

Dokumen ini memetakan seluruh kriteria pengujian lapisan database pada folder `tests/acceptance/db/` terhadap dokumen rujukan arsitektur (`kontrak-db.md`, `matriks-penerimaan.md`, `kontrak-aturan-nomenklatur.md`).

---

## 1. Ringkasan Pemetaan Matriks Uji

| Kriteria ID | Berkas Pengujian | Fungsi Pengujian | Target Objek Database | Pemetaan Matriks Uji |
| :--- | :--- | :--- | :--- | :--- |
| **A-DB-01** | `test_schema_delta.py` | `test_a_db_01_organization_table` | `pp.organization` | Delta Skema Bagian 3.1 |
| **A-DB-02** | `test_schema_delta.py` | `test_a_db_02_site_table` | `pp.site` | Delta Skema Bagian 3.1 |
| **A-DB-03** | `test_schema_delta.py` | `test_a_db_03_warehouse_ext_delta` | `pp.warehouse_ext` | Delta Skema Bagian 3.1 |
| **A-DB-04** | `test_schema_delta.py` | `test_a_db_04_org_site_warehouse_hierarchy` | FK Hierarchy | Delta Skema Bagian 2.1 |
| **A-DB-05** | `test_schema_delta.py` | `test_a_db_05_pp_tables_org_id_columns` | Kolom `org_id` pada 14 tabel `pp.*` | Delta Skema Bagian 3.2 |
| **A-DB-06** | `test_schema_delta.py` | `test_a_db_06_approval_request_delta_columns` | `pp.approval_request` | Delta Skema Bagian 3.3 |
| **A-DB-07** | `test_schema_delta.py` | `test_a_db_07_nomenclature_rule_version_table` | `pp.nomenclature_rule_version` | Delta Skema Bagian 3.4 & Invariant 10 |
| **A-DB-08** | `test_schema_delta.py` | `test_a_db_08_nomenclature_rule_pattern_and_attribute_tables` | `pp.nomenclature_rule_pattern`, `pp.nomenclature_rule_attribute` | Delta Skema Bagian 3.4 |
| **A-DB-09** | `test_schema_delta.py` | `test_a_db_09_clarification_session_and_turn_tables` | `pp.clarification_session`, `pp.clarification_turn` | Delta Skema Bagian 3.5 & Uji 06 |
| **A-DB-10** | `test_schema_delta.py` | `test_a_db_10_procurement_handoff_and_quote_tables` | `pp.procurement_handoff`, `pp.procurement_quote_stub` | Delta Skema Bagian 3.6 |
| **A-DB-11** | `test_schema_delta.py` | `test_a_db_11_tool_execution_attempt_table_and_indexes` | `pp.tool_execution_attempt` | Delta Skema Bagian 3.7 |
| **A-DB-12** | `test_stock_reservation_race.py` | `test_a_db_12_concurrent_stock_reservation_race_condition` | `pp.tool_reserve_stock`, `erp.bin` | **Uji 08** (Reservasi Konkuren) |
| **A-DB-13** | `test_approval_invalidation.py` | `test_a_db_13_material_change_invalidates_approval` | `pp.approval_request.invalidation_reason` | **Uji 09** (Invalidasi Material) |
| **A-DB-14** | `test_approval_invalidation.py` | `test_a_db_14_execute_transfer_gated_by_valid_approval` | `pp.assert_approved`, `pp.tool_execute_transfer` | **Uji 09** (Gating Mutasi Stok) |
| **A-DB-15** | `test_role_isolation.py` | `test_a_db_15_agent_role_cannot_modify_erp_tables` | Penolakan DML `erp.*` spesifik tabel | **Uji 10** (Isolasi Peran pp_agent) |
| **A-DB-16** | `test_role_isolation.py` | `test_a_db_16_agent_role_cannot_modify_pp_tables` | Penolakan DML `pp.*` spesifik tabel | **Uji 10** (Isolasi Peran pp_agent) |
| **A-DB-17** | `test_role_isolation.py` | `test_a_db_17_agent_role_cannot_execute_decide_approval` | Penolakan eksekusi `pp.decide_approval` | **Uji 10** (Isolasi Peran pp_agent) |
| **A-DB-18** | `test_role_isolation.py` | `test_a_db_18_agent_role_cannot_access_secrets_or_ddl` | Penolakan DDL & manipulasi skema/tabel | **Uji 10** (Isolasi Peran pp_agent) |
| **A-DB-19** | `test_role_isolation.py` | `test_a_db_19_console_role_can_execute_decide_approval` | Otorisasi konsol pada `pp.decide_approval` | **Uji 10** (Otorisasi Konsol) |
| **A-DB-20** | `test_role_isolation.py` | `test_a_db_20_worker_role_has_restricted_permissions` | Penolakan mutasi keputusan/ERP pp_worker | **Uji 10** (Otorisasi Terbatas Worker) |
| **A-DB-21** | `test_audit_durability.py` | `test_a_db_21_rejected_attempt_recorded_despite_rollback` | `pp.tool_execution_attempt` | **Uji 11** (Audit Anti-Rollback) |
| **A-DB-22** | `test_nomenclature_validation.py` | `test_a_db_22_valid_complete_model_matched` | `pp.tool_apply_part_match` | **Uji 01** (Ekstraksi Kode Valid) |
| **A-DB-23** | `test_nomenclature_validation.py` | `test_a_db_23_negative_capacity_73_without_oil_seal_rejected` | `pp.tool_apply_part_match` | **Uji 13** (Invarian Seal Kapasitas 73) |
| **A-DB-24** | `test_nomenclature_validation.py` | `test_a_db_24_negative_capacity_73_d_cut_shaft_rejected` | `pp.tool_apply_part_match` | **Uji 14** (Invarian Poros D Kapasitas 73) |
| **A-DB-25** | `test_nomenclature_validation.py` | `test_a_db_25_negative_capacity_13_keyway_shaft_rejected` | `pp.tool_apply_part_match` | **Uji 15** (Invarian Poros Pasak K Kapasitas 13) |
| **A-DB-26** | `test_nomenclature_validation.py` | `test_a_db_26_special_suffix_s100_identity_preserved` | `pp.canonical_item`, `pp.tool_propose_mapping` | **Uji 05 & Uji 16** (Preservasi Suffix -S100) |
| **A-DB-27** | `test_nomenclature_validation.py` | `test_a_db_27_draft_nomenclature_rule_cannot_be_activated_without_approval` | `pp.nomenclature_rule_version` | Invariant 10 Tata Kelola Aturan |
| **A-DB-28** | `test_policy_auto_approve.py` | `test_a_db_28_policy_auto_approve_requires_demo_mode` | `pp.policy_auto_approve` | Syarat Mode Demo ADR-001 |
| **A-DB-29** | `test_policy_auto_approve.py` | `test_a_db_29_policy_auto_approve_records_policy_audit_trail` | `pp.policy_auto_approve` | Jejak Audit Keputusan Kebijakan |
| **A-DB-30** | `test_policy_auto_approve.py` | `test_a_db_30_policy_auto_approve_rejects_conflict_and_unverified_suffix` | `pp.policy_auto_approve` | Penolakan Suffix & Ambang Batas |
| **A-DB-31** | `test_policy_auto_approve.py` | `test_a_db_31_policy_auto_approve_rejects_hash_mismatch` | `pp.policy_auto_approve` | Penolakan Hash Tidak Cocok |
| **A-DB-32** | `test_decide_approval.py` | `test_a_db_32_decide_approval_requires_valid_personnel_name` | `pp.decide_approval` | Kewajiban Nama Personel Sah |
| **A-DB-33** | `test_decide_approval.py` | `test_a_db_33_decide_approval_validates_decision_status` | `pp.decide_approval` | Validasi Status approved/rejected |
| **A-DB-34** | `test_decide_approval.py` | `test_a_db_34_decide_approval_rejects_second_decision` | `pp.decide_approval` | Penolakan Putusan Ganda (Idempotensi) |
| **A-DB-35** | `test_decide_approval.py` | `test_a_db_35_decide_approval_emits_vault_event` | `pp.decide_approval`, `pp.vault_event` | Emisi Peristiwa Audit Vault |
| **A-DB-36** | `test_role_isolation.py` | `test_a_db_36_agent_role_can_execute_contract_tools_with_audit` | Eksekusi Alat (`pp.tool_*`) & Audit `pp_agent` | **Uji 10** (Kontrol Positif pp_agent) |
| **A-DB-37** | `test_role_isolation.py` | `test_a_db_37_worker_role_can_write_outbox_handoff_path` | Hak Tulis Outbox (`pp.vendor_message`) & Handoff (`pp.procurement_handoff`) | **Uji 10** (Kontrol Positif pp_worker) |

---

## 2. Rincian Kriteria Pengujian

### A-DB-01 s.d. A-DB-11: Delta Skema Fondasi DDL
Memastikan seluruh tabel baru dan penambahan kolom pada lapis `pp` terbentuk sesuai kontrak arsitektur Bagian 3:
- Tabel master `pp.organization` dan `pp.site`.
- Hubungan hierarki referensial Organisasi -> Site -> Gudang.
- Keberadaan kolom `org_id` bertipe UUID NOT NULL dengan nilai default pada 14 tabel domain `pp.*`.
- Penambahan kolom ikatan hash dokumen dan versi kebijakan pada `pp.approval_request`.
- Tabel versi aturan nomenklatur beserta pola dan atributnya berstatus bawaan `draft`.
- Tabel sesi klarifikasi dengan batasan maksimal 3 putaran dan kunci idempotensi putaran unik.
- Tabel handoff pengadaan dan stub penawaran vendor dengan batasan kuantitas positif.
- Tabel audit log percobaan eksekusi durable `pp.tool_execution_attempt` beserta indeks performanya.

### A-DB-12: Pencegahan Over-Reservation Konkuren (Uji 08)
Dua koneksi paralel mengeksekusi `pp.tool_reserve_stock` secara bersamaan pada saldo sisa 1 unit. Sistem membuktikan bahwa mekanisme penguncian atomik (`SELECT ... FOR UPDATE`) memastikan tepat satu koneksi berhasil, satu koneksi ditolak dengan kode `INSUFFICIENT_STOCK`, dan batas `reserved_qty <= actual_qty` pada `erp.bin` tidak pernah terlanggar.

### A-DB-13 s.d. A-DB-14: Invalidasi Persetujuan Akibat Perubahan Material (Uji 09)
Perubahan material pada kuantitas atau spesifikasi dokumen membatalkan status persetujuan sebelumnya (`invalidation_reason = 'MATERIAL_CHANGE_DETECTED'`). Pemanggilan fungsi pembuktian persetujuan (`pp.assert_approved`) dan eksekusi mutasi transfer fisik (`pp.tool_execute_transfer`) menolak eksekusi jika status persetujuan tidak lagi valid.

### A-DB-15 s.d. A-DB-20: Penolakan Pelanggaran Keamanan Peran Database (Uji 10 - Kontrol Negatif Diperketat)
Penegakan matriks hak akses RBAC PostgreSQL dengan penegasan pada level objek target (bukan sekadar penolakan skema global):
- Peran `pp_agent` ditolak melakukan `INSERT`, `UPDATE`, `DELETE` langsung pada tabel `erp.*` (`erp.stock_entry`, `erp.purchase_order`, `erp.bin`). Penolakan ditegaskan spesifik pada tabel, bukan pesan error skema.
- Peran `pp_agent` ditolak melakukan modifikasi langsung pada tabel `pp.*` (`pp.approval_policy`, `pp.work_order_ext`). Penolakan ditegaskan spesifik pada tabel.
- Peran `pp_agent` ditolak mengeksekusi fungsi persetujuan manusia `pp.decide_approval`. Penolakan ditegaskan spesifik pada objek fungsi.
- Peran `pp_agent` ditolak menjalankan perintah DDL (`CREATE TABLE`, `ALTER TABLE`) atau memanipulasi struktur database.
- Peran `pp_console` diizinkan mengeksekusi `pp.decide_approval`.
- Peran `pp_worker` ditolak mengeksekusi `pp.decide_approval`, ditolak DML pada `erp.stock_entry`, serta ditolak menulis langsung ke tabel keputusan (`pp.approval_request`, `pp.decision_record`).

### A-DB-21: Ketahanan Jejak Audit Percobaan (Uji 11)
Operasi yang ditolak oleh aturan kebijakan atau pelanggaran invarian database tetap meninggalkan baris log pada `pp.tool_execution_attempt` dengan status `rejected_policy` atau `failed_exception`, meskipun transaksi bisnis dibatalkan atau di-rollback.

### A-DB-22 s.d. A-DB-27: Validasi Nomenklatur dan Invarian Fisik (Uji 01, 05, 13, 14, 15, 16)
Pemeriksaan keabsahan fisik kode suku cadang pada level database:
- Pengenalan kode lengkap valid `HG-KN73BJ-S100` dengan kode item sintetis (`SYN-HGKN-0001`), skor >= 0.90, dan status `matched`.
- Penolakan kode model kapasitas 73 tanpa oil seal 'J' (`HG-KN73` / `HG-KN73B`) karena secara fisik tidak diproduksi.
- Penolakan kode model kapasitas 73 dengan poros potong D (`HG-KN73BD`) karena poros D hanya untuk kapasitas 13.
- Penolakan kode model kapasitas 13 dengan poros alur pasak (`HG-KN13K`) karena alur pasak dilarang untuk kapasitas 13.
- Preservasi varian khusus berakhiran `-S100` sebagai identitas kanonik mandiri yang tidak dilebur ke model polos tanpa suffix.
- Penegakan tata kelola aturan: aturan berstatus `draft` dilarang dialihkan ke status `active` tanpa pengesahan nyata oleh personel berwenang.

### A-DB-28 s.d. A-DB-31: Mesin Persetujuan Kebijakan Otomatis (Policy Engine)
Pengecekan batas persetujuan otomatis deterministik:
- Hanya dapat berjalan saat mode demo diaktifkan.
- Keputusan dicatat atas nama kebijakan (`policy:<versi>`), bukan meniru nama manusia.
- Menolak pemetaan yang memiliki konflik spesifikasi, skor di bawah 0.90, atau varian dengan suffix yang belum terverifikasi.
- Menolak eksekusi apabila hash dokumen tidak cocok dengan hash yang diajukan.

### A-DB-32 s.d. A-DB-35: Konsol Keputusan Manusia (pp.decide_approval)
Pemeriksaan integritas fungsi keputusan manusia:
- Mewajibkan nama personel yang sah (tidak boleh kosong, spasi, atau memuat teks otomatis/mesin).
- Membatasi status keputusan hanya pada `approved` atau `rejected`.
- Menolak keputusan kedua pada permintaan yang telah diputuskan sebelumnya.
- Menerbitkan baris rekaman audit peristiwa ke tabel `pp.vault_event`.

### A-DB-36 s.d. A-DB-37: Kontrol Positif Hak Akses Peran Database (Uji 10 - Kontrol Positif Baru)
Pemeriksaan hak eksekusi dan penulisan jalur resmi yang wajib dipenuhi oleh migrasi 008:
- **A-DB-36**: Peran `pp_agent` berhak mengeksekusi fungsi alat baca/tulis kontrak (`pp.tool_start_run` dan `pp.tool_apply_part_match`) dan memiliki izin menulis rekaman audit percobaan ke tabel `pp.tool_execution_attempt`.
- **A-DB-37**: Peran `pp_worker` berhak menulis ke jalur outbox pesan vendor (`pp.vendor_message`) dan jalur handoff pengadaan (`pp.procurement_handoff`) sesuai matriks `kontrak-db.md` Bagian 6, untuk memastikan pekerja latar belakang dapat menjalankan fungsi integrasi tanpa memerlukan hak modifikasi pada tabel keputusan.
