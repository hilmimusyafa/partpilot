# Hasil implementasi dan pengujian PartPilot

Tanggal pengujian: **23 Oktober 2026 WIB**. [Buka PartPilot](https://partpilot.rifqisetiawan.my.id/).

## Release dan data aktif

- VPS tetap menjadi host. `current-demo` menunjuk ke `releases/main-20261023-r9`.
- API dan worker memakai image `partpilot-demo:20261023-main-r9`; bridge WhatsApp memakai image `partpilot-whatsapp:20261023-reconnect-r1`.
- Backup database dan konfigurasi dibuat sebelum migrasi, di direktori privat `private/before-evidence-20261022T205803Z` pada root PartPilot VPS. Credential tidak dimasukkan ke dokumen atau repository.
- Migration020–023 terpasang. API publik telah mengembalikan **10 record bukti**, dengan URL sumber dan SHA-256; seluruhnya `is_local_asset_history=false`.
- Provider aktif **9router** sesuai revisi pengguna. Adapter Vertex tersedia, tetapi autentikasi dan pengujian live project `hackathon-primestep-16` belum dilakukan.

## Pengujian otomatis

Pembaruan r9 menghapus input kurs di Teknisi dan Meja manajer. Endpoint perbandingan makanan otomatis memakai nilai tetap 18.000, dan menolak override nilai lain. Build, TypeScript, lint, serta 10 tes benchmark/kontrak berhasil. Tarif skenario tetap Rp59.976.000/jam; checkbox hanya mengakui bahwa biaya merupakan estimasi skenario.

Perbaikan reconnect WhatsApp **23 Oktober 2026**: sesi QR di VPS masih memiliki `creds.me.id` walaupun `creds.registered=false`. Bridge lama tidak melakukan restore/retry untuk keadaan tersebut. Pemeriksaan sesi kini menerima identitas QR yang masih ada; logout/bad session tetap mereset kredensial. Tes regresi gagal sebelum patch dan berhasil sesudahnya; **14 tes bridge lulus**. Image bridge aktif `partpilot-whatsapp:20261023-reconnect-r1` berhasil tersambung otomatis setelah restart. RFQ `PP-30aee152` terkirim ke nomor pengujian yang diizinkan; balasan pengguna diproses menjadi **quoted**, delapan field lengkap, tanpa field hilang. Perbandingan baru `6dc0958c-b106-497f-b2e5-006537fde132` memakai pemetaan 18.000 dan mencakup dua opsi lengkap; tidak ada keputusan pembelian yang dibuat oleh pengujian ini.

Pembaruan **main-20261023-r8** menetapkan pemetaan bawaan **18.000 IDR per unit dolar publikasi** pada konfigurasi backend serta tampilan Teknisi dan Meja manajer. Dengan benchmark 3.332 unit/jam, tarif skenario menjadi **Rp59.976.000/jam**. Nilai tetap dapat diubah pengguna dan tetap memerlukan pengakuan asumsi simulasi. Build 13 halaman, TypeScript, lint, serta sembilan tes kalkulator benchmark berhasil. Konfigurasi API publik mengembalikan `18000`; browser Meja keputusan juga menampilkan `18000` tanpa mengetik nilai baru. Hasil historis di bawah tetap memakai pemetaan yang digunakan saat pengujian tersebut, bukan dihitung ulang secara diam-diam.

Pembaruan navigasi **main-20261023-r7**: tab Beranda dihapus; Teknisi mengarah ke halaman utama dan tetap aktif pada `/technician/`. Tombol **Reset** kembali tersedia di kanan atas. Build 13 halaman, TypeScript, dan lint berhasil. Uji browser memverifikasi dialog terbuka, tombol **Reset sesi** terkunci sebelum teks `RESET DEMO` diisi, lalu aktif setelah teks sesuai; **Batal** menutup dialog. Reset database tidak dijalankan dalam uji ini; generation tetap **9** dan 10 bukti OEM tetap tersedia. API aktif sehat. Panduan demo diperbarui dengan langkah reset dan dampaknya.

Pembaruan halaman utama pada release **main-20261023-r6**: alur maintenance tampil langsung di `/` dan `/technician/`; `/maintenance/` lama mengalihkan ke beranda. Menu halaman demo dan reset dihapus dari navigasi. Meja manajer mendukung benchmark conveyor makanan dengan pengakuan asumsi eksplisit; perubahan penawaran memerlukan pembaruan perbandingan sehingga tidak memakai kalkulator lama tanpa persetujuan.

Build frontend (13 halaman statis), TypeScript, lint, dan 34 tes identitas lulus. Uji browser pada beranda menghasilkan assessment `7a7325b6-b132-4696-9c1e-874c19a0594c` dengan empat tool calls, kemudian WO `728dc425-2ae9-44d8-a299-0edebdce6b04` berstatus `identified`. WO dibuka di meja manajer, lima gudang tampil, dan perhitungan benchmark melalui UI berhasil. Tidak ada WhatsApp yang dikirim pada uji perubahan halaman ini.

Uji pertama menemukan jawaban model dengan normalisasi kategori yang ditolak validator (`category_normalization_mismatch`). Instruksi ekstraksi diperjelas agar `value` dan `normalized_value` kategori persis `Bearing`; validasi tidak dilonggarkan. WO gagal `5395a618-ae96-4be0-ae73-9cfe050078be` tetap tersimpan sebagai audit. Uji ulang berhasil; model tetap dapat menghasilkan `needs_review` bila keluarannya tidak memenuhi kontrak.

| Pemeriksaan | Hasil dan batas cakupan |
|---|---|
| Suite aktif `pytest tests/codex -m 'not live_gateway' -q` | **291 passed**, 1 deselected, 3 peringatan deprecation. |
| Test gateway live untuk WO dan procurement | **1 passed**, 9,86 detik; memakai model nyata dan PostgreSQL terisolasi. Fixture migrasi test diperbaiki agar mencakup012–016. |
| Regresi setelah perbaikan WO r2 | **119 passed** untuk food, identitas, database, dan pencocokan deskripsi; **136 passed** pada suite portable yang terkait. Angka ini beririsan dengan suite utama, bukan tambahan yang boleh dijumlahkan. |
| Horizon pemulihan r3 | **32 passed**, termasuk PostgreSQL terisolasi: ETA lebih dari 48 jam tercakup hingga pulih dan horizon yang terlalu pendek tidak dapat diranking. |
| Parser form WhatsApp r3 | **94 passed**, termasuk PostgreSQL terisolasi. Dua waktu dalam satu baris terbaca; duplikasi kolom, angka terpotong, dan peminjaman nilai kolom lain ditolak. |
| Parser tanggal final r4 | **117 passed**, termasuk PostgreSQL. Tanggal berupa negasi, rentang, alternatif, atau zona waktu bertentangan ditolak. Format tanggal lengkap yang didukung tetap diterima. |
| Provenance ketersediaan final r4 | **97 passed**, termasuk PostgreSQL: identitas, katalog, food, lima gudang, dan procurement. Katalog hilang/scope tidak sah menghentikan pencarian tanpa fallback catatan NTN. |
| Maintenance agent pada PostgreSQL terisolasi | 10 record diingest; 4 tool calls; hasil valid disimpan dan dibaca ulang. Salah satu run: 2 giliran model, 14,22 detik. |
| Bridge WhatsApp | **13 tests passed**; allowlist juga diuji di backend sebelum transport dipanggil. |
| Frontend akhir | Build berhasil: 13 halaman statis; TypeScript dan lint berhasil. |

Suite utama dijalankan sebelum patch r2–r4; test yang terdampak dijalankan ulang setelah patch. Hasil tidak dijumlahkan sebagai jumlah test unik.

`pytest` tanpa pembatasan tidak seluruhnya lulus. Run awal menghasilkan 23 gagal, 269 lulus, 41 dilewati, dan 135 error: sebagian besar acceptance test lama masih menargetkan `src/partpilot/app.py` dan direktori `db/` yang tidak tersedia pada release asal. Dependency lingkungan test Vertex serta fixture live gateway kemudian diperbaiki dan kelompok terkait berhasil diuji ulang. Test legacy yang usang tidak diklaim lulus.

## Pengujian aplikasi aktif

Assessment `779027db-0d40-4ba6-aac6-9e5a60a68d6c` selesai melalui browser dengan empat panggilan bukti: kasus OEM, katalog exact, troubleshooting, dan katalog kandidat. WO `5fb87790-95c6-4d9e-97dd-8599f7dc1505` berstatus **identified**, dengan part `DEMO-RHP-PSF20CR`, jumlah2, dan rujukan katalog OEM asli. Gudang asal kosong; Gudang2 memiliki dua unit exact dari fixture simulasi.

Pengujian pertama menemukan frasa model “bearing unit flange” ditolak validator kategori lama. Patch r2 menerima frasa yang terbukti ada dalam permintaan, tetap menolak bukti palsu, serta memakai katalog RHP terverifikasi untuk WO makanan. Katalog yang hilang menghentikan proses sebelum model dipanggil.

RFQ WhatsApp `PP-bd835457` dikirim pada 04.12 WIB hanya ke **082178830078**. Lima balasan pengguna diterima. Sistem mengirim tiga klarifikasi dan tidak menebak tahun/jam yang belum diberikan. Pesan terakhir memiliki dua kolom waktu dalam satu baris; parser diperbaiki, lalu pesan asli diproses ulang melalui validator dan fungsi audit database. Body dan ID pesan tidak diganti, tidak dibuat balasan sintetis, dan tidak ada RFQ ulang. Conversation berstatus **quoted**, delapan kolom lengkap, `missing_fields=[]`.

Penawaran pengujian: RHP PSF20CR, stok10, harga Rp500.000/unit, ongkir Rp50.000 total, pajak Rp50.000 total, persiapan5 jam, ETA **29 Oktober 2026 10.00 WIB**, berlaku sampai **4 November 2026 12.00 WIB**. Ini input simulasi yang benar-benar dikirim lewat WhatsApp, bukan harga vendor komersial terverifikasi.

Perbandingan `346f4ed4-ce46-437e-ba5f-c5087bd73870` pada 04.31 WIB menghitung seluruh waktu sampai pulih:

| Opsi | Biaya sumber | Waktu terdampak mendatang | Total relevan skenario |
|---|---:|---:|---:|
| Gudang2, dua unit exact | Rp6.650.000 | 5,68 jam | Rp309.531.332,00 |
| Vendor WhatsApp, dua unit exact | Rp1.100.000 | 151,48 jam | Rp8.076.862.591,34 |

Kedua total mencakup Rp250.000 asumsi tenaga pemulihan dan benchmark OEM dengan pemetaan simulasi 16.000. Angka besar tersebut menunjukkan sensitivitas terhadap durasi, **bukan kerugian nyata pabrik pengguna**. Jadwal penuh kontinu, waktu instalasi/restart, dan mapping mata uang perlu dikalibrasi saat data pabrik tersedia. Negosiasi dilewati karena biaya di luar harga barang sudah melampaui target (`non_item_cost_exceeds_target`); tidak ada counteroffer yang dikirim.

Keputusan browser **warehouse:SYN-WH-02** tersimpan pada 04.31 WIB, ID `9470084d-846d-44fd-9733-e37be93fab24`, `procurement_executed=false`. UI menampilkan “Keputusan sudah tercatat” dan “Sudah dipilih”.

Setelah r4 aktif, smoke test pada **04.39 WIB** berhasil memeriksa health, 10 bukti, WhatsApp terhubung dengan satu penerima, penawaran lengkap, keputusan gudang, serta PO kandidat. Evaluasi ketersediaan baru untuk **kedua SKU di kelima gudang** memuat URL/hash katalog OEM dan tidak lagi membawa catatan NTN lama. Snapshot sourcing sebelumnya tetap disimpan sebagai riwayat pengujian; tidak ditulis ulang agar tampak dibuat oleh versi baru. Endpoint evaluasi bersifat baca dan tidak melakukan reservasi atau mutasi stok.

## Cabang alternatif sampai PO demo

Pengujian terpisah melalui API publik memakai assessment `e667e949-2865-4884-8122-551d86f49bcb`. Model 9router menyelesaikan dua giliran dan empat tool calls dalam16,087 detik. PSF20/LP99 mendapat review engineering yang secara eksplisit berlabel **simulasi**, lalu WO `b37ca026-5748-44e1-85e1-7e2c184805a5` berhasil diidentifikasi memakai katalog OEM.

Run `0aa2980f-e353-4a56-81dc-d7fc6d88ffe6` membandingkan gudang dan vendor simulator. Pilihan vendor `SIM-ENOUGH` menghasilkan **PO-DEMO-20261023-A5F8B407A73F**, total tagihan **Rp8.650.000**. PDF satu halaman berhasil diunduh (HTTP200), terbaca, dan memuat penanda demo/tidak dikirim/tidak ada pembelian aktual. Biaya downtime tidak masuk tagihan PO. Pengujian ini tidak memanggil WhatsApp dan tidak mengubah run exact di atas.

## Batas klaim demo

Kasus OEM merupakan riwayat eksternal terpublikasi. Tidak ada histori CMMS pengguna yang direkayasa. Nama part nyata; aset, stock, harga, ETA, pemeriksaan engineering demo, dan operasi adalah simulasi. Pemetaan bawaan terbaru 18.000 IDR per unit dolar publikasi bukan kurs nyata; hasil pengujian sebelum r8 memakai 16.000. Total biaya merupakan estimasi skenario, bukan kerugian pabrik yang terukur.

Keputusan akhir membuat catatan/PO demo; tidak mengirim pesanan pembelian atau memindahkan stok. Prediksi umur bearing, tanggal kegagalan, dan predictive maintenance berbasis sensor belum tersedia.
