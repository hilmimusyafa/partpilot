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

Untuk WhatsApp, isi tanggal lengkap dengan tahun, jam, dan zona waktu; contoh `29 Oktober 2026 10:00 WIB`. Form dapat dikirim bertahap. Koreksi hanya memperbarui kolom yang disebutkan; informasi waktu yang belum lengkap akan diminta kembali, bukan ditebak.

**Batas:** stok/harga/ETA/operasi simulasi; ISO mata uang benchmark tidak diketahui dan pemetaan rupiah bukan kurs nyata; tidak ada prediksi umur bearing atau tanggal kegagalan. Provider aktif 9router; Vertex project `hackathon-primestep-16` menunggu credential.
