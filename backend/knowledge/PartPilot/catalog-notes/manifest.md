# PartPilot — Manifest pengetahuan per gudang

[Kembali ke indeks](../index.md)

Manifest ini hanya indeks pengetahuan penamaan, bukan inventory atau pemetaan produk. Company sintetis: `SYN-COMPANY-01`; kategori exact: `Bearing`. Semua ID gudang adalah placeholder sintetis.

| Label placeholder | Warehouse exact sintetis | Kategori | Catatan lokal | Status penamaan |
|---|---|---|---|---|
| Gudang 1 | SYN-WH-01 | Bearing | [Bearing — Gudang 1](SYN-WH-01/bearing.md) | user_provided; grammar NTN, bore, suffix |
| Gudang 2 | SYN-WH-02 | Bearing | [Bearing — Gudang 2](SYN-WH-02/bearing.md) | user_provided; simulasi grammar LAHER ALUR |
| Gudang 3 | SYN-WH-03 | Bearing | [Bearing — Gudang 3](SYN-WH-03/bearing.md) | demo_fixture; grammar BEARING KONVEYOR |
| Gudang 4 | SYN-WH-04 | Bearing | [Bearing — Gudang 4](SYN-WH-04/bearing.md) | demo_fixture; grammar LAHER MOTOR |
| Gudang 5 | SYN-WH-05 | Bearing | [Bearing — Gudang 5](SYN-WH-05/bearing.md) | demo_fixture; grammar BANTALAN |

## Kontrak retrieval yang dituju

1. Pastikan company yang sah, kategori exact, dan gudang dari konteks yang diotorisasi. Note tidak memberikan izin akses.
2. Pilih tepat satu note kategori + gudang untuk setiap query scoped. Pencarian lintas lima gudang boleh menelusuri scope yang diotorisasi satu per satu dengan note lokal masing-masing; pertahankan scope setiap hasil.
3. Scope tidak diketahui, note hilang/tidak cocok, atau penamaan unknown memerlukan klarifikasi. Jangan menerapkan aturan gudang lain atau melakukan fallback global. Ketidakpastian satu gudang tidak melarang melanjutkan scope lain yang sah dalam pencarian lintas gudang yang diminta.
4. Pertahankan nama lengkap, case, spasi, dan suffix. Tidak ada normalisasi diam-diam, stripping suffix, fuzzy/vector/embedding matching, atau broad scan catatan untuk menebak identitas.
5. Nol hasil exact adalah miss pada scope itu; banyak hasil adalah ambigu dan perlu klarifikasi. Stok nol tidak menghapus identitas record.
6. Record, katalog ukuran, stok, lokasi, dan pemetaan per barang tetap di database. Merek/base/suffix harus memiliki sumber eksplisit dari database atau label existing; jangan mengarang label dari dimensi atau istilah penutup.

Aturan Gudang 1 dan Gudang 2 berstatus user-provided dan manufacturer-unverified; Gudang 2 adalah simulasi. Gudang 3–5 memakai fixture demo sintetis yang diminta user, juga manufacturer-unverified. Runtime membaca satu note scoped melalui allowlist. Nama tampilan/alamat dummy dan seluruh record barang tetap di database; manifest ini tidak membuktikan stok atau validasi pabrikan.
