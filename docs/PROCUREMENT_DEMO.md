# PartPilot — backend simulator procurement

Scope: bearing sintetis, satu sumber memenuhi seluruh jumlah, lima scope gudang, lima vendor simulasi. Runtime tetap FastAPI + worker Python + PostgreSQL. Tidak menambah Hermes/LangChain sebagai runtime baru.

## Perilaku

1. Buat dan submit WO memakai API yang sudah ada. Worker memanggil gateway untuk ekstraksi fakta; backend memeriksa bukti teks dan menentukan kecocokan. Kekurangan label meminta klarifikasi. Kode tambahan seperti C3 yang belum didukung masuk review. Konflik jumlah harus dijawab angka positif oleh manusia; raw submission tetap tersimpan.
2. Setelah WO `identified`, buat sourcing run. Stok asal cukup menghasilkan `fulfilled_source`; vendor tidak dihubungi dan mesin tidak dianggap selesai diperbaiki.
3. Jika kurang, evaluasi empat gudang lain secara scoped. WH02 memiliki alias G2-BRG-017 untuk NTN 6200LLU. Aturan WH03–05 belum tersedia: hasilnya `knowledge_unavailable`, bukan stok kosong. Stok tidak dijumlahkan antar sumber. Satuan selain `Nos` belum didukung.
4. Panggil advance untuk menjalankan simulator. Semua RFQ dikumpulkan sebelum menentukan target nego. Maksimal satu counteroffer per run/vendor; vendor termurah tidak harus dinego. Penawaran awal vendor yang menolak tetap dapat dipilih.
5. Kirim asumsi jadwal pemulihan dan ekonomi untuk comparison. Backend mengambil harga/ongkir/pajak dari penawaran tersimpan, bukan dari request manajer. Data tidak lengkap tidak diperingkat. Peringkat hanya informasi; tidak otomatis memilih.
6. Manager mengirim pilihan. Database memeriksa eligibility, expiry, penawaran terbaru, stok dan identitas barang terkini. Pilihan hanya mencatat intent; tidak mengurangi stok, membuat transfer, membeli, atau menyelesaikan perbaikan.

## API untuk dashboard

Semua endpoint baru berawalan `/api/v1/demo`. JSON dan nilai uang/jumlah memakai decimal string. POST create/comparison/decision wajib header `Idempotency-Key` yang stabil untuk retry request yang sama. Gunakan key baru untuk operasi yang berbeda. Unknown fields ditolak.

| Method/path | Body / hasil |
| --- | --- |
| POST `/sourcing-runs` | `{ "session_id": "WO_ID", "expected_version": 3 }`; ganti versi sesuai GET WO |
| GET `/sourcing-runs/{id}` | Status sumber, availability, lima vendor, exchanges, versi terbaru, keputusan |
| POST `/sourcing-runs/{id}/advance` | `{}`; pemrosesan simulator yang bounded dan aman diulang |
| POST `/sourcing-runs/{id}/comparisons` | `expected_version`, `production`, `options`; lihat kontrak OpenAPI dan contoh tes |
| GET `/comparisons/{id}` | Snapshot historis immutable, peringkat, opsi tidak layak beserta alasannya |
| POST `/comparisons/{id}/decision` | `{ "expected_version": 1, "option_id": "vendor:SIM-REVISE", "acknowledgment": "demo_only" }` |

HTTP 409 berarti versi/sumber berubah atau pilihan tidak layak; refresh dan buat comparison baru. HTTP 422 berarti input tidak valid. POST yang diulang dengan key/body sama mengembalikan hasil awal; GET membaca kondisi terkini. GET comparison hanya memperbarui indikator expiry, bukan memvalidasi ulang stok; validasi stok dilakukan saat memilih.

Satu versi WO hanya boleh memiliki satu sourcing run. Membuat ulang run yang sama memakai key berbeda ditolak `409 run_already_exists`; gunakan key awal atau GET run yang sudah ada.

Kontrak mesin yang dihasilkan aplikasi tersedia di `GET /api/v1/openapi.json`. `tests/codex/test_procurement.py::comparison_input` adalah contoh lengkap struktur jadwal/asumsi. Semua sumber harus memakai waktu awal dan horizon yang sama. Waktu awal comparison harus dekat waktu server (maksimal 60 detik); jangan menggunakan contoh tanggal lama. Instalasi/restart tidak boleh mendahului ETA.

## Skenario sintetis

| Vendor | Stok | Respons |
| --- | ---: | --- |
| SIM-ENOUGH | 100 | Quote awal, harga Rp150.000/unit, ongkir Rp20.000, ETA 6 jam |
| SIM-SHORT | 2 | Quote tetapi tidak memenuhi WO 9 unit |
| SIM-REFUSE | 100 | Harga Rp190.000, ongkir Rp30.000, ETA 8 jam; counteroffer ditolak |
| SIM-REVISE | 100 | Harga awal Rp180.000, ongkir Rp25.000, ETA 5 jam; menerima satu harga counteroffer |
| SIM-SILENT | tidak diketahui | `no_response`, tidak berubah menjadi `no_stock` |

Semua quote demo memakai pajak eksplisit 0, persiapan 1 jam, masa berlaku 24 jam. ETA dihitung dari waktu run. Respons diam disimulasikan langsung sebagai hasil timeout; MVP tidak menunggu berjam-jam.

Asumsi transfer/gudang juga sintetis: replenishment Rp150.000/unit; ongkir transfer Rp40.000; ETA transfer 2 jam; gudang asal ongkir/ETA 0. Ini bukan harga ERP atau kebijakan operasional. Nilai dan asal asumsi tercatat dalam snapshot. Biaya donor tambahan harus dinyatakan; `unknown` menghasilkan incomplete. `not_applicable` adalah pernyataan eksplisit pemakai, bukan fakta otomatis.

