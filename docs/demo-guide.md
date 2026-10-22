# Panduan demo PartPilot: input, tombol, dan fungsi setiap section

Disesuaikan dengan aplikasi aktif **main-20261023-r8**, 23 Oktober 2026. Mulai dari [halaman utama PartPilot](https://partpilot.rifqisetiawan.my.id/).

**Story satu kalimat:** “Conveyor makanan bising setelah washdown; PartPilot memakai kasus dan katalog OEM untuk membantu inspeksi, menyiapkan WO, lalu memilih sumber part dengan mempertimbangkan waktu pulih dan estimasi kerugian produksi.”

**Jalur utama:** gejala → bukti dan dugaan penyebab → konfirmasi part exact → WO → gudang sendiri/gudang lain → penawaran vendor → perbandingan biaya → keputusan sumber. Cabang alternatif PSF20/LP99 dan pembuatan PO dijelaskan setelah jalur utama.

## Sebelum mulai: navigasi dan pilihan jalur

| Bagian atas halaman | Untuk apa / apa yang dilakukan |
|---|---|
| **Teknisi** | Membuka halaman utama dengan form gejala. Seluruh jalur utama bisa didemokan di sini sampai keputusan. |
| **Meja manajer** | Membuka daftar WO tersimpan; manajer dapat melanjutkan pencarian, membandingkan sumber, dan mencatat keputusan untuk WO yang sama. |
| **Reset** | Mengulang seluruh sesi simulasi untuk semua pengguna. Membuka dialog dahulu; belum mereset saat baru diklik. |
| Banner bukti OEM dan simulasi | Menjelaskan batas data: sumber pengetahuan nyata, sedangkan inventori dan operasi yang diperagakan adalah simulasi. |

Pilih satu jalur vendor sebelum mulai: **WhatsApp** untuk memperagakan balasan nyata dari nomor pengujian, atau **simulator** untuk presentasi tanpa menunggu ponsel. Jangan menjalankan simulator terlebih dahulu jika akan memakai WhatsApp pada pencarian yang sama.

Untuk WhatsApp, siapkan ponsel nomor **082178830078**. Hanya nomor tersebut yang diizinkan untuk pengujian saat ini. Tombol RFQ benar-benar mengirim pesan; isi penawarannya tetap data simulasi.

Selama memperagakan analisis, tetap di halaman ini sampai WO terbentuk. Refresh atau berpindah halaman tidak memulihkan tampilan assessment terakhir secara otomatis. WO yang sudah dibuat tetap bisa dibuka dari **Meja manajer**. Jangan klik Reset hanya untuk mengulang analisis satu kasus.

## 1. Section “Gejala dan bukti teknisi”

**Fungsi:** mengumpulkan keluhan, kode komponen yang dibaca dari marking/BOM, jumlah kebutuhan, dan identitas teknisi. Ini input analisis, bukan diagnosis yang sudah dipastikan.

Isi **Gejala** dengan:

```text
Conveyor makanan terasa kasar dan bising setelah high-pressure washdown; ada jejak korosi di sekitar flange. Mesin dihentikan untuk inspeksi.
```

| Kolom | Isi untuk demo | Arti kolom |
|---|---|---|
| **Kode unit pada marking/BOM** | `RHP PSF20CR` | Kode unit lengkap sebagai dasar pencarian exact. Jangan menggantinya dengan kode insert saja. |
| **Jumlah hasil inspeksi** | `2` | Jumlah unit yang dibutuhkan WO, bukan stok vendor. |
| **Nama teknisi** | `Rifqi — teknisi demo` | Pihak yang mengonfirmasi kebutuhan; wajib terisi sebelum membuat WO. |

**Klik:** **Analisis dengan AI dan bukti OEM** sekali, lalu tunggu proses selesai. Section 2 muncul setelah respons diterima; section 3 tersedia bila assessment berstatus `completed`.

**Yang disampaikan:** “Teknisi melaporkan gejala dan kode yang ditemukan. AI mencari bukti untuk membantu pemeriksaan sebelum penggantian diputuskan.”

Marking PSF20CR, aset conveyor, jumlah dua unit, dan inspeksi dalam demo ini merupakan skenario simulasi. Nama komponennya nyata; kasus historis OEM tidak menyebut bahwa aset demo ini memakai SKU atau jumlah tersebut.

## 2. Section “Analisis dan jejak penggunaan tools”

**Fungsi:** menunjukkan hasil penalaran berbasis bukti, pemeriksaan yang masih diperlukan, dan sumber yang dibaca agent. **Tidak ada kolom yang perlu diisi.**

| Isi section | Cara membaca / tindakan presenter |
|---|---|
| **Assessment … • completed** | ID dan status analisis yang mendasari WO. |
| Ringkasan diagnosis | Baca sebagai dugaan penyebab yang perlu inspeksi; jangan menyebut kerusakan sudah terbukti. |
| Kartu penyebab dan **Pemeriksaan:** | Pilih satu hipotesis relevan untuk dijelaskan, misalnya hubungan washdown dengan korosi/masuknya air apabila muncul pada hasil. Jelaskan pemeriksaan yang diminta AI. |
| Daftar tindakan | Saran tindak lanjut/perbaikan berdasarkan bukti. Isi kalimat dapat berbeda antar-run. |
| **Tindak lanjut maintenance dan batas bukti** | Klik untuk membuka saran tindak lanjut dan keterbatasan hasil. Ini bukan prediksi tanggal rusak atau umur bearing. |
| Daftar tool, status, durasi, dan ID bukti | Tunjukkan bahwa agent memanggil tools dan memperoleh bukti. Urutan/jumlah panggilan mengikuti run, tidak harus selalu sama. |
| **Dokumen yang dipakai dan sumber aslinya** | Klik, lalu klik salah satu tautan sumber. Dokumen terbuka di tab baru; kembali ke tab PartPilot untuk melanjutkan. |

Tools yang dapat terlihat: `retrieve_cases` untuk kasus OEM terpublikasi, `read_catalog_part` untuk katalog part exact/kandidat, dan `read_troubleshooting` untuk pedoman pemeriksaan. Riwayat yang digunakan merupakan **kasus eksternal OEM**, bukan log CMMS atau histori mesin milik pengguna.

**Yang disampaikan:** “Bagian agentic AI ada pada pemilihan dan pemanggilan tools untuk membaca kasus, katalog, serta troubleshooting, kemudian menyusun hipotesis dan usulan tindakan. Dokumen yang mendasarinya bisa ditelusuri.”

## 3. Section “Konfirmasi part dan work order” — jalur exact

**Fungsi:** memisahkan usulan AI dari kebutuhan part yang dikonfirmasi manusia, lalu membuat work order.

| Bagian | Maksudnya |
|---|---|
| **Exact: RHP PSF20CR** | Unit flange empat baut lengkap dengan identitas sama seperti kode input. Ini jalur utama demo. |
| **Kandidat: RHP PSF20/LP99** | Usulan alternatif yang perlu review teknis dan higiene. Belum otomatis setara atau layak dipasang. |
| Checkbox konfirmasi marking/BOM | Pernyataan teknisi bahwa kode, jumlah, dan kebutuhan penggantian sudah diperiksa untuk skenario ini. Pada demo, pemeriksaannya simulasi. |
| **Review kandidat alternatif PSF20/LP99** | Opsional. Untuk jalur exact, biarkan tertutup dan tidak perlu diisi. Langkah alternatif ada di bagian 8. |

**Urutan klik:**

1. Pastikan **Nama teknisi** pada section 1 sudah diisi.
2. Centang **Saya sudah mengonfirmasi marking/BOM, jumlah, dan kebutuhan penggantian untuk skenario yang sedang dievaluasi.**
3. Klik **Buat / buka WO part exact**.
4. Tunggu kotak WO menampilkan SKU **PSF20CR** dan status **`identified`**. Status dapat melalui antre/proses sebelum selesai.
5. Klik **Cari gudang sendiri dan gudang lain** pada kotak WO tersebut.

Tombol pembuatan WO belum menjalankan pembelian atau memindahkan stok. Sistem membuat/membuka WO yang terkait dengan assessment, lalu mengidentifikasi part.

Jika status memerlukan klarifikasi/pemeriksaan, klik **Buka detail / klarifikasi WO** dan baca masalahnya. Jangan menganggap hasil `needs_review` sebagai identitas yang sudah valid.

Tautan **Buka WO ini di meja manajer →** membuka WO yang sama pada tampilan manajer. Untuk jalur utama paling sederhana, lanjutkan di halaman sekarang. Pilihan pindah ke tampilan manajer dijelaskan pada bagian 9.

**Yang disampaikan:** “Setelah teknisi mengonfirmasi unit lengkap dan jumlahnya, PartPilot menyiapkan WO serta mencari part exact di seluruh gudang.”

## 4. Section “Stok barang yang sama di setiap gudang”

Section ini muncul setelah tombol pencarian gudang dijalankan. **Tidak ada input yang perlu diisi.**

**Fungsi:** memperlihatkan hasil pencocokan identitas part antar-gudang, meskipun nama dan kode internal barang berbeda.

| Isi kartu gudang | Arti |
|---|---|
| Nama, alamat, dan penanda **Gudang asal** | Lokasi sumber barang; gudang asal adalah lokasi awal kebutuhan WO. |
| **Nama di gudang / Kode di gudang** | Label dan kode inventori di lokasi tersebut. Perbedaan kode internal tidak otomatis berarti komponen berbeda. |
| **Stok fisik** | Jumlah barang yang ada. |
| **Sudah dialokasikan** | Bagian stok yang disiapkan untuk kebutuhan lain. |
| **Bisa dipakai** | Stok fisik dikurangi alokasi. Angka ini dibandingkan dengan kebutuhan. |
| **Kebutuhan WO / Kekurangan** | Kebutuhan dua unit dan selisih yang belum tercukupi. |
| Status stok | Bedakan stok kurang/kosong dengan identitas atau data yang belum dapat dipastikan. “Belum diketahui” bukan berarti nol. |

Fixture awal jalur exact: **Gudang 1 kosong; Gudang 2 memiliki dua unit exact yang bisa dipakai**. Gunakan nilai aktual di layar jika data berubah.

**Yang disampaikan:** “Gudang sendiri tidak cukup. Sistem menemukan identitas unit yang sama di gudang lain, lalu membandingkannya dengan vendor berdasarkan biaya sampai produksi pulih.”

Kartu stok belum merupakan keputusan pengadaan. Dalam alur ini satu sumber dipilih untuk memenuhi seluruh kebutuhan WO, bukan pembagian pesanan ke beberapa sumber.

## 5. Section “Vendor dan biaya sampai produksi pulih”

**Fungsi:** mengambil penawaran vendor untuk SKU pada WO dan menetapkan asumsi perhitungan biaya. Periksa tulisan **Pencarian ini untuk …** agar penawaran sesuai SKU exact atau kandidat yang sedang dibuka.

### 5A. Pilihan vendor melalui WhatsApp

1. Bila perlu, klik **Status / koneksi WhatsApp (tab baru)**. Pastikan status **Terhubung**. Tab ini hanya untuk koneksi/percakapan, belum mengirim RFQ.
2. Kembali ke tab WO. Klik **Kirim RFQ WhatsApp** sekali. Pesan dikirim ke nomor pengujian **082178830078**.
3. Di ponsel nomor tersebut, gunakan fitur **Reply/Balas** pada RFQ terbaru agar jawaban terkait ke permintaan yang benar.
4. Salin seluruh form berikut sebagai balasan:

```text
Merek dan nomor kode : RHP PSF20CR
Stok tersedia (pcs) : 10
Harga per pcs (Rp) : 500000
Ongkos kirim total (Rp) : 50000
Pajak total (Rp) : 50000
Waktu persiapan sebelum dikirim (jam) : 5
Perkiraan tiba (tanggal dan jam WIB) : dalam 8 jam
Penawaran berlaku sampai (tanggal dan jam WIB) : dalam 2 hari
```

| Input penawaran | Penjelasan |
|---|---|
| Kode part | Harus sama dengan SKU yang diminta. Form di atas untuk **PSF20CR**, bukan kandidat. |
| Stok 10 | Jumlah tersedia pada vendor; WO tetap membeli dua unit. |
| Harga Rp500.000 | Harga per unit. |
| Ongkir Rp50.000 dan pajak Rp50.000 | Masing-masing nilai total penawaran, bukan per unit. |
| Persiapan 5 jam | Waktu persiapan sebelum dikirim. |
| Tiba dalam 8 jam | Waktu sampai barang tiba, sudah mencakup persiapan lima jam; tidak dijumlahkan menjadi 13 jam. |
| Berlaku dalam 2 hari | Batas waktu penawaran dapat dipakai untuk keputusan. |

Waktu relatif dihitung dari **waktu pesan diterima**. Untuk waktu absolut, tulis tanggal lengkap beserta tahun, jam, dan `WIB`, serta pastikan masih di masa depan. Jangan memakai rentang/dua pilihan waktu untuk satu kolom.

Total tagihan dua unit pada form ini adalah **Rp1.100.000**: 2 × Rp500.000 + Rp50.000 + Rp50.000. Ini harga pengujian, bukan harga pasar terverifikasi.

### 5B. Pilihan vendor simulator

Klik **Ambil penawaran vendor simulasi**. Sistem menggunakan fixture vendor tanpa mengirim pesan WhatsApp. Tidak perlu mengisi form di ponsel. Lanjutkan ke asumsi biaya setelah proses selesai.

Gunakan satu jalur vendor untuk satu pencarian. Jika simulator sudah dijalankan dan ingin mencoba WhatsApp, buat assessment/WO baru; jangan mencampur hasil kedua jalur pada pencarian yang sama.

### 5C. Membaca kartu percakapan WhatsApp

Kartu ini muncul setelah RFQ dikirim. Halaman membaca pembaruan sekitar setiap lima detik.

| Isi kartu | Yang dilakukan |
|---|---|
| **Menunggu balasan vendor** | Balas RFQ dari ponsel; belum ada penawaran lengkap untuk dipilih. |
| **Menunggu kelengkapan penawaran / Belum lengkap:** | Baca kolom yang kurang, lalu balas klarifikasi dengan nilai jelas. |
| **Penawaran diterima** | Periksa kode, stok, harga, ongkir, pajak, ETA, dan masa berlaku yang berhasil diekstrak. |
| **Lihat percakapan (… pesan)** | Klik untuk memperlihatkan pesan keluar, balasan asli, dan tindak lanjut. |
| Pesan diterima tetapi belum terhubung | Balas ulang menggunakan fitur Reply pada RFQ aktif yang sesuai. |
| Jumlah tindak lanjut / counteroffer | Aktivitas yang benar-benar tercatat; counteroffer tidak selalu terjadi. |

**Yang disampaikan:** “Balasan vendor diubah menjadi penawaran terstruktur. Data yang belum lengkap diminta kembali, dan percakapannya tetap bisa ditelusuri.”

### 5D. Input benchmark biaya downtime

Klik tautan **NSK SS-E-2054** bila ingin menunjukkan sumber benchmark. Kasus tersebut melaporkan **3.332 unit `$` publikasi per jam**. ISO mata uang dan tahun harga tidak dipublikasikan; nilai ini bukan tarif aktual pabrik dan tidak dianggap pasti USD.

1. Kolom **Asumsi IDR per satu unit dolar publikasi** otomatis terisi nilai bawaan berikut; pastikan nilainya sesuai sebelum menghitung. Nilai tetap dapat diubah oleh pengguna:

```text
18000
```

2. Centang **Saya memahami penerapan benchmark dan konversi ini adalah asumsi skenario. Total rupiah yang dihasilkan merupakan estimasi simulasi.**
3. Klik **Hitung / perbarui perbandingan**.
4. Setiap harga, ETA, hasil negosiasi, atau nilai pemetaan berubah, klik tombol tersebut lagi sebelum memilih sumber.

Pemetaan ini menghasilkan **Rp59.976.000/jam untuk skenario**: 3.332 × 18.000. Manajer dapat mengubah angka pemetaan melalui kolom tersebut. Tarif sumber 3.332 tidak diedit dari UI ini; belum tersedia kolom langsung tarif downtime pabrik dalam Rp/jam.

Asumsi lain yang diisi sistem: **instalasi 1 jam, restart 1 jam, dan tenaga pemulihan Rp250.000**. Angka-angka ini simulasi. Perbandingan menghitung waktu produksi mendatang yang masih terdampak sampai pulih, bukan membebankan kembali seluruh kerugian masa lalu ke setiap opsi.

**Yang disampaikan:** “Kita memakai benchmark eksternal yang jelas sumbernya. Pemetaan rupiah adalah asumsi skenario untuk melihat dampak waktu tiba dan waktu pulih terhadap pilihan sumber.”

## 6. Section “Rekomendasi berdasarkan biaya” dan “Biaya total sampai produksi pulih”

**Fungsi:** memperlihatkan sumber dengan total relevan terendah di antara opsi yang lengkap dan masih berlaku. Perhitungan dan peringkat memakai aturan kalkulasi, bukan angka yang dikarang model bahasa.

### Kartu rekomendasi

Tunjukkan nama sumber, total relevan, stok tersedia, dan ETA. Jika sebagian sumber belum lengkap, rekomendasi dapat berubah setelah penawaran baru masuk. Belum ada sumber yang dipilih hanya karena kartu rekomendasi muncul.

### Tabel “Sumber gudang” dan “Penawaran vendor”

| Kolom / bagian | Maksudnya |
|---|---|
| **Peringkat / sumber** | Peringkat global membandingkan gudang dan vendor bersama-sama meskipun ditampilkan dalam dua tabel. |
| **Stok** | Jumlah tersedia untuk memenuhi seluruh kebutuhan. |
| **Harga / buah** | Nilai per unit pada sumber tersebut. |
| **Ongkir / pajak** | Komponen biaya tambahan penawaran. |
| **Barang + ongkir + pajak** | Biaya sumber; pada vendor inilah dasar total tagihan PO. |
| **Kerugian produksi (estimasi)** | Estimasi dampak waktu sampai produksi pulih dengan benchmark dan asumsi yang disetujui. |
| **Pemulihan** | Biaya tambahan pemulihan sesuai asumsi, terpisah dari tagihan vendor. |
| **Total relevan** | Biaya sumber + pemulihan + estimasi kerugian produksi. Inilah dasar urutan opsi. |
| **Waktu & validitas** | Klik untuk melihat waktu tiba, waktu pulih, dan batas berlaku. |
| **Belum dapat dipilih** | Sumber yang belum lengkap atau tidak memenuhi syarat beserta alasannya. |

Pada layar sempit, geser tabel ke kanan untuk menemukan total dan tombol tindakan.

**Yang disampaikan:** “Harga barang paling murah belum tentu memberikan total biaya paling rendah. Kita membandingkan ongkos mendapatkan part dan dampak menunggu produksi pulih.”

Dengan fixture exact baru dan balasan WhatsApp segera, Gudang 2 diperkirakan unggul karena lebih cepat. Tetap gunakan hasil aktual di layar; jangan menghafalkan total rupiah atau memaksakan pemenang tertentu.

Negosiasi mengikuti kebijakan maksimal satu putaran per vendor bila target memungkinkan. Bila biaya di luar barang saja sudah melampaui target, sistem dapat melewati negosiasi. Jangan menjanjikan bahwa setiap demo akan mengirim counteroffer.

## 7. Mencatat keputusan akhir

### Bila memilih gudang — penutup jalur utama

1. Klik **Pilih [nama gudang]** di kartu rekomendasi, atau **Pilih gudang** pada baris sumber yang diinginkan.
2. Section **Konfirmasi keputusan** muncul. Periksa sumber dan kebutuhan yang akan dipenuhi.
3. Klik **Konfirmasi keputusan** untuk menyimpan; **Batal** kembali tanpa memilih.
4. Tunjukkan tulisan **Keputusan sudah tercatat**, **Pilihan tercatat**, atau **Sudah dipilih** pada opsi tersebut.

Hasilnya adalah catatan keputusan sumber gudang. **Tidak ada PO vendor, perpindahan stok fisik, atau pemberitahuan otomatis kepada staf gudang.**

### Bila memilih vendor — menampilkan PO

1. Pilih vendor lengkap dan masih berlaku dengan **Setujui PO** pada tabel **Penawaran vendor**, atau **Pilih [vendor]** jika vendor menjadi rekomendasi.
2. Pada halaman utama, klik **Konfirmasi keputusan**.
3. Section **Purchase Order • PT PartPilot** muncul dengan nomor PO, pemasok, jumlah, harga, dan total tagihan.
4. Klik **Unduh PO (PDF)** untuk mengunduh dokumen, lalu buka file hasil unduhannya.

Total PO hanya barang, ongkir, dan pajak. Biaya pemulihan serta estimasi kerugian produksi digunakan untuk keputusan, bukan ditagihkan kepada vendor. PO berstatus demo dan tidak dikirim otomatis melalui WhatsApp/email.

**Satu assessment hanya boleh mempunyai satu keputusan akhir**, termasuk cabang exact dan alternatif. Jika ingin menunjukkan dua hasil akhir, buat assessment baru untuk hasil kedua. Status dipilih tidak berarti mesin sudah diperbaiki.

**Penutup:** “AI membantu menghubungkan gejala, bukti, dan usulan tindakan. Teknisi mengonfirmasi part, manajer menilai biaya sampai pulih, lalu keputusan tercatat dan dapat ditelusuri.”

## 8. Cabang opsional: “Review kandidat alternatif PSF20/LP99”

Gunakan cabang ini untuk menunjukkan pencarian **alternatif yang berbeda dari part awal**. Jika hanya mendemokan exact, seluruh section ini boleh dilewati.

**Makna review:** AI boleh mengusulkan kandidat, tetapi manusia harus memeriksa kecocokan sebelum kandidat dipakai untuk pengadaan. Dimensi antarmuka sama belum membuktikan kesetaraan. UI menampilkan batas suhu LP99 dan bahwa bukti sertifikasi food contact/NSF H1 belum tersedia dalam paket sumber; jangan menyatakan persetujuan higiene sudah dibuktikan oleh AI.

### Langkah dan input

1. Jika assessment sebelumnya sudah mempunyai keputusan akhir, kembali ke section 1 dan klik **Analisis dengan AI dan bukti OEM** untuk membuat assessment baru. Gunakan gejala, marking awal **RHP PSF20CR**, jumlah dua, dan nama teknisi yang sama. Tidak perlu Reset seluruh aplikasi.
2. Setelah selesai, pada section 3 klik **Review kandidat alternatif PSF20/LP99** untuk membuka panel.
3. Untuk simulasi alur persetujuan saja, isi berikut:

| Isi panel | Input demo | Fungsi |
|---|---|---|
| **Antarmuka, beban, putaran dan fit diperiksa** | Centang untuk simulasi | Persetujuan kecocokan mekanis terhadap kebutuhan pemasangan/operasi. |
| **Suhu dan duty cycle cocok** | Centang untuk simulasi | Persetujuan batas suhu dan pola operasi. |
| **Tim higiene menyetujui penggunaan pada posisi ini** | Centang untuk simulasi | Persetujuan higiene untuk posisi penggunaan dalam proses makanan. |
| **Reviewer** | `Rifqi — reviewer simulasi` | Pihak yang bertanggung jawab atas review. |
| **Dasar keputusan (nyatakan jika hanya simulasi)** | Tempel teks di bawah | Alasan dan batas persetujuan yang disimpan sebagai catatan. |

```text
SIMULASI pengujian aplikasi. Pemeriksaan mekanis, suhu, pola operasi, dan higiene diasumsikan disetujui untuk skenario ini. Belum ada inspeksi atau persetujuan engineering pada mesin nyata. Kecocokan PSF20/LP99 harus diverifikasi sebelum penggunaan aktual.
```

4. Klik **Catat persetujuan engineering**. Tunggu label menjadi **Review sudah tercatat**.
5. Centang konfirmasi marking/BOM, jumlah, dan kebutuhan skenario di bagian atas section 3. Pastikan nama teknisi masih terisi.
6. Klik **Cari sumber kandidat yang disetujui**. Walaupun bernama “Cari sumber”, langkah ini terlebih dahulu membuat/membuka **WO kandidat**.
7. Tunggu WO **PSF20/LP99** berstatus **`identified`**, lalu klik **Cari gudang sendiri dan gudang lain**.
8. Periksa SKU pada hasil stok. Sistem memakai **RHP PSF20/LP99** otomatis untuk WO kandidat; tidak perlu mengganti marking awal PSF20CR pada section 1.
9. Pilih **Ambil penawaran vendor simulasi** untuk jalur cepat, lalu isi pemetaan `18000`, centang pengakuan asumsi, dan klik **Hitung / perbarui perbandingan**.
10. Baca hasil aktual. Untuk memperagakan pembuatan PO, pilih vendor layak dengan **Setujui PO** → **Konfirmasi keputusan** → **Unduh PO (PDF)**. Jika vendor tersebut bukan rekomendasi termurah, jelaskan bahwa pilihan ini untuk menunjukkan keluaran PO, bukan klaim bahwa vendor menang biaya.

Fixture kandidat menyediakan dua unit di Gudang 3. Stok dan penawaran tetap simulasi. Jika memakai WhatsApp untuk kandidat, gunakan pencarian baru yang belum menjalankan simulator dan ganti **hanya kode part** pada form menjadi:

```text
Merek dan nomor kode : RHP PSF20/LP99
```

Sertakan kembali tujuh kolom penawaran lainnya. Penawaran exact PSF20CR tidak boleh digunakan untuk kandidat PSF20/LP99.

Pada penggunaan nyata, checkbox hanya dicentang setelah pemeriksaan/persetujuan benar-benar dilakukan. Catatan simulasi tidak merupakan izin pemasangan pada mesin nyata.

**Yang disampaikan:** “Alternatif tidak langsung disamakan dengan part awal. Agent menyiapkan kandidat dan bukti, lalu persetujuan engineering serta higiene menjadi syarat sebelum kandidat diteruskan ke pencarian sumber.”

## 9. Opsional: memperagakan perpindahan ke “Meja manajer”

Halaman ini memproses **WO yang sama**, bukan membuat demo baru. Cara paling mudah adalah menyelesaikan pengambilan penawaran di halaman utama, lalu membuka tautan **Buka WO ini di meja manajer →** sebelum keputusan akhir.

Alternatifnya, klik tab **Meja manajer**, cari WO yang tepat, lalu klik **Buka stok & perbandingan →** pada barisnya. Cocokkan ID WO, SKU, dan jumlah agar tidak membuka hasil pengujian lama.

| Section / kontrol | Fungsi dan tindakan |
|---|---|
| **ORDER LIST** | Daftar WO tersimpan. Gunakan **Cari work order**, filter status/urgensi, atau **Muat ulang**. |
| **Buat work order** | Kembali ke form Teknisi untuk kebutuhan baru; tidak diperlukan bila WO demo sudah ada. |
| **Meja keputusan** — ringkasan WO | Menampilkan kebutuhan, jumlah, gudang asal, dan status identifikasi. Jika belum valid, gunakan **Selesaikan identifikasi terlebih dahulu**. |
| Pemeriksaan stok | Untuk WO teridentifikasi, halaman mencoba memeriksa stok otomatis. Gunakan **Coba cek stok lagi** bila pemeriksaan gagal. |
| **Penawaran vendor melalui WhatsApp** | Jika belum ada penawaran dan ingin mengirim dari sini, klik **Kirim RFQ WhatsApp pengujian**. Ini kirim nyata ke nomor uji. |
| **Benchmark biaya produksi hilang** | Isi `18000`, centang pengakuan benchmark/konversi simulasi, lalu **Hitung / perbarui perbandingan**. |
| **Penawaran WhatsApp nyata / Penawaran simulator** | Hasil tiap vendor, stok, harga awal/akhir, dan status negosiasi. “Nyata” merujuk transport balasan WhatsApp, bukan verifikasi harga komersial. |
| **Percakapan vendor** | Balasan asli, kolom yang terbaca, dan kebutuhan klarifikasi. |
| **Rekomendasi berdasarkan biaya / Biaya total sampai produksi pulih** | Cara membaca sama dengan bagian 6. Opsi belum lengkap atau kedaluwarsa tidak dapat dikonfirmasi. |

Jika ingin WhatsApp dari tampilan manajer, kirim RFQ **sebelum membuat perbandingan gudang saja**. Pada versi UI ini, panel kirim RFQ dapat tidak tampil setelah perbandingan tersedia. Jalur simulator dimulai dari halaman utama; tidak ada tombol ambil penawaran simulator pada Meja keputusan.

Balasan WhatsApp diperbarui sekitar setiap lima detik, tetapi **perbandingan biaya kasus makanan harus diperbarui dengan tombol** setelah penawaran berubah. Jangan menampilkan peringkat lama sebagai hasil penawaran terbaru.

Nama tombol konfirmasi berbeda dengan halaman utama:

| Sumber | Tombol awal | Tombol pada dialog | Hasil |
|---|---|---|---|
| Gudang | **Pilih gudang** atau **Pilih [nama gudang]** | **Konfirmasi pilihan gudang** | **Request mutasi berhasil dicatat**; klik **Selesai**. Ini catatan simulasi, bukan perpindahan stok nyata. |
| Vendor | **Setujui PO** atau **Pilih [vendor]** | **Konfirmasi PO demo** | Kartu PO dan **Unduh PO (PDF)**. |

Jika muncul bahwa data/penawaran berubah, klik **Tutup & perbarui**, hitung ulang perbandingan, lalu tinjau pilihan lagi. Jangan membuat keputusan kedua untuk assessment yang sudah selesai.

## 10. Mengulang demo dan menangani tombol yang belum aktif

### Reset seluruh sesi

Gunakan ketika memang ingin membersihkan sesi aktif untuk presentasi ulang:

1. Klik **Reset** di kanan atas.
2. Pada dialog **Kembalikan sesi ke awal?**, baca dampaknya.
3. Isi **Ketik RESET DEMO** dengan `RESET DEMO` persis.
4. Klik **Reset sesi**. Aplikasi kembali ke halaman utama dengan form baru.
5. Jika tidak jadi, klik **Batal**; tidak ada data yang direset.

Reset berlaku untuk semua pengguna: WO, penawaran, dan keputusan aktif dibersihkan; stok sintetis dipulihkan; percakapan WhatsApp aktif ditutup dan pesan yang belum dikirim dibatalkan. Bukti OEM dan catatan audit tetap disimpan. Pesan yang sudah terkirim tidak ditarik kembali dari ponsel penerima.

### Bila belum bisa melanjutkan

| Kondisi | Periksa / lakukan |
|---|---|
| **Buat / buka WO part exact** abu-abu | Analisis selesai dan mendukung exact, nama teknisi minimal dua karakter, konfirmasi skenario dicentang, serta tidak ada proses lain berjalan. |
| **Catat persetujuan engineering** abu-abu | Tiga checkbox terisi, reviewer minimal dua karakter, dan dasar keputusan minimal sepuluh karakter. Untuk demo gunakan catatan simulasi di atas. |
| **Cari sumber kandidat yang disetujui** abu-abu | Catat review dahulu, centang konfirmasi skenario, dan isi nama teknisi. |
| Tombol pencarian gudang belum muncul | Tunggu WO `identified`. Jika meminta review/klarifikasi, buka detail WO. |
| **Hitung / perbarui perbandingan** abu-abu | Centang pengakuan benchmark. Tombol juga terkunci saat proses berjalan atau keputusan sudah tercatat. |
| Vendor belum dapat dipilih | Periksa kode, kecukupan stok, kelengkapan harga/waktu, masa berlaku, dan status negosiasi. Baca alasan **Belum dapat dipilih**. |
| **Kedaluwarsa** | Minta penawaran dengan masa berlaku baru, lalu hitung ulang; jangan memakai total lama. |
| Sudah ada keputusan exact tetapi ingin keputusan alternatif | Buat assessment baru melalui tombol analisis, lalu jalankan cabang alternatif. Tidak perlu reset seluruh aplikasi. |
| Halaman meminta muat ulang karena sesi direset | Muat ulang sebelum melanjutkan agar memakai sesi terbaru. |

## Catatan singkat untuk jawaban kepada juri

- **Yang asli:** kasus kegagalan OEM terpublikasi, katalog/penamaan komponen, pedoman troubleshooting, dan angka benchmark dari sumber. Semua dapat ditelusuri lewat referensi; kasus OEM bukan histori mesin demo.
- **Yang simulasi:** aset/inspeksi demo, stok gudang, vendor/harga/ETA contoh, persetujuan engineering demo, pemetaan rupiah, dan operasi pengadaan. Balasan WhatsApp benar-benar diterima, namun isinya penawaran pengujian.
- **Bagian agentic AI:** agent memilih dan memanggil tools bukti, lalu menyusun hipotesis, pemeriksaan, dan usulan part. Identifikasi WO serta ekstraksi balasan mengikuti validasi; biaya, peringkat, dan kebijakan negosiasi dihitung dengan aturan yang dapat diaudit. Manusia mengonfirmasi part, alternatif, pengiriman RFQ, dan keputusan akhir.
- **Batas kemampuan:** belum memprediksi sisa umur bearing, tanggal kegagalan, atau predictive maintenance berbasis sensor. Rekomendasi pemeriksaan/tindak lanjut tidak sama dengan prediksi umur komponen.
- **Gateway aktif:** 9router. Adapter Vertex untuk project `hackathon-primestep-16` tersedia, tetapi belum diaktifkan dan diuji live karena credential belum tersedia.

Untuk rincian setiap sumber dan alur penggunaan data, lihat [Ringkasan data dan Agentic AI](data-and-agentic-ai.md).
