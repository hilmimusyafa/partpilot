# Data nyata dan cara kerja AI PartPilot

Demo memakai kasus pelanggan yang diterbitkan produsen, katalog part, dan panduan kerusakan OEM sebagai bukti. AI menelusuri bukti tersebut untuk menyusun hipotesis, langkah pemeriksaan, dan usulan part. Identitas aset demo, stok, harga, serta waktu pemulihan tetap diberi asal data simulasi. Keputusan teknis dan pengadaan memiliki tahap konfirmasi tersendiri.

## Sepuluh record bukti di PostgreSQL

Record berikut diingest ke `pp.maintenance_evidence`. Tautan menuju sumber asli; locator menunjukkan bagian yang mendukung record. Riwayat teknis dan ekonomi SS-E-2003 adalah dua ekstrak dari satu kasus, bukan dua kejadian atau dua pelanggan.

| ID record dan jenis | Nama serta sumber | Locator dan pemakaian |
|---|---|---|
| `history:NSK-SS-E-2003` — `published_case` | [NSK Food Production Conveyor](https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/food-production-conveyor/) | Introduction, Key Facts, Value Proposals. Preseden utama: kegagalan berulang setelah washdown; uji 10 bearing selama 12 bulan tanpa kegagalan yang dilaporkan. |
| `catalog:PSF20CR` — `catalog_part` | [RHP PSF20CR, katalog NSK Self-Lube](https://www.nsk.com/content/dam/nsk-marketing/projects-completed/literature/product-brochures/self-lube-bearings_product-brochure/en_self-lube-bearings_product-brochure/preview-pdf_self-lube-bearings_product-brochure_en/EN_Self_Lube_Bearings_SLB_Product-Brochure_low-res.pdf) | Halaman cetak 100, 104–105. Unit flange lengkap yang diusulkan sebagai permintaan exact demo. |
| `catalog:PSF20/LP99` — `catalog_part` | [RHP PSF20/LP99, katalog NSK Self-Lube](https://www.nsk.com/content/dam/nsk-marketing/projects-completed/literature/product-brochures/self-lube-bearings_product-brochure/en_self-lube-bearings_product-brochure/preview-pdf_self-lube-bearings_product-brochure_en/EN_Self_Lube_Bearings_SLB_Product-Brochure_low-res.pdf) | Halaman cetak 123–125, 128–129. Kandidat engineering; belum disetujui sebagai pengganti. |
| `troubleshooting:rust_and_corrosion` — `troubleshooting` | [NSK Rust and Corrosion](https://www.nsk.com/am-en/tools-resources/bearings/troubleshooting/damage-by-type/rust-and-corrosion/) | Damage Condition, Possible Causes, Countermeasures. Panduan kemungkinan penyebab dan pemeriksaan umum. |
| `economics:NSK-SS-E-2003` — `economic_case` | [NSK Food Production Conveyor](https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/food-production-conveyor/) | Cost Saving Breakdown. Biaya tahunan historis; tidak tersedia jumlah jam untuk menentukan tarif per jam. |
| `economics:NSK-SS-E-2054` — `economic_case` | [NSK Main Make-Up Conveyor](https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/main-make-up-conveyor/) | Cost Saving Breakdown, baris lost production. Benchmark eksternal terpilih: 3.332 unit `$` publikasi per jam. |
| `economics:NSK-SS-E-2061` — `economic_case` | [NSK Cutter Line](https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/cutter-line/) | Cost Saving Breakdown. Referensi sekunder; tarif mencakup tiga lini dan total tabel tidak konsisten. Bukan default. |
| `economics:NSK-SS-E-2034` — `economic_case` | [NSK Confectionary Washing Process](https://www.nsk.com/am-en/tools-resources/bearings/aip/success-stories-overview/confectionary-washing-process/) | Cost Saving Breakdown. Referensi sekunder; pengali kejadian/periode kurang jelas dan aplikasinya berbeda. Bukan default. |
| `economics:PERMA-BOTTLING-WASHDOWN` — `economic_case` | [perma Beverage Bottling Facility](https://www.permausa.com/learn-connect/case-studies/beverage-bottling-facility-eliminates-conveyor-bearing-failures-with-perma-flex) | The Challenge, paragraf terakhir. Angka sampai `$15.000/jam` adalah batas atas untuk kasus berbeda. Bukan default. |
| `economics:NSK-FOOD-BROCHURE-P15` — `economic_case` | [NSK Food and Beverage](https://www.nsk.com/content/dam/nsk-marketing/projects-completed/literature/sector-brochures/food---beverage_sector-brochure/en_food_beverage_sector-brochure/preview-pdf_food_beverage_sector-brochure_en/EN_Food-and-Beverage_FB_Sector-Brochure_low-res.pdf) | Halaman cetak/PDF 15, Key Facts dan Breakdown of cost savings. Kasus conveyor tujuh jalur; biaya tahunan dan durasi tersedia, tarif per jam tidak dinyatakan. Bukan default. |

Kasus tersebut merupakan laporan OEM tentang pelanggan anonim. Itu **bukan ekspor CMMS, histori aset pengguna, atau verifikasi independen**. Tanggal kejadian, SKU historis, dan bidang lain yang tidak diketahui tetap `null`. Tanggal pengambilan sumber tidak dijadikan tanggal kejadian. Catatan mutu sumber, termasuk selisih satu dolar pada rincian SS-E-2003, dipertahankan.

Nama **RHP PSF20CR** dan **RHP PSF20/LP99** berasal dari katalog, bukan BOM kasus SS-E-2003. Keduanya unit flange lengkap. Insert `F-UC204/LP99` saja tidak dianggap unit yang sama. Kesamaan dimensi tidak membuktikan kecocokan beban, kecepatan, suhu, washdown, atau higiene. Bukti terpilih belum menetapkan persetujuan NSF H1/kontak pangan untuk LP99.

## Dari sumber ke agen

Ekstrak terkurasi dari paket `PartPilot-Kasus-Nyata` dan `PartPilot-Downtime-Data-Asli` disertakan dalam `backend/maintenance/evidence_pack`. Loader memuat JSON yang ditinjau, bukan seluruh halaman web atau fixture stok. `scripts/seed_maintenance_evidence.py` memasukkannya ke PostgreSQL.

Setiap record menyimpan fakta, URL, locator, waktu pengambilan, hash SHA-256 salinan sumber, serta hash isi record. Pengulangan ingest identik tidak membuat duplikat. Perubahan fakta dengan ID yang sama ditolak; koreksi harus menjadi versi bukti baru. Hash menjaga keterlacakan salinan, bukan membuktikan kebenaran klaim OEM.

Agen memakai **native function calling**: model memilih nama fungsi dan argumennya, aplikasi menjalankan fungsi yang diizinkan, lalu hasilnya dikembalikan ke model. Fungsinya hanya membaca:

| Fungsi | Tugas sebenarnya |
|---|---|
| `retrieve_cases` | Mencari kasus OEM dan referensi ekonomi yang diizinkan dalam record database. Tidak mencari WO lokal atau menjelajah web bebas. |
| `read_catalog_part` | Membaca bukti katalog SKU lengkap; exact dan kandidat dibaca terpisah. |
| `read_troubleshooting` | Membaca panduan kemungkinan penyebab dan pemeriksaan kerusakan. Tidak memastikan diagnosis. |

Loop dibatasi **4 giliran model, 8 panggilan fungsi, dan anggaran aplikasi 85 detik**; setiap panggilan model diberi timeout 20 detik. Tidak ada tool untuk SQL bebas, mengubah stok, membuat WO, membeli part, atau mengirim pesan. Sebelum hasil diterima, aplikasi memeriksa struktur jawaban, penggunaan tool yang diwajibkan, dan bahwa semua ID kutipan benar-benar sudah diperoleh. Hasil tidak valid atau model gagal menghasilkan `needs_review`/`failed` dengan draft kosong, tanpa diagnosis cadangan buatan.

Permintaan, hasil penilaian, dan status disimpan di `pp.maintenance_assessment`. Argumen, hasil, bukti, urutan, serta durasi panggilan disimpan di `pp.maintenance_tool_trace`. Jejak tool tidak bisa ditulis ulang; reasoning internal/signature provider tidak ditampilkan sebagai jejak publik.

**Bukti uji nyata:** pada PostgreSQL terisolasi, 10 record diingest dan model memilih empat panggilan: kasus, katalog PSF20CR, troubleshooting, dan katalog PSF20/LP99. Dua giliran model selesai dalam **14,22 detik** dengan JSON valid, kutipan, draft exact yang belum dikonfirmasi, dan kandidat yang belum layak dibeli. Hasil dibaca ulang dari koneksi database baru. Lihat [catatan pengujian](verification-results.md). Ini satu hasil uji, bukan jaminan latensi. Enam belas tes maintenance, termasuk penyimpanan dan pembatasan hak akses PostgreSQL, juga lulus.

Provider aktif mengikuti pilihan pengguna: **9router**, dengan konfigurasi `ag/gemini-3.8-flash-low` pada uji tersebut. Adapter Vertex AI tersedia sebagai opsi; dukungan kode dan konfigurasi proyek tidak berarti koneksi live Vertex sudah terbukti bekerja.

## Dari usulan ke pengadaan

Teknisi membaca hipotesis dan pemeriksaan yang masih diperlukan, lalu mengonfirmasi kode unit lengkap, jumlah, dan pemeriksaan aktual sebelum WO dibuat. Status penilaian `completed` berarti proses AI selesai, bukan part sudah cocok. PSF20/LP99 memerlukan persetujuan engineering dan higiene untuk antarmuka/beban/kecepatan, suhu/duty, serta persyaratan higiene. Kandidat tidak boleh otomatis menggantikan exact agar cocok dengan stok.

Setelah konfirmasi, aplikasi menjalankan alur **gudang sendiri → gudang lain → vendor** berdasarkan identitas lengkap, jumlah, ketersediaan, kelengkapan penawaran, dan kebijakan. Pemeriksaan sumber, kelayakan, urutan proses, serta pilihan final memakai aturan dan validasi database. Ini bukan keputusan bebas agen maintenance. Aset, stok gudang, harga penawaran fixture, dan waktu pemulihan ilustratif tetap merupakan data simulasi; balasan vendor yang benar-benar diterima disimpan dengan asal transportnya dan tidak dijadikan histori kasus OEM.

Worker identifikasi WO untuk lokasi `FOOD-SITE` membaca record katalog RHP yang dipilih dari database bukti yang sama. Worker memvalidasi cakupan perusahaan/gudang, identitas unit lengkap, hash ekstrak, serta rujukan katalog OEM. Jika bukti hilang atau tidak valid, proses berhenti pada `knowledge_unavailable`; tidak memakai catatan penamaan NTN lama. Referensi WO mempertahankan URL/hash publikasi dan hash versi ekstrak. LLM hanya boleh mengekstrak fakta identitas yang didukung teks permintaan teknisi, sehingga isi katalog alternatif tidak berubah menjadi permintaan penggantian otomatis.

Pencarian ketersediaan unit RHP memakai pembaca katalog terverifikasi yang sama, lalu mencocokkan identitas lengkap dengan record inventori di setiap gudang yang diizinkan. Provenance katalog dan jumlah stok merupakan dua jenis bukti berbeda: katalog OEM menjelaskan identitas part; inventori simulasi menentukan jumlah yang tersedia. Katalog yang tidak tersedia menghentikan evaluasi scope tersebut, bukan diganti dengan catatan umum merek lain. Snapshot perbandingan lama dipertahankan sebagai audit; perbaikan referensi berlaku pada evaluasi baru.

Negosiasi dibatasi kebijakan satu putaran: target dan kelayakan berasal dari aturan serta snapshot perbandingan yang tervalidasi. Pengiriman mengikuti workflow yang diizinkan. **LLM tidak bertindak sebagai negosiator bebas.** Ekstraksi bahasa dari balasan, bila memakai model, tetap berbeda dari kewenangan menetapkan harga atau menyetujui pembelian.

## Perhitungan biaya dan batas maintenance

Kalkulator biaya bersifat deterministik. Mode benchmark mengambil **3.332 `$` publikasi/jam dari SS-E-2054**. ISO mata uang, tahun harga, serta definisi akuntansi kerugian tidak dinyatakan; angka itu bukan tarif IDR dan bukan pengukuran pabrik demo. **8,6 jam pada sumber adalah jumlah tahunan**, bukan lama satu penggantian. Kasus ini tetap terpisah dari histori teknis SS-E-2003.

Pengguna harus mengakui penggunaan benchmark eksternal dan konversi simulasi sebelum membandingkan total IDR. Nilai contoh **16.000 IDR per satu unit mata uang publikasi** adalah pemetaan demo yang dinyatakan eksplisit, bukan kurs nyata, identifikasi USD, atau penyesuaian inflasi. Jadwal produksi terdampak, durasi pemasangan/restart, dan biaya tenaga tambahan juga memiliki label asumsi tersendiri.

Rumusnya: jam produksi terjadwal yang terdampak × 3.332 × pemetaan simulasi, kemudian ditambah biaya pengadaan dan biaya tambahan yang relevan. Kode menolak baris biaya dengan ID atau rujukan bukti duplikat. Namun, anggapan bahwa komponen biaya tidak tumpang tindih masih merupakan asumsi demo, karena cakupan akuntansi tarif OEM tidak dijelaskan. LLM tidak mengerjakan aritmetika, menciptakan throughput/margin, atau memilih tool kalkulator pada flow maintenance ini. Tarif tenaga `$26/jam` dari kasus sumber tidak otomatis dikenakan pada seluruh waktu menunggu part. Hasil adalah estimasi skenario, bukan penghematan pabrik yang sudah tercapai.

Demo membantu menilai gejala, memakai preseden kerusakan berulang, dan menyiapkan tindak lanjut inspeksi. Tidak tersedia model sensor, probabilitas kegagalan, atau **remaining useful life (RUL)**. Rekomendasi memeriksa seal, mencatat hasil, dan memverifikasi kondisi setelah perbaikan tidak menjadikannya sistem predictive maintenance atau pemantauan otomatis.

Semua opsi layak memakai horizon perbandingan yang sama: minimal 48 jam, diperpanjang sampai ETA terlama ditambah pemasangan dan restart. ETA beberapa hari tidak dipotong menjadi biaya 48 jam. API kalkulator yang menerima horizon lebih pendek daripada waktu pulih mengembalikan hasil tidak lengkap dan tidak memasukkannya sebagai total biaya penuh. Jadwal produksi kontinu dan masing-masing satu jam pemasangan/restart tetap asumsi simulasi yang perlu diganti dengan data pabrik saat implementasi nyata.