Contoh uji WO 9 unit dari WH02: stok asal 8, WH01 10. Setelah nego, SIM-REVISE memiliki harga unit 149444.44. Dengan asumsi pengujian 10 jam dampak, produksi normal 100/jam, aktual 40/jam, kontribusi 30/unit, fraksi dipulihkan 25%, dan biaya tambahan 1000, total opsi adalah 1384499.96. Angka ini hanya contoh fixture, bukan rekomendasi pembelian.

## Menjalankan dan menguji di VPS

Gunakan Python 3.12, PostgreSQL 16, dan dependencies pyproject (termasuk PyYAML). Dari root PartPilot:

```sh
# Tidak membaca DSN database utama. Membuat PG16 sementara milik penguji,
# memakai socket lokal, lalu membersihkannya.
.venv/bin/python scripts/run_isolated_checks.py

# Tambahkan uji nyata gateway. Hanya dua variabel gateway di-load.
.venv/bin/python scripts/run_isolated_checks.py \
  --gateway-env /home/rifqisetiawan/.config/partpilot/gateway-codex.env
```

Tanpa `--gateway-env`, tes live gateway sengaja deselected; tes simulator tidak menggunakan LLM. Uji live benar-benar memakai model dan gagal jika gateway tidak tersedia. API harness memakai proses Python baru tiap request untuk menguji persistence setelah restart. Jalankan sebagai pengguna biasa, bukan root (initdb menolak root).

Untuk menjalankan layanan manual, siapkan database DEMO terpisah dan DSN di environment backend. Urutan skema di test harness: `001_schema.sql`, `009_bearing_lookup.sql`, seed `009_bearing_mvp_synth.sql`, `010_work_order_identification.sql`, `011_work_order_production_context.sql`, lalu tambahan `012_procurement_demo.sql`. Jangan menjalankan ulang seed ke database pelanggan. Backend juga membutuhkan referensi company/site/line/station/machine yang konsisten; test harness menyediakan fixture tersebut.

```sh
# DATABASE_URL disiapkan operator, tidak ditempel ke dokumen/repo/chat.
.venv/bin/python -m uvicorn backend.wo.app:app --host 127.0.0.1 --port 8026

# Terminal terpisah; bounded, berhenti setelah 120 tick.
.venv/bin/python scripts/run_wo_worker.py \
  --gateway-env /home/rifqisetiawan/.config/partpilot/gateway-codex.env \
  --max-ticks 120 --poll-seconds 1
```

Penambahan file kode tidak menerapkan migration ke database utama atau me-restart service. Pengujian hanya memakai database sementara. Endpoint demo belum memiliki autentikasi/otorisasi manajer; bind localhost atau akses melalui SSH tunnel. `demo_only` bukan bukti identitas manajer. Jangan mengekspos endpoint ini langsung ke internet.

## Batas keamanan dan migrasi berikutnya

- Seluruh tulisan procurement baru lewat fungsi validasi `pp.demo_*` dan tercatat di audit immutable. Berikan service role SELECT yang diperlukan dan EXECUTE fungsi terkait, bukan INSERT/UPDATE/DELETE tabel procurement. Migration mencabut hak PUBLIC dan tidak membuat/grant role otomatis. Akun runtime harus berbeda dari pemilik migration agar pencabutan hak bermakna. Tes memakai owner database sementara; pembuktian role production masih pekerjaan deployment.
- Kalkulator deterministik backend adalah komponen terpercaya. Database memvalidasi sumber/jumlah/identitas/versi dan pilihan, tetapi tidak menghitung ulang seluruh ekonomi. LLM tidak menerima DSN, hak SQL, atau alat memilih/approve.
- Modul WO lama masih melakukan DML melalui repository/worker terpercaya, belum seluruhnya dikonversi ke SECURITY DEFINER. Jangan mengklaim seluruh backend telah memenuhi isolasi role production. Migrasi guard/role WO dan audit kegagalan lengkap diperlukan sebelum data pelanggan.
- Audit procurement mencatat transisi sukses dan reservasi pesan. Request yang ditolak tidak ditulis sebagai event bisnis dalam transaksi yang di-rollback; perlu telemetry request terpisah untuk audit semua percobaan.
- Transport ada di `backend/procurement/transport.py`; simulator di modul terpisah. ID event dan payload disimpan sebelum pengiriman; retry simulator memakai event yang sama. Untuk WhatsApp nyata perlu adapter dedupe/receipt, webhook, timer, retry dengan backoff, dan status pengiriman tidak pasti. Jangan menganggap jaringan eksternal memberikan exactly-once hanya karena outbox unik.
- Tidak ada WhatsApp/email nyata, UI chat, frontend manajer baru, eksekusi transfer/PO, auth multi-tenant atau deployment GCP pada perubahan ini. Tidak ada perubahan ke worker pengembangan Jarvis/Hermes.
- Availability adalah pembacaan scoped per gudang, bukan reservasi atau snapshot transaksi lintas seluruh gudang. Pemilihan memvalidasi lagi sumber tunggal di dalam transaksi. Untuk skala besar perlu snapshot konsisten dan pencarian lintas gudang terindeks; katalog yang terpotong tetap ambiguous.
- Catatan warehouse dan delapan seed asli dipertahankan. Data latihan, hasil model dan konfigurasi gateway tidak boleh dipublikasikan tanpa pemeriksaan terpisah.
