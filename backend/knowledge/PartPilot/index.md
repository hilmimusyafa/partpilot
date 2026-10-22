# PartPilot — Pengetahuan penamaan bearing

Dokumentasi ini hanya menyimpan sistematika penamaan per kategori dan gudang, bukan inventory, katalog per barang, atau tabel pemetaan identitas.

- [Manifest pengetahuan per gudang](catalog-notes/manifest.md)

## Lingkup dan sumber

Lingkup sintetis: satu perusahaan (`SYN-COMPANY-01`), kategori exact `Bearing`, dan lima gudang placeholder (`SYN-WH-01` sampai `SYN-WH-05`). Label Gudang 1–5 bukan nama gudang operasional atau denah pabrik. Aturan Gudang 1 berasal dari user; aturan Gudang 2 berasal dari simulasi user. Gudang 3–5 memakai aturan lokal fixture demo lima gudang yang diminta user. Seluruhnya belum diverifikasi terhadap katalog pabrikan. Nama tampilan dan alamat dummy disimpan di database.

Database adalah sumber record inventory, katalog ukuran per barang, stok, lokasi, dan pemetaan identitas. Nama serta label aktual harus diambil dari database atau label existing yang eksplisit, bukan dibuat dari contoh di dokumentasi ini. Kesamaan nama atau dimensi tidak membuktikan kompatibilitas teknik.

## Batas penggunaan

Pilih pengetahuan berdasarkan company yang sah, kategori, dan gudang. Pencarian lintas lima gudang yang diminta dan diotorisasi boleh dilakukan secara sengaja, satu query scoped per langkah dengan note lokal masing-masing. Tidak ada fuzzy matching, broad scan, atau fallback global. Ketidakpastian harus diklarifikasi, bukan diisi dengan aturan gudang lain.

Runtime memuat satu note kategori/gudang melalui allowlist dan menyimpan hash snapshot untuk provenance. Scope yang tidak terdaftar tetap knowledge_unavailable. Dokumentasi bukan bukti otorisasi akses, stok aktual, atau verifikasi pabrikan.
