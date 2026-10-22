---
company: SYN-COMPANY-01
warehouse: SYN-WH-03
category: Bearing
naming_status: demo_fixture
synthetic_scope_placeholder: true
simulated: true
source_status: USER-REQUESTED DEMO FIXTURE; SIMULATED; MANUFACTURER-UNVERIFIED
---

# Bearing — Gudang 3 (simulasi)

[Manifest](../manifest.md) · [Indeks](../../index.md)

## Scope dan sumber

Hanya untuk tuple sintetis `(SYN-COMPANY-01, Bearing, SYN-WH-03)`. Aturan ini mendukung fixture demo lima gudang yang diminta user, bukan verifikasi pabrikan atau nama gudang operasional. Nama tampilan dan alamat dummy tersimpan di database.

## Format nama lokal

`BEARING KONVEYOR [d]X[D]X[B] SEGEL KONTAK G3`

`G3-LHR-*` adalah pola kode stok lokal, bukan manufacturer MPN. SEGEL KONTAK menyatakan penutup kontak dalam fixture demo ini; teks tersebut tidak menetapkan merek atau suffix.

Dimensi bila tercantum berurutan diameter dalam, diameter luar, dan lebar dalam mm. Grammar bukan daftar ukuran atau barang yang tersedia. Identitas merek, base dan suffix harus dibaca dari label eksplisit pada record database/metadata, tidak diturunkan dari ukuran, kemiripan nama, penutup, atau kode stok.

## Retrieval dan batas implementasi

Runtime memuat note ini melalui allowlist kategori dan gudang. Query tetap dibatasi company sah, kategori exact `Bearing`, dan gudang exact `SYN-WH-03`; note bukan otorisasi akses. Pencarian lintas gudang memakai note masing-masing, tanpa fallback global atau pemindahan aturan antargudang.

Pertahankan nama lokal exact dan suffix lengkap. LLU, ZZ, LLB, dan LLF tidak disetarakan. Kesamaan dimensi tidak membuktikan kompatibilitas atau interchangeability teknik. Nol record pada scope adalah miss, banyak kandidat tetap ambigu, dan stok nol tidak menghapus identitas.

Seluruh record, ukuran per barang, stok, lokasi, dan pemetaan label berada di database. Migrasi fixture demo menambahkan record beserta label eksplisit; note ini tidak menyalin inventory. Scope di luar allowlist atau metadata yang tidak jelas tetap memerlukan pemeriksaan.
