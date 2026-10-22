# Catatan Ambiguitas dan Ketidakselarasan Antar-Dokumen Kontrak Database

Dokumen ini mendokumentasikan temuan ambiguitas, perbedaan spesifikasi, atau ketidakjelasan teknis antar-dokumen perancangan (`kontrak-db.md`, `matriks-penerimaan.md`, `kontrak-aturan-nomenklatur.md`, dan `ADR-001-stack-dan-batas.md`). Sesuai aturan penulisan tes penerimaan, pengujian tidak boleh menebak implementasi, melainkan mendokumentasikan ambiguitas secara transparan dengan kutipan baris dan membatasi pengujian pada aspek kontrak yang definitif.

---

## 1. Mekanisme Pemicu Invalidasi Persetujuan pada Perubahan Material (Uji 09)

### Kutipan Sumber Kontrak
- `kontrak-db.md` Bagian 3.3 (baris 91-97):
  ```sql
  ALTER TABLE pp.approval_request
      ADD COLUMN IF NOT EXISTS doc_hash text,
      ADD COLUMN IF NOT EXISTS policy_version text,
      ADD COLUMN IF NOT EXISTS approval_mode text NOT NULL DEFAULT 'manual' 
          CHECK (approval_mode IN ('manual', 'policy_auto')),
      ADD COLUMN IF NOT EXISTS invalidation_reason text;
  ```
- `kontrak-db.md` Bagian 5.7 (baris 382-384):
  ```text
  - Invariant:
    - Memanggil pp.assert_approved('Material Request', p_material_request).
  ```
- `matriks-penerimaan.md` Uji 09 (baris 175-181):
  ```text
  When: Kuantitas yang dibutuhkan pada baris WO diubah dari 1 unit menjadi 2 unit.
  Then:
    - Hash dokumen berubah (doc_hash mismatch).
    - Status tiket persetujuan lama otomatis dibatalkan / dinonaktifkan (invalidation_reason = 'MATERIAL_CHANGE_DETECTED').
    - Pemanggilan pp.tool_execute_transfer menolak eksekusi mutasi sampai persetujuan baru disahkan.
  ```

### Analisis Ambiguitas
`kontrak-db.md` mendefinisikan kolom `invalidation_reason` pada tabel `pp.approval_request` dan menyatakan bahwa `pp.tool_execute_transfer` memanggil `pp.assert_approved`. Namun, kontrak tidak merinci:
1. Apakah invalidasi terjadi via database trigger pada tabel sumber (misal `erp.material_request_item` atau `pp.wo_part_request`), atau
2. Apakah invalidasi dieksekusi secara eksplisit oleh fungsi tersimpan saat terjadi modifikasi data, atau
3. Apakah `pp.assert_approved` membandingkan ulang hash dokumen terkini terhadap `doc_hash` yang tersimpan pada baris persetujuan.

### Keputusan Batas Tes
Pengujian pada `test_approval_invalidation.py` memverifikasi bahwa:
- Kolom `invalidation_reason` ada pada tabel `pp.approval_request`.
- Saat sebuah persetujuan berstatus tidak valid atau memiliki `invalidation_reason`, pemanggilan `pp.assert_approved` dan `pp.tool_execute_transfer` menolak eksekusi mutasi fisik.

---

## 2. Keberadaan Fungsi Impor Aturan Nomenklatur `pp.import_nomenclature_rule`

### Kutipan Sumber Kontrak
- `kontrak-aturan-nomenklatur.md` Tahap 4 (baris 63-65):
  ```text
  Aturan diimpor ke PostgreSQL menggunakan fungsi tersimpan:
  pp.import_nomenclature_rule(p_org_id, p_family_code, p_version_tag, p_rule_yaml, p_approved_by).
  ```
- `kontrak-db.md` Bagian 5 (Fungsi Tersimpan, baris 256-423):
  Daftar fungsi yang didefinisikan secara resmi hanya mencakup:
  - `pp.tool_start_run`
  - `pp.tool_apply_part_match`
  - `pp.tool_propose_mapping`
  - `pp.tool_record_clarification_turn`
  - `pp.tool_reserve_stock`
  - `pp.tool_plan_transfer`
  - `pp.tool_execute_transfer`
  - `pp.policy_auto_approve`
  - `pp.decide_approval`
  Fungsi `pp.import_nomenclature_rule` tidak dicantumkan dalam spesifikasi DDL fungsi di `kontrak-db.md`.

### Analisis Ambiguitas
Terdapat perbedaan antara dokumen arsitektur database (`kontrak-db.md`) dan dokumen tata kelola aturan (`kontrak-aturan-nomenklatur.md`). Tidak ada rincian tipe pengembalian, perlakuan parsing YAML di dalam PostgreSQL, atau hak akses role untuk fungsi `pp.import_nomenclature_rule`.

### Keputusan Batas Tes
Pengujian pada `test_schema_delta.py` dan `test_nomenclature_validation.py` menguji langsung struktur tabel relasional hasil penguraian aturan (`pp.nomenclature_rule_version`, `pp.nomenclature_rule_pattern`, dan `pp.nomenclature_rule_attribute`) serta penegakan status draft tanpa bergantung pada fungsi impor yang belum dispesifikasikan DDL-nya di `kontrak-db.md`.

