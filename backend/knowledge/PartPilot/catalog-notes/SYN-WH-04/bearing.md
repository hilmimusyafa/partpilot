---
company: SYN-COMPANY-01
warehouse: SYN-WH-04
category: Bearing
naming_status: unknown
synthetic_scope_placeholder: true
---

# Bearing — Gudang 4 (unknown)

[Manifest](../manifest.md) · [Indeks](../../index.md)

Scope sintetis: `(SYN-COMPANY-01, Bearing, SYN-WH-04)`. Gudang 4 adalah placeholder, bukan nama gudang operasional atau denah pabrik.

Penamaan lokal, nama/kode barang, dimensi, suffix, alias, dan pemetaan identitas tetap `unknown`. Belum ada pengetahuan penamaan dari user untuk gudang ini. Tidak ada aturan lokal atau pemetaan produk yang ditetapkan; status unknown bukan pernyataan tentang stok atau keberadaan record.

Untuk kategori dan gudang ini, pilih hanya note ini melalui manifest. Klarifikasi scope serta nama/kode lokal yang pasti sebelum lookup yang bergantung pada aturan yang belum diketahui. Jangan menerapkan aturan gudang lain, mengarang padanan, atau memakai fallback global/fuzzy/embedding. Kemiripan nama atau dimensi tidak membuktikan identitas.

Pencarian lintas lima gudang yang diminta dan diotorisasi tetap boleh menelusuri scope lain yang sah, satu query scoped per langkah dengan note lokal masing-masing; ketidakpastian scope ini tidak mengizinkan pemindahan aturan atau scope diam-diam.

Database tetap sumber record, katalog ukuran, stok, lokasi, dan pemetaan per barang. Note ini bukan inventory. Pembaca catatan oleh runtime belum diimplementasikan.
