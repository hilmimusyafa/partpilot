# PartPilot

PartPilot membantu teknisi dan manajer maintenance mencari spare part dari gudang sendiri, gudang lain, dan vendor. Demo utama memakai conveyor makanan setelah washdown: **gejala → bukti OEM → dugaan penyebab dan pemeriksaan → konfirmasi part/WO → sumber pengadaan → biaya pemulihan → keputusan manajer**.

[Demo conveyor makanan](https://partpilot.rifqisetiawan.my.id/maintenance/) · [Panduan singkat](docs/demo-guide.md) · [Data dan Agentic AI](docs/data-and-agentic-ai.md) · [Hasil pengujian](docs/verification-results.md) · [API maintenance](backend/maintenance/README.md).

## Data asli dan simulasi

PostgreSQL menyimpan **10 record bukti**: satu kasus teknis OEM, dua unit katalog, satu panduan troubleshooting, dan enam ekstrak ekonomi. Kasus teknis utama adalah NSK SS-E-2003; benchmark kerugian produksi berasal dari kasus berbeda, SS-E-2054. URL, halaman/bagian sumber, hash dan tanggal pengambilan dipertahankan; informasi yang tidak dipublikasikan tetap null. Ini riwayat eksternal terpublikasi, bukan histori mesin demo atau CMMS pengguna.

Nama **RHP PSF20CR** dan **RHP PSF20/LP99** berasal dari katalog asli. Penempatan pada aset demo, stok, vendor simulator, harga, ETA, dan jadwal operasi adalah simulasi. PSF20/LP99 memerlukan review engineering dan higiene. Dimensi yang sama tidak cukup untuk menetapkan substitusi.

Benchmark melaporkan **3.332 `$` publikasi/jam**, tanpa ISO mata uang atau tahun harga. Contoh pemetaan **16.000 IDR per unit dolar publikasi** wajib diakui sebagai asumsi demo, bukan kurs nyata. Hasil rupiah adalah estimasi skenario; tidak disebut kerugian terukur atau margin kontribusi pabrik.

## Bagian Agentic AI

Model memilih dan memanggil `retrieve_cases`, `read_catalog_part`, dan `read_troubleshooting`, membaca hasilnya, lalu menyusun hipotesis, pemeriksaan, serta usulan part dengan kutipan. Loop dibatasi empat giliran model, delapan tool calls, dan anggaran 85 detik. Tool trace serta hasil disimpan untuk audit. Model tidak mendapat SQL, credential database, hak menyetujui part, atau hak mengirim pesan pada flow analisis ini.

Identitas, stok, persetujuan alternatif, aritmetika Decimal, negosiasi satu putaran, dan keputusan akhir divalidasi kode/database. Komponen workflow deterministik ini mendukung agen; LLM tidak menjadi negosiator bebas atau kalkulator biaya. Tidak tersedia prediksi umur bearing, probabilitas kegagalan, atau model predictive maintenance.

## Backend dan gateway

FastAPI/PostgreSQL16, worker, frontend static export, dan bridge WhatsApp Baileys dijalankan melalui Docker Compose. VPS tetap menjadi host aplikasi. Modul baru: `backend/maintenance/`, `backend/demo/food.py`, `backend/procurement/benchmark.py`, dan migration020–023.

Provider aktif **9router**, sesuai revisi pengguna, dengan `PARTPILOT_MODEL=ag/gemini-3.8-flash-low`. Native function calling telah diuji. Credential dimuat dari file server-side di luar repository.

Adapter Vertex AI tersedia sebagai opsi:

```dotenv
PARTPILOT_AI_PROVIDER=vertex_ai
GOOGLE_CLOUD_PROJECT=hackathon-primestep-16
GOOGLE_CLOUD_LOCATION=global
PARTPILOT_MODEL=MODEL_ID_VERTEX_DARI_PANITIA
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-credentials.json
```

Ganti placeholder model dengan ID Vertex yang tersedia dan diizinkan panitia. Siapkan ADC dengan izin project/model, mount credential read-only ke API dan worker, lalu uji koneksi sebelum mengganti provider. **Vertex belum diuji live**; tidak ada fallback provider otomatis. Project ID saja tidak cukup untuk autentikasi. Jangan commit key, token, atau sesi WhatsApp.

## Ingestion dan pengujian

Untuk instalasi dedicated demo yang sudah sampai migration019, backup DB lalu jalankan **020, 021, 022, 023** berurutan sebagai owner. Berikan runtime SELECT evidence, INSERT/UPDATE assessment, dan INSERT trace/review/link sesuai kebutuhan. Runtime tidak boleh mengubah bukti immutable.

```bash
python scripts/seed_maintenance_evidence.py --validate-only
# Set MAINTENANCE_SEED_DATABASE_URL secara aman ke dedicated demo DB owner.
python scripts/seed_maintenance_evidence.py
python -m pytest tests/codex -m "not live_gateway" -q
npm ci
npm run build:web
npm run lint:web
```

Seed memvalidasi struktur/provenance paket, menolak perubahan diam-diam pada ID lama, dan idempotent untuk record identik. Runtime memakai ekstrak yang ditinjau; raw capture HTML/PDF berada dalam paket riset terpisah. Integrasi DB membuat cluster PostgreSQL16 sendiri dengan private socket dan membutuhkan Linux `/usr/lib/postgresql/16/bin`. Unit tests portable dapat berjalan di Windows. Test bertanda `live_gateway` dijalankan terpisah setelah credential server dimuat secara aman. Beberapa acceptance test lama menargetkan `src/partpilot/app.py` yang tidak tersedia pada release VPS; hasil bare pytest harus dibaca bersama catatan verifikasi, bukan dianggap seluruhnya lulus.

## WhatsApp dan keputusan

Pengujian saat ini hanya mengizinkan **6282178830078**. `PARTPILOT_WA_RECIPIENTS` di bridge dan `PARTPILOT_WA_ALLOWED_RECIPIENTS` di backend harus sesuai. Backend tanpa allowlist menolak pengiriman. RFQ memerlukan tombol eksplisit; membaca halaman tidak mengirim pesan.

Balasan WhatsApp nyata dipisahkan dari simulator. Keputusan vendor membuat PO **demo**, bukan pembelian aktual; pilihan gudang tidak memindahkan stok. Dalam satu siklus demo sebelum reset, satu assessment hanya boleh punya satu keputusan akhir, termasuk cabang alternatif. Reset mempertahankan evidence dan audit eksternal; pesan yang sudah dikirim tidak ditarik kembali.

## Struktur Monorepo

Repositori ini disusun dengan struktur monorepo untuk memfasilitasi integrasi antarkomponen:
```text
partpilot/
├── docs/                  # Dokumentasi & panduan perancangan sistem
├── frontend-web/          # Dashboard frontend berbasis Next.js (App Router, Tailwind CSS, TypeScript)
├── pnpm-workspace.yaml    # Konfigurasi workspace pnpm
├── package.json           # Monorepo scripts (npm / pnpm)
└── README.md
```

## Memulai Frontend Web

### Menjalankan Development Server:
Dari root repositori:
```bash
npm run dev:web
# atau
pnpm --filter frontend-web dev
```

Atau langsung dari direktori `frontend-web`:
```bash
cd frontend-web
npm run dev
```

Buka [http://localhost:3000](http://localhost:3000) di browser.

### Build Production:
```bash
npm run build:web
```

## Backend dan demo

Backend FastAPI/PostgreSQL ada di `backend/`. Bukti OEM dipisahkan dari operasi simulasi. Lihat `docs/DEMO_DEPLOYMENT.md` untuk provisioning dasar dan reset, serta migration020–023 untuk skenario makanan.
