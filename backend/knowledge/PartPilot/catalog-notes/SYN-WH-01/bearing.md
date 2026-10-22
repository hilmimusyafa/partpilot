---
company: SYN-COMPANY-01
warehouse: SYN-WH-01
category: Bearing
naming_status: user_provided
synthetic_scope_placeholder: true
source_status: USER-PROVIDED; MANUFACTURER-UNVERIFIED
---

# Bearing — Gudang 1

[Manifest](../manifest.md) · [Indeks](../../index.md)

## Scope dan sumber

Hanya untuk tuple sintetis `(SYN-COMPANY-01, Bearing, SYN-WH-01)`. Gudang 1 adalah placeholder, bukan nama operasional. Pengetahuan diberikan user, belum diverifikasi terhadap katalog pabrikan. Ini sistematika penamaan, bukan daftar barang atau katalog dimensi per item.

## Grammar NTN

Pemisahan konseptual: `NTN | seri | bore | suffix`.

Satu contoh sintaks ilustratif: `NTN 6200LLU` → `NTN | 62 | 00 | LLU`. Contoh ini bukan bukti keberadaan record atau ketersediaan stok.

- `NTN`: merek dalam grammar ini.
- `seri`: bagian seri; pada contoh, `62`.
- `bore`: kode diameter dalam; `00` berarti `d = 10 mm`, `01` berarti `d = 12 mm`. Jangan mengekstrapolasi kode yang belum diberikan.
- `suffix`: bagian identitas nama lengkap, tidak boleh dihapus atau disetarakan diam-diam.
- Urutan dimensi adalah `d × D × B` dalam mm: diameter dalam, diameter luar, dan lebar. Spesifikasi record termasuk `d` harus ditopang database/katalog atau label existing yang eksplisit. Nilai `D` dan `B` harus berasal dari katalog, bukan ditebak dari seri/bore; katalog ukuran per item tetap di database.

## Semantik suffix yang diberikan user

| Suffix | Penjelasan pada kedua sisi |
|---|---|
| ZZ | Pelindung logam (metal shield) |
| LLB | Seal noncontact |
| LLF | Seal noncontact; tetap berbeda dari LLB |
| LLH | Seal low-torque |
| LLU | Seal contact |

Penjelasan ini tidak digeneralisasi ke semua produk/merek. LLB tidak setara dengan LLF. Kesamaan bore atau dimensi tidak membuktikan identitas, substitusi, kompatibilitas, atau interchangeability teknik.

## Retrieval dan batas implementasi

Gunakan note ini hanya untuk company, kategori, dan gudang di atas. Untuk pencarian lintas gudang yang diminta dan diotorisasi, lakukan satu query scoped per langkah dengan note lokal masing-masing; jangan memindahkan aturan ini ke gudang lain. Pertahankan nama lengkap, case, spasi, dan suffix; tidak ada fuzzy matching atau fallback global.

Identitas dan pemetaan per barang serta merek/base/suffix bersumber dari database atau label existing yang eksplisit. Metadata tidak pasti memerlukan klarifikasi. Nol hasil exact berarti miss; banyak hasil berarti ambigu. Record, stok, lokasi, dan katalog ukuran tetap di database, bukan di note ini.

Runtime memilih note ini melalui allowlist SYN-WH-01/Bearing dan menyimpan hash snapshot sebagai provenance.