---

## 3. Penegakan Larangan Aktivasi Aturan Nomenklatur Tanpa Pengesahan Sah

### Kutipan Sumber Kontrak
- `kontrak-db.md` Invariant 10 (baris 463-464):
  ```text
  Tabel pp.nomenclature_rule_version default berstatus 'draft' dengan approved_by dan approved_at bernilai NULL.
  Pengaktifan versi aturan ke status 'active' memerlukan pengesahan nyata oleh Operator / Product Owner (Rifqi).
  Dilarang memasukkan klaim persetujuan fiktif atau otomatis pada aturan nomenklatur.
  ```
- `kontrak-db.md` Bagian 3.4 DDL (baris 109-114):
  ```sql
  status text NOT NULL DEFAULT 'draft'
      CHECK (status IN ('draft', 'verified', 'active', 'deprecated')),
  raw_definition_yaml text NOT NULL,
  approved_by text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  ```

### Analisis Ambiguitas
DDL pada Bagian 3.4 hanya mencakup CHECK nilai status, namun belum menyertakan constraint relasional seperti:
`CHECK (status <> 'active' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL))`
atau BEFORE UPDATE trigger yang mencegah pengaktifan langsung.

### Keputusan Batas Tes
Pengujian pada `test_nomenclature_validation.py` (`test_a_db_27_draft_nomenclature_rule_cannot_be_activated_without_approval`) memverifikasi bahwa upaya mengubah status menjadi `'active'` saat `approved_by` dan `approved_at` bernilai NULL ditolak oleh database.

---

## 4. Mekanisme Pengecekan Mode Demo pada `pp.policy_auto_approve`

### Kutipan Sumber Kontrak
- `ADR-001-stack-dan-batas.md` Bagian 2.7 (baris 83):
  ```text
  Auto-approve HANYA aktif apabila konfigurasi lingkungan mengaktifkan DEMO_AUTO_APPROVE_MODE=true pada data sintetis.
  ```
- `kontrak-db.md` Bagian 5.8 (baris 392-399):
  ```sql
  CREATE OR REPLACE FUNCTION pp.policy_auto_approve(
      p_org_id uuid,
      p_approval_id int,
      p_policy_version text,
      p_expected_doc_hash text
  ) RETURNS jsonb
  ```

### Analisis Ambiguitas
Fungsi `pp.policy_auto_approve` tidak menerima parameter penanda mode demo secara eksplisit (`is_demo_mode`). Kontrak tidak merinci apakah pemeriksaan mode demo dilakukan melalui konfigurasi sesi PostgreSQL (`current_setting('app.demo_auto_approve_mode', true)`), tabel parameter sistem, atau pemeriksaan lingkungan runtime.

### Keputusan Batas Tes
Pengujian pada `test_policy_auto_approve.py` memverifikasi penolakan persetujuan otomatis saat mode demo tidak aktif, dan memvalidasi keabsahan jejak audit saat evaluasi kebijakan disetujui.

---

## 5. Implementasi Transaksional Audit Durable di PostgreSQL

### Kutipan Sumber Kontrak
- `kontrak-db.md` Bagian 4.1 (baris 244-253):
  ```text
  Untuk menjamin Audit Attempt Tetap Ada Saat Operasi Ditolak (Acceptance Test 11):
  1. Pola Transaksi Aplikasi (Pre-logging Pattern):
     Backend FastAPI menjalankan pencatatan attempt ke tabel pp.tool_execution_attempt dalam koneksi/transaksi terpisah (autocommit=True) tepat sebelum mengeksekusi operasi bisnis.
  2. Pola Database Return-Status (Safe Execution Functions):
     Seluruh fungsi pp.tool_* dirancang tidak memicu uncaught fatal rollback untuk penolakan bisnis (business rejection), melainkan mengembalikan structured JSON:
     {"success": false, "code": "REJECTED_CONSTRAINT", "message": "...", "attempt_id": 1234}.
  ```
- `matriks-penerimaan.md` Uji 11 (baris 211-216):
  ```text
  When: Worker mencoba memanggil operasi transfer ilegal yang melanggar invariant database.
  Then: Transaksi bisnis transfer ditolak. Baris catatan pemanggilan di tabel pp.tool_execution_attempt TETAP ADA dengan status = 'rejected_policy'.
  ```

### Analisis Ambiguitas
PostgreSQL standar tidak memiliki fitur `AUTONOMOUS TRANSACTION` bawaan di dalam blok transaksi PL/pgSQL yang sama (kecuali menggunakan ekstensi eksternal seperti `dblink`). Oleh karena itu, ketahanan audit membutuhkan penanganan transaksi pada lapis pemanggil (koneksi audit independen atau fungsi pembungkus dengan penanganan eksepsi internal).

### Keputusan Batas Tes
Pengujian pada `test_audit_durability.py` memverifikasi integritas alur ini dengan menjalankan pencatatan pre-logging pada koneksi audit terpisah, mengeksekusi transaksi bisnis yang memicu penolakan invariant, lalu membuktikan bahwa baris log attempt tetap bertahan di database dengan status `rejected_policy`.
