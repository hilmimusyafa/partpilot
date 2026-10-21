# PartPilot — Pengetahuan penamaan bearing

Dokumentasi ini hanya menyimpan sistematika penamaan per kategori dan gudang, bukan inventory, katalog per barang, atau tabel pemetaan identitas.

- [Manifest pengetahuan per gudang](catalog-notes/manifest.md)

## Lingkup dan sumber

Lingkup sintetis: satu perusahaan (`SYN-COMPANY-01`), kategori exact `Bearing`, dan lima gudang placeholder (`SYN-WH-01` sampai `SYN-WH-05`). Label Gudang 1–5 bukan nama gudang operasional atau denah pabrik. Aturan Gudang 1 berasal dari user; aturan Gudang 2 berasal dari simulasi user. Keduanya belum diverifikasi terhadap katalog pabrikan. Penamaan Gudang 3–5 tetap `unknown`.

Database adalah sumber record inventory, katalog ukuran per barang, stok, lokasi, dan pemetaan identitas. Nama serta label aktual harus diambil dari database atau label existing yang eksplisit, bukan dibuat dari contoh di dokumentasi ini. Kesamaan nama atau dimensi tidak membuktikan kompatibilitas teknik.

## Batas penggunaan

Pilih pengetahuan berdasarkan company yang sah, kategori, dan gudang. Pencarian lintas lima gudang yang diminta dan diotorisasi boleh dilakukan secara sengaja, satu query scoped per langkah dengan note lokal masing-masing. Tidak ada fuzzy matching, broad scan, atau fallback global. Ketidakpastian harus diklarifikasi, bukan diisi dengan aturan gudang lain.

Ini adalah snapshot ekspor dokumentasi yang terpisah; tidak ada jaminan sinkronisasi otomatis dengan catatan sumber. Pembaca catatan oleh runtime belum diimplementasikan. Dokumentasi bukan bukti perilaku backend, otorisasi akses, atau kesiapan rilis.
