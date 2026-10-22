# Panduan demo singkat PartPilot

**Story satu kalimat:** “Conveyor makanan bising setelah washdown; PartPilot memakai kasus dan katalog OEM untuk membantu inspeksi, menyiapkan WO, lalu memilih sumber part dengan mempertimbangkan waktu pulih dan estimasi kerugian produksi.”

1. Buka [Demo conveyor makanan](https://partpilot.rifqisetiawan.my.id/maintenance/). Pakai gejala bawaan, marking **RHP PSF20CR**, jumlah **2**, dan nama teknisi demo.
2. Klik **Analisis dengan AI dan bukti OEM**. Tunjukkan hipotesis, pemeriksaan, tool calls, serta tautan dokumen. Kasus OEM adalah preseden eksternal, bukan riwayat mesin demo.
3. Centang konfirmasi marking/BOM dan kebutuhan penggantian. Klik **Buat / buka WO part exact**. Setelah `identified`, cari gudang. Fixture: asal kosong, gudang lain punya dua unit exact.
4. Pilih **satu jalur vendor**: simulator atau tombol **RFQ WhatsApp** ke 082178830078. Jangan menjalankan simulator dahulu jika akan memakai WhatsApp pada run yang sama. Isi form yang diterima; harga/ETA adalah data pengujian.
5. Tunjukkan sumber benchmark **$3.332/jam**. Akui penerapan benchmark dan pemetaan IDR simulasi, lalu hitung perbandingan. ETA ditambah instalasi dan restart; hanya jam produksi mendatang yang terdampak dihitung.
6. Bandingkan biaya sumber + pemulihan + estimasi produksi hilang. Setelah balasan berubah, perbarui perbandingan. Negosiasi hanya berlangsung jika target biaya memungkinkan; tidak selalu ada penawaran balik.
7. Opsional, **sebelum keputusan akhir**: buka kandidat **PSF20/LP99**, isi reviewer dan tiga pemeriksaan engineering/higiene, serta nyatakan bila persetujuannya hanya simulasi. Buat WO kandidat dan cari sumbernya. Tanpa persetujuan, kandidat tidak dapat dipilih sebagai pengganti.
8. Dalam satu siklus demo sebelum reset, konfirmasi satu keputusan akhir untuk assessment tersebut. Vendor menghasilkan PO demo; pilihan gudang mencatat sumber. Tidak ada pembelian atau perpindahan stok aktual.

**Penutup:** “AI menghubungkan gejala dengan bukti dan usulan tindakan; validasi teknis, kalkulasi biaya, serta persetujuan manusia menjaga keputusan dapat ditelusuri.”

## Input siap salin

Semua input di bawah adalah **skenario pengujian**, bukan laporan inspeksi atau penawaran komersial nyata. Jalur utama berakhir dengan pilihan gudang; jalur alternatif sampai PO dapat diperagakan pada assessment baru.

### 1. Gejala dan teknisi

Tempel ke kolom **Gejala**:

```text
Conveyor makanan terasa kasar dan bising setelah high-pressure washdown; ada jejak korosi di sekitar flange. Mesin dihentikan untuk inspeksi.
```

| Kolom | Input |
|---|---|
| Kode unit pada marking/BOM | `RHP PSF20CR` |
| Jumlah hasil inspeksi | `2` |
| Nama teknisi | `Rifqi — teknisi demo` |

Klik analisis, baca bukti, lalu centang konfirmasi marking/BOM untuk **skenario demo** sebelum membuat WO exact. Jangan menuliskan dugaan penyebab sebagai diagnosis yang sudah terbukti.

### 2. Penawaran vendor lewat WhatsApp

Klik RFQ WhatsApp, lalu balas pesan RFQ terbaru dari nomor **082178830078** dengan seluruh form ini:

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

Sistem mendukung waktu relatif tersebut dan mengubahnya menjadi tanggal/jam berdasarkan **waktu pesan diterima**, sehingga contoh tidak kedaluwarsa karena disalin pada hari lain. ETA delapan jam sudah mencakup persiapan lima jam; keduanya tidak dijumlahkan kembali. Untuk waktu absolut, ganti nilainya dengan tanggal lengkap, misalnya `29 Oktober 2026 10:00 WIB`, dan sesuaikan agar masih di masa depan.

Total tagihan untuk dua unit = **Rp1.100.000**. Stok 10 adalah jumlah tersedia, bukan jumlah yang dibeli. Tunggu status **Penawaran diterima**, lalu perbarui perbandingan. Dengan fixture baru dan balasan segera, gudang exact diperkirakan lebih unggul karena lebih cepat; gunakan hasil aktual di layar, bukan angka total hafalan. Jika demo memakai simulator, lewati input WhatsApp ini.

### 3. Asumsi biaya

Isi kolom **Asumsi IDR per satu unit dolar publikasi** dengan:

```text
16000
```

Centang pengakuan benchmark/konversi simulasi, lalu klik **Hitung / perbarui perbandingan**. Tarif sumber dikunci pada 3.332 unit `$` publikasi/jam; pemetaan di atas menghasilkan **Rp53.312.000/jam untuk skenario**, bukan tarif aktual pabrik. Belum ada kolom input langsung tarif downtime Rp/jam. Instalasi 1 jam, restart 1 jam, dan tenaga pemulihan Rp250.000 diisi sistem sebagai asumsi demo.

### 4. Opsional: alternatif sampai PO demo

Untuk tetap memiliki hasil exact sekaligus hasil alternatif, klik **Analisis dengan AI dan bukti OEM** lagi untuk membuat assessment baru dengan input awal yang sama. Pada assessment baru, lakukan review kandidat sebelum keputusan final. Tidak perlu reset seluruh demo.

| Kolom | Input |
|---|---|
| Reviewer | `Rifqi — reviewer demo` |
| Antarmuka, beban, putaran dan fit diperiksa | Centang untuk simulasi |
| Suhu dan duty cycle cocok | Centang untuk simulasi |
| Tim higiene menyetujui penggunaan pada posisi ini | Centang untuk simulasi |

Tempel ke **Dasar keputusan**:

```text
SIMULASI pengujian alur aplikasi: pemeriksaan antarmuka, beban, putaran, fit, suhu, duty cycle, dan higiene diasumsikan lulus untuk fixture demo. Ini bukan hasil inspeksi atau persetujuan engineering aset nyata; kecocokan PSF20/LP99 tetap perlu diverifikasi sebelum penggunaan nyata.
```

Klik **Catat persetujuan engineering**, centang konfirmasi skenario, lalu **Cari sumber kandidat yang disetujui**. Sistem memakai kode `RHP PSF20/LP99` untuk WO kandidat secara otomatis; tunggu `identified` dan cari gudang. Pilih **Ambil penawaran vendor simulasi**, gunakan input biaya 16000, hitung perbandingan, lalu konfirmasi opsi vendor yang layak sesuai hasil layar untuk menghasilkan PO demo. Biaya downtime tidak masuk tagihan PO.

Jika ingin menguji WhatsApp pada cabang kandidat, ganti hanya baris kode pada form menjadi `Merek dan nomor kode : RHP PSF20/LP99` dan gunakan jalur WhatsApp saja pada run tersebut. Balasan exact PSF20CR tidak boleh dipakai sebagai penawaran kandidat.

**Batas:** stok/harga/ETA/operasi simulasi; ISO mata uang benchmark tidak diketahui dan pemetaan rupiah bukan kurs nyata; tidak ada prediksi umur bearing atau tanggal kegagalan. Provider aktif 9router; Vertex project `hackathon-primestep-16` menunggu credential.
