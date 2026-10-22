---
company: SYN-COMPANY-01
warehouse: SYN-WH-02
category: Bearing
naming_status: user_provided
synthetic_scope_placeholder: true
simulated: true
source_status: USER-PROVIDED SIMULATION; MANUFACTURER-UNVERIFIED
---

# Bearing — Gudang 2

[Manifest](../manifest.md) · [Indeks](../../index.md)

## Scope dan sumber

Hanya untuk tuple sintetis `(SYN-COMPANY-01, Bearing, SYN-WH-02)`. Gudang 2 adalah placeholder, bukan nama operasional. Aturan berasal dari simulasi user dan belum diverifikasi pabrikan. Ini pengetahuan sistematika, bukan inventory, tabel lookup, atau pemetaan identitas per record; tidak ada persetujuan teknik.

## Format nama lokal

`LAHER ALUR [d]X[D]X[B] [penutup]`

Semua dimensi dalam mm, berurutan diameter dalam `d`, diameter luar `D`, dan lebar `B`. Pertahankan nama exact pada sumber, termasuk huruf kapital, spasi, dan `X`; jangan menambahkan unit atau mengubah label aktual secara otomatis. Grammar ini bukan daftar ukuran barang yang tersedia.

| Istilah lokal | Makna yang diberikan user |
|---|---|
| LAHER ALUR | Deep-groove ball bearing |
| KARET RAPAT DUA SISI | Contact seals di kedua sisi |
| PLAT DUA SISI | Metal shields di kedua sisi |
| KARET NONKONTAK DUA SISI | Noncontact seals di kedua sisi |

`G2-BRG-*` adalah pola kode stok lokal, bukan manufacturer MPN dan bukan daftar record. Nama lokal tidak mencantumkan merek. Nama dan label aktual harus diambil dari database atau label existing yang eksplisit, bukan dibuat dari grammar ini. Merek, base, dan suffix tidak boleh ditebak dari dimensi, nama lokal, atau istilah penutup. Istilah noncontact generik tidak membedakan LLB dari LLF; suffix eksplisit wajib tersedia. LLB tidak setara dengan LLF.

## Retrieval dan batas implementasi

Gunakan hanya company yang sah, kategori exact `Bearing`, dan gudang exact `SYN-WH-02`. Note bukan otorisasi akses. Cari nama atau kode lokal exact dengan sumber metadata eksplisit; jangan stripping suffix, mengubah ejaan diam-diam, atau menggunakan fuzzy/vector/embedding matching.

Pencarian lintas lima gudang yang diminta dan diotorisasi boleh menelusuri satu query scoped per langkah dengan note lokal masing-masing. Jangan memindahkan aturan Gudang 2, broad scan catatan, atau fallback global.

Identitas dan pemetaan per barang harus bersumber dari database/label existing yang eksplisit. Kesamaan dimensi tidak membuktikan identitas, substitusi, kompatibilitas, atau interchangeability teknik. Ketidakpastian scope/nama/kode/label/metadata memerlukan klarifikasi. Nol hasil exact berarti miss pada scope itu; banyak hasil berarti ambigu, bukan izin memilih hasil pertama. Stok nol tidak menghapus identitas record.

Seluruh record, katalog ukuran, stok, lokasi, dan pemetaan per barang tetap di database; tidak disalin ke note ini. Penamaan Gudang 3–5 tetap unknown. Pembaca catatan oleh runtime belum diimplementasikan.
