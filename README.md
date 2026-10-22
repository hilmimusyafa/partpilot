# PartPilot ⚙️
> **Autonomous Industrial MRO Spare Parts Procurement & Fulfillment Multi-Agent System**  
> *Dari Laporan Kerusakan Mesin (Work Order) hingga Penerbitan Purchase Order (PO) yang Disetujui Manusia — Cepat, Akurat, Tanpa Ghost Stock.*

[![Hackathon](https://img.shields.io/badge/Hackathon-ITB%202026%20Agentic%20AI-0052CC?style=for-the-badge)](https://partpilot.rifqisetiawan.my.id)
[![Team](https://img.shields.io/badge/Team-Five%20Agent-FF8800?style=for-the-badge)](#10-susunan-tim--pembagian-kontribusi-anggota)
[![Status](https://img.shields.io/badge/Build-Frozen%20Submission-00875A?style=for-the-badge)](#12-informasi-versi-beku-freeze-version)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2015-black?style=flat&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016-336791?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Google Gemini](https://img.shields.io/badge/Model-Gemini%203.8%20Flash-4285F4?style=flat&logo=google)](https://cloud.google.com/vertex-ai)
[![WhatsApp](https://img.shields.io/badge/Bridge-Baileys%20WhatsApp-25D366?style=flat&logo=whatsapp)](https://github.com/WhiskeySockets/Baileys)

---

## 📌 Akses Cepat Demo & Penilai
- 🌐 **Live Demo URL:** [https://partpilot.rifqisetiawan.my.id](https://partpilot.rifqisetiawan.my.id)
- 🔑 **Akun Demo:** Username: `demo` *(Password runtime tersedia pada file sesi penilaian)*
- 📑 **Dokumentasi Lengkap:**
  - [Buku 1: Masalah dan Solusi](docs/Buku1_PartPilot_Masalah_dan_Solusi.md)
  - [Buku 2: Rancang Bangun Aplikasi & TOR](docs/Buku2_PartPilot_Rancang_Bangun_Aplikasi.md)
  - [Buku 3: Strategi Tim & Pelaksanaan Teknis](docs/Buku3_PartPilot_Strategi_Tim.md)
  - [Panduan Live Deployment & Reset](docs/DEMO_DEPLOYMENT.md)
  - [Panduan Integrasi WhatsApp](docs/WHATSAPP_DEMO.md)

---

## 📑 Daftar Isi
1. [Ringkasan Eksekutif & Latar Belakang Masalah](#1-ringkasan-eksekutif--latar-belakang-masalah)
2. [Arsitektur Multi-Agent & Alur Sistem](#2-arsitektur-multi-agent--alur-sistem)
3. [Fitur Utama & Keunggulan Agentic AI](#3-fitur-utama--keunggulan-agentic-ai)
4. [Skenario Demo & Panduan Pengujian Juri](#4-skenario-demo--panduan-pengujian-juri)
5. [Panduan Instalasi & Menjalankan Sistem](#5-panduan-instalasi--menjalankan-sistem)
6. [Tech Stack & Dependensi](#6-tech-stack--dependensi)
7. [Konfigurasi Lingkungan & Pagar Keamanan](#7-konfigurasi-lingkungan--pagar-keamanan)
8. [Bukti Pengujian & Verifikasi (QA)](#8-bukti-pengujian--verifikasi-qa)
9. [Keterbatasan & Batasan Bagian yang Disimulasikan](#9-keterbatasan--batasan-bagian-yang-disimulasikan)
10. [Susunan Tim & Pembagian Kontribusi Anggota](#10-susunan-tim--pembagian-kontribusi-anggota)
11. [Sumber Daya & Deklarasi Penggunaan AI](#11-sumber-daya--deklarasi-penggunaan-ai)
12. [Informasi Versi Beku (Freeze Version)](#12-informasi-versi-beku-freeze-version)

---

## 1. Ringkasan Eksekutif & Latar Belakang Masalah

### 1.1 Masalah Industri: Biaya Mesin Berhenti (Unplanned Downtime)
Ketika mesin produksi di pabrik, pertambangan, atau pembangkit listrik rusak tiba-tiba (*corrective breakdown*), pabrik tidak hanya menanggung biaya perbaikan mekanis. **Biaya terbesar yang melumpuhkan produktivitas adalah waktu tunggu suku cadang (logistic delay) dan waktu urusan administrasi pengadaan (administrative delay).**

- **Dampak Finansial Global:** Riset Siemens (2024) mencatat bahwa pabrik-pabrik manufaktur skala menengah-besar rata-rata kehilangan **27 jam per bulan** akibat mesin berhenti tidak terencana. Fortune Global 500 kehilangan sekitar **\$1,4 triliun per tahun** (setara 11% dari total pendapatan).
- **Kondisi Riil di Indonesia:** Studi empiris pada dua pembangkit listrik di Indonesia (Purnomo & Triayudi, 2026) mencatat lebih dari **291.000 data material** yang tercatat berulang dengan nama/kode berbeda (*ghost stock*). Di pabrik kemasan PT Dwi Indah, lini produksi Casterline kerap dibiarkan idle hanya karena keterlambatan pengadaan komponen kritis (bearing, seal, motor).
- **Karakteristik Suku Cadang MRO (Maintenance, Repair, & Operations):**
  1. *Nama part tidak seragam:* Satu part memiliki nomor suku cadang OEM, kode vendor lokal, nama sebutan teknisi bengkel ("laher" vs "bearing"), dan dimensi fisik.
  2. *Stok tersembunyi antargudang:* Sistem ERP lama antar cabang sering kali tidak saling mengenali alias suku cadang, menyebabkan manajer membeli barang baru dari luar padahal gudang cabang sebelah memiliki stok melimpah.
  3. *Proses pengadaan lambat & manual:* RFQ (*Request for Quotation*) dikirim satu per satu melalui WhatsApp/email, format balasan vendor acak-acakan, negosiasi berlarut-larut, dan risiko *human-error* tinggi.

### 1.2 Solusi PartPilot
**PartPilot** adalah platform multi-agen otonom cerdas yang mempercepat pemulihan lini manufaktur dari jam-ke-menit:
1. **Mengidentifikasi part** secara multimodal dari bahasa bebas teknisi di lapangan (bahkan ketika kode part aus/tidak terbaca).
2. **Harmonisasi katalog & cek stok multi-gudang** untuk mendeteksi alias part tersembunyi lintas cabang.
3. **Mengirim RFQ dan menawar vendor secara otonom via WhatsApp** dengan batas wewenang yang ketat.
4. **Menghitung total dampak ekonomi** (harga part, ongkir, pajak, durasi pengiriman, hingga nilai *loss of production* mesin).
5. **Menyajikan Meja Keputusan (Human-in-the-Loop)** dan menerbitkan dokumen Purchase Order (PO) PDF siap tanda tangan secara instan.

```
+---------------------------------------------------------------------------------------------------+
| KALIMAT UTAMA KEPADA JURI:                                                                        |
| "Ketika mesin rusak, yang membuat pabrik berhenti lama sering kali bukan waktu memperbaikinya,    |
| melainkan waktu menunggu suku cadangnya. PartPilot mengotomasi pengadaan suku cadang secara       |
| menyeluruh—dari deskripsi teknisi hingga draf PO siap tanda tangan—dengan manusia tetap memegang   |
| kendali penuh atas keputusan pengeluaran uang."                                                   |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Arsitektur Multi-Agent & Alur Sistem

### 2.1 Filosofi Inti: *"Angka dari Kode, Kata-Kata dari Model"*
PartPilot menerapkan prinsip keamanan mutlak untuk aplikasi industrial enterprise:
- **Model AI (Google Gemini 3.8 Flash)** bertugas mengekstraksi fakta dari bahasa natural teknisi, menyusun pertanyaan klarifikasi cerdas, dan membaca teks penawaran vendor yang tidak terstruktur.
- **Kode Deterministik & Validasi PostgreSQL** bertugas menghitung seluruh nominal uang, perbandingan total biaya, batas toleransi negosiasi (-10%), ketersediaan stok fisik gudang, dan penerbitan nomor PO resmi.
- **Model AI dilarang keras:** memanipulasi angka keuangan, mengakses kredensial/DSN database secara langsung, atau mengeksekusi pembelian tanpa persetujuan manusia.

### 2.2 Diagram Alur Sistem End-to-End

```mermaid
flowchart TD
    subgraph S1["Fase 1: Work Order & Identifikasi Part"]
        A["Teknisi Lapor Kerusakan<br/>(Deskripsi fisik/dimensi mesin)"] --> B{"Mesin Pengecek:<br/>Rule-First Matcher"}
        B -- "Deskripsi Lengkap" --> D["Standarisasi Part ID<br/>(e.g. NTN 6200LLU)"]
        B -- "Gejala/Dimensi Ambigu" --> C["Agen Klarifikasi AI<br/>(Gemini 3.8 Flash)"]
        C -->|Tanya Dimensi/Seal| A1["Teknisi Jawab Klarifikasi<br/>(Human-in-the-Loop 1)"]
        A1 --> D
    end

    subgraph S2["Fase 2: Multi-Warehouse Sourcing"]
        D --> E{"Cek Stok Gudang Asal<br/>(SYN-WH-01)"}
        E -- "Stok Cukup (>= Qty)" --> F["Rekomendasi Pemakaian Sendiri<br/>(Zero Lead Time)"]
        E -- "Stok Kurang" --> G["Agen Pemeriksa Lintas Gudang<br/>(WH02 - WH05)"]
        G --> H{"Ditemukan Alias Part?<br/>(e.g. G2-BRG-017 di WH02)"}
        H -- "Ada Stok di Cabang" --> I["Rencana Transfer Antargudang"]
        H -- "Semua Gudang Kurang" --> J["Pemicu Pengadaan Vendor Eksternal"]
    end

    subgraph S3["Fase 3: Pengadaan Vendor Otonom (WhatsApp / Simulator)"]
        J --> K["Agen Dispatcher RFQ<br/>(Broadcast via WhatsApp Baileys / Sim)"]
        K --> L["Vendor Terima Pesan RFQ & Format Penawaran"]
        L --> M["Agen Pembaca & Ekstraksi Quote<br/>(Zero-Hallucination Parser)"]
        M --> N{"Evaluasi Kuotasi Lengkap?"}
        N -- "Data Hilang/Salah" --> O["Follow-Up Spesifik ke Vendor<br/>(Maks 3 kali)"]
        O --> L
        N -- "Lengkap" --> P["Agen Negosiasi Harga Otonom<br/>(1-Round Target: 90% Benchmark)"]
        P --> Q["Vendor Setuju / Menolak Penawaran"]
    end

    subgraph S4["Fase 4: Meja Keputusan & Penerbitan Dokumen"]
        F --> R["Engine Komparasi Ekonomi<br/>(Harga + Ongkir + Pajak + Downtime Lost)"]
        I --> R
        Q --> R
        R --> S["Meja Keputusan Manajer<br/>(Rekomendasi Total Biaya Terendah)"]
        S --> T{"Persetujuan Manajer<br/>(Human-in-the-Loop 2)"}
        T -- "Pilih Transfer Gudang" --> U["Catat Mutasi Demo<br/>(Tanpa PO Eksternal)"]
        T -- "Pilih Vendor Eksternal" --> V["Penerbitan Dokumen PO Resmi<br/>(Generate PDF PT PartPilot)"]
    end
```

### 2.3 Rincian Agen & Komponen Sistem
| Nama Agen / Komponen | Peran Utama | Teknologi / Engine | Titik Kendali / Guardrail |
|---|---|---|---|
| **WO Identification Agent** | Mengubah laporan teknisi (bahasa bebas, nomor aus, dimensi diameter/tebal/seal) menjadi entitas part standar. | Rule-First Engine + Google Gemini 3.8 Flash (Low Effort) | Tidak menebak part jika informasi kunci (diameter/seal) belum ada. |
| **Clarification Agent** | Mengajukan pertanyaan interaktif terarah kepada teknisi ketika deskripsi part kurang spesifik. | Gemini 3.8 Flash via API Gateway | Hanya menanyakan parameter teknis yang hilang (brand, ukuran poros, jenis tutup). |
| **Multi-Warehouse Matcher** | Memetakan alias lokal (*disparate SKU*) dari 5 gudang berbeda ke satu entitas part standar (*Single Source of Truth*). | PostgreSQL 16 exact index lookup + scoped notes | Gudang tanpa mapping menghasilkan status `knowledge_unavailable`, bukan stok kosong palsu. |
| **Vendor Sourcing Agent** | Menghubungi vendor secara serentak, mengirimkan format RFQ resmi, dan menangani percakapan multi-turn. | Node.js WhatsApp Baileys bridge + Deterministic Simulator | Idempotent dispatch; tidak ada spam atau pesan ganda saat restart sistem. |
| **Quote Parser Agent** | Membaca balasan pesan WhatsApp dalam format bebas (teks santai, singkatan "45rb/pcs", format form) ke objek `Quote` terstruktur. | Prompt Extraction + Validasi Skema Pydantic v2 | Angka tidak boleh diasumsikan 0 jika tidak ada; wajib bernilai non-negatif. |
| **Price Negotiation Agent** | Melakukan negosiasi harga 1 putaran secara otonom dengan target harga 90% dari penawaran terbaik sementara. | Logika Deterministik Keuangan (`floor_IDR`) + Messaging | Maksimal 1 counteroffer per vendor per run; tidak membocorkan struktur biaya pesaing. |
| **Economic Decision Engine** | Menghitung total dampak biaya masa depan: part + ongkir + pajak + recovery labor + nilai kerugian produksi per jam. | Formula Finansial Baku (Python Decimal Engine) | Memisahkan biaya internal pabrik dari nilai nominal invoice PO vendor. |
| **PO Document Agent** | Menerbitkan dokumen legal Purchase Order (PDF) lengkap dengan nomor unik, barcode dummy, dan syarat ketentuan. | ReportLab 4.4.9 Python PDF Engine | PO berstatus immutable; hanya terbit setelah tombol persetujuan manajer ditekan. |

### 2.4 Dua Titik Kendali Manusia (Human-in-the-Loop)
1. **Titik Kendali 1 — Verifikasi & Klarifikasi Teknisi (`/technician/clarification`):**  
   Ketika deskripsi fisik ambigu, AI tidak mengambil keputusan tebakan liar. Teknisi wajib memilih/mengonfirmasi spesifikasi teknis part sebelum proses pencarian stok dimulai.
2. **Titik Kendali 2 — Meja Keputusan Manajer (`/manager/decision`):**  
   AI hanya berfungsi sebagai penasihat cerdas (*decision support system*) yang mengurutkan opsi berdasarkan total efisiensi biaya. Pembelian tidak akan pernah dieksekusi secara liar. Manajer pengadaan memegang wewenang tunggal untuk menyetujui vendor dan menandatangani PO.

---

## 3. Fitur Utama & Keunggulan Agentic AI

- 🔍 **Pemahaman Deskripsi Fisik & Bahasa Bebas Teknisi:**  
  Mampu mengenali bearing dari deskripsi awam (misal: *"bearing conveyor terasa kasar saat diputar, diameter luar 30mm, karet dua sisi"*) tanpa memerlukan kode OEM resmi.
- 🏢 **Eliminasi Ghost Stock Lintas 5 Gudang Cabang:**  
  Menemukan bahwa bearing NTN 6200LLU di Gudang Utama (WH01) yang habis ternyata tersimpan di Gudang 2 (WH02) dengan nama lokal `G2-BRG-017`, menghemat 100% biaya pembelian baru.
- 📱 **Integrasi WhatsApp Web Asli (Dual-Mode: Live WhatsApp & Simulator):**  
  Menghubungkan langsung ke vendor melalui nomor WhatsApp nyata menggunakan arsitektur Baileys Web Socket bridge dengan proteksi allowlist nomor kontak untuk demo aman.
- 💬 **Toleran Percakapan Natural & Validasi Form WhatsApp:**  
  Mendukung balasan vendor berupa form isian standar maupun chat santai. Jika ada kolom vital yang terlewat (misal: ongkos kirim belum disebut), agen otomatis meminta ulang hanya kolom yang hilang.
- 🤝 **Algoritma Negosiasi Otonom Satu Putaran Terkendali:**  
  Menawar harga vendor secara sopan dan terukur berdasarkan patokan 90% dari opsi terefisien tanpa risiko tawar-menawar tanpa batas.
- ⏱️ **Kalkulasi Biaya Terpadu dengan Biaya Downtime Mesin:**  
  Memperhitungkan kerugian lini produksi per jam (downtime cost) sehingga vendor dengan harga sedikit lebih tinggi tetapi pengiriman 2 jam bisa direkomendasikan di atas vendor murah yang butuh waktu 3 hari.
- 📄 **Penerbitan Dokumen PO (PDF) Sekali Klik:**  
  Menghasilkan dokumen Purchase Order format standar enterprise dengan snapshot data yang terkunci (*immutable snapshot*).

---

## 4. Skenario Demo & Panduan Pengujian Juri

Aplikasi telah dilengkapi dengan **4 Preset Demo Terpadu** pada antarmuka teknisi (`/technician/`), yang dirancang khusus untuk memperagakan seluruh kemampuan sistem:

| Preset Demo | Masukan Deskripsi & Parameter | Gudang Asal | Hasil & Perilaku Sistem yang Ditunjukkan |
|---|---|:---:|---|
| **1. Stok Sendiri** *(Fulfill from Origin)* | *"Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca."* <br>*(Qty: 1 pcs)* | `SYN-WH-01` | **Stok Asal Cukup (Tersedia 4 pcs).** Sistem langsung menyarankan pengambilan dari gudang sendiri. Tidak ada RFQ vendor yang dikirim, lead time 0 jam. |
| **2. Nama Berbeda di Gudang 2** *(Cross-Warehouse Alias)* | *"Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca."* <br>*(Qty: 6 pcs)* | `SYN-WH-01` | **Stok Asal Tidak Cukup (Hanya ada 4 pcs).** Agen mendeteksi Gudang WH02 memiliki 8 pcs dengan kode lokal `G2-BRG-017`. Sistem merekomendasikan transfer internal, mencegah pengadaan ganda. |
| **3. Perbandingan Vendor & Nego** *(Multi-Vendor Sourcing)* | *"Bearing NTN ukuran 10x30x9 mm, karet rapat dua sisi. Kode tidak terbaca."* <br>*(Qty: 12 pcs)* | `SYN-WH-01` | **Kedua Gudang Tidak Mencukupi (Syarat 1 sumber utuh).** Agen menghubungi vendor eksternal, membandingkan kuotasi, mengeksekusi negosiasi 1 putaran, dan menampilkan komparasi harga + ongkir + downtime. |
| **4. Demo Lengkap End-to-End** *(Clarification + All Features)* | *"Saat inspeksi sebelum shift, bearing conveyor terasa kasar saat diputar. Diameter luar 30 mm. Kode tidak terbaca."* <br>*(Qty: 6 pcs)* | `SYN-WH-01` | **Alur Paling Lengkap:** <br>1. AI mendeteksi spesifikasi belum lengkap dan mengajukan 3 pertanyaan klarifikasi (Merk, Dimensi 10x30x9, Tutup Karet). <br>2. Teknisi mengisi klarifikasi. <br>3. Identifikasi berhasil -> Masuk Meja Keputusan Manajer. <br>4. Evaluasi opsi transfer vs vendor negosiasi. <br>5. Manajer menyetujui -> Terbit Dokumen PDF PO resmi. |

### Panduan Langkah Pengujian Cepat untuk Juri:
1. Buka [https://partpilot.rifqisetiawan.my.id](https://partpilot.rifqisetiawan.my.id).
2. Pilih peran **Teknisi** (`/technician`).
3. Klik tombol preset **"Demo lengkap"** pada bagian bawah form.
4. Klik tombol **"Cari Suku Cadang"**. Sistem mendeteksi bahwa informasi belum lengkap dan membuka halaman klarifikasi AI (`/technician/clarification`).
5. Jawab pertanyaan AI: Brand `NTN`, Dimensi `10x30x9 mm`, Seal `Karet rapat dua sisi (LLU/2RS)`. Kirim klarifikasi.
6. Masuk ke halaman **Manajer Pengadaan** (`/manager`). Buka work order yang baru saja berstatus `Teridentifikasi`.
7. Sistem secara otomatis menjalankan pencarian ketersediaan stok 5 gudang dan menghubungi vendor via WhatsApp / Simulator.
8. Masuk ke halaman **Meja Keputusan** (`/manager/decision`). Amati perbandingan komparatif antara opsi transfer gudang WH02 vs opsi vendor yang sudah dinegosiasikan.
9. Pilih salah satu penawaran vendor yang direkomendasikan, lalu klik **"Setujui & Buat Purchase Order"**.
10. Unduh dan buka dokumen PDF Purchase Order resmi yang diterbitkan oleh sistem.

---

## 5. Panduan Instalasi & Menjalankan Sistem

### 5.1 Prasyarat Sistem
- **Node.js:** Versi 18 LTS atau 20+
- **Python:** Versi 3.12+
- **PostgreSQL:** Versi 16
- **Docker & Docker Compose:** Versi v2.20+ (opsional untuk containerized deployment)

### 5.2 Opsi A: Menjalankan Monorepo Secara Lokal

#### 1. Clone Repository & Setup Frontend:
```bash
git clone https://github.com/hilmimusyafa/partpilot.git
cd partpilot

# Install dependencies frontend monorepo
npm install

# Jalankan server frontend Next.js (port 3000)
npm run dev:web
```
Buka browser pada: `http://localhost:3000`.

#### 2. Setup Environment & Backend Python:
```bash
# Setup virtual environment Python
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependensi backend
pip install -e .
pip install pytest

# Setup database PostgreSQL lokal dan jalankan skema:
psql -U postgres -d postgres -c "CREATE DATABASE partpilot_demo;"
psql -U postgres -d partpilot_demo -f backend/db/001_schema.sql
psql -U postgres -d partpilot_demo -f backend/db/009_bearing_lookup.sql
psql -U postgres -d partpilot_demo -f backend/db/seed/009_bearing_mvp_synth.sql
psql -U postgres -d partpilot_demo -f backend/db/010_work_order_identification.sql
psql -U postgres -d partpilot_demo -f backend/db/011_work_order_production_context.sql
psql -U postgres -d partpilot_demo -f backend/db/012_procurement_demo.sql
psql -U postgres -d partpilot_demo -f backend/db/013_demo_console.sql
psql -U postgres -d partpilot_demo -f backend/db/014_whatsapp.sql
psql -U postgres -d partpilot_demo -f backend/db/015_purchase_orders.sql
psql -U postgres -d partpilot_demo -f backend/db/016_negotiation_policy.sql
psql -U postgres -d partpilot_demo -f backend/db/017_five_warehouse_demo.sql
psql -U postgres -d partpilot_demo -f backend/db/018_dashboard_revisions.sql
psql -U postgres -d partpilot_demo -f backend/db/019_plain_vendor_replies.sql

# Jalankan FastAPI Backend server (port 8026 / 18080)
export DATABASE_URL="postgresql://postgres:password@127.0.0.1:5432/partpilot_demo"
uvicorn backend.wo.app:app --host 127.0.0.1 --port 18080 --reload
```

#### 3. Menjalankan Worker Background:
```bash
# Worker untuk proses identifikasi AI & background matching:
python scripts/run_wo_worker.py --max-ticks 120 --poll-seconds 1
```

---

### 5.3 Opsi B: Menjalankan via Docker Compose (Arsitektur Production)
Untuk deployment lengkap satu perintah seperti di VPS:
```bash
cd deploy
docker compose -f compose.yaml build
docker compose -f compose.yaml up -d
```
Layanan yang dijalankan:
- `db`: PostgreSQL 16 Alpine terisolasi
- `api`: FastAPI REST API Server (port 18080)
- `worker`: Python Supervised Worker untuk pemrosesan identifikasi & matching AI
- `whatsapp`: Node.js Baileys WebSocket WhatsApp Bridge (port 18081)
- `chat-worker`: Worker percakapan dan parsing penawaran WhatsApp

---

## 6. Tech Stack & Dependensi

| Layer | Komponen / Library | Fungsi & Rasionalitas |
|---|---|---|
| **AI / Model** | **Google Gemini 3.8 Flash** | Ekstraksi entitas bahasa bebas, klarifikasi interaktif, dan parsing chat penawaran vendor dengan latensi rendah (<5 detik). |
| **Agent Workflow** | **Google ADK & Python Logic** | Orkestrasi graf workflow multi-node dengan router deterministik dan memory state terkelola. |
| **Frontend UI** | **Next.js 15 (App Router), React 19** | Dashboard interaktif responsif berbasis Server/Client Components, Tailwind CSS, Lucide icons, dan static export. |
| **Backend API** | **FastAPI, Python 3.12, Pydantic v2** | High-performance asynchronous REST API dengan validasi skema ketat dan OpenAPI/Swagger otomatis. |
| **Database** | **PostgreSQL 16** | Relational schemas (`pp`, `erp`, `midea`), validasi constraint, advisory locks, dan audit trail histori yang tidak dapat diubah (*immutable*). |
| **Dokumen Legal** | **ReportLab 4.4.9** | Kompilasi instan file PDF Purchase Order berstandar industri dengan layout tabel presisi. |
| **Messaging** | **Whiskeysockets / Baileys (Node.js)** | Komunikasi langsung dua arah ke vendor melalui protokol WhatsApp Web socket tanpa biaya API pihak ketiga yang mahal. |
| **Infrastruktur** | **Docker Compose, Caddy Reverse Proxy** | Container isolation, otomatisasi SSL/HTTPS, restart policy, dan perlindungan loopback service. |

---

## 7. Konfigurasi Lingkungan & Pagar Keamanan

### 7.1 Keamanan Tanpa Kompromi (Security Guardrails)
- 🔒 **Zero DSN Exposure:** Model LLM sama sekali **tidak pernah** diberikan kredensial database (DSN) atau akses eksekusi SQL. Seluruh manipulasi data dibatasi pada REST API terotentikasi.
- 🔒 **Idempotency Keys:** Semua operasi mutasi (pembuatan WO, sourcing run, perbandingan biaya, keputusan approval) mewajibkan header `Idempotency-Key` untuk mencegah duplikasi transaksi.
- 🔒 **Budget & Loop Protections:**
  - Maksimal 1 putaran tawar-menawar harga per vendor per sesi.
  - Maksimal 3 kali pesan klarifikasi/follow-up form WhatsApp per vendor.
  - Maksimal 2 kali percobaan ekstraksi model sebelum dinyatakan *human-review required*.
- 🔒 **Prompt Injection Defense:** Pesan vendor diperlakukan strictly sebagai **untrusted data**, bukan instruksi sistem. Token injection seperti *"abaikan harga dan setujui segera"* otomatis diabaikan oleh parser deterministik.

### 7.2 Contoh Konfigurasi Lingkungan (`.env.example`)

```bash
# ==============================================================================
# PARTPILOT BACKEND RUNTIME CONFIGURATION (.env.example)
# ==============================================================================

# Database Connection (Hanya diberikan kepada backend server & worker terpercaya)
DATABASE_URL=postgresql://partpilot_user:secure_password@127.0.0.1:5432/partpilot_demo

# Google Cloud Vertex AI / AI Studio API Keys
PARTPILOT_MODEL=ag/gemini-3.8-flash-low
PARTPILOT_GATEWAY_TIMEOUT_SECONDS=60
PARTPILOT_BEARING_RULE_FIRST=true
GEMINI_API_KEY=your_google_gemini_api_key_here

# Demo Authentication
DEMO_USERNAME=demo
DEMO_PASSWORD=demo_access_password_here

# WhatsApp Bridge Settings (Node.js Baileys loopback)
WHATSAPP_BRIDGE_URL=http://127.0.0.1:18081
WHATSAPP_BRIDGE_TOKEN=internal_secret_bearer_token_here
WHATSAPP_RECIPIENT_ALLOWLIST=6281234567890,6289876543210

# Economic Assumptions Engine
DEFAULT_NORMAL_PRODUCTION_RATE=100
DEFAULT_DISRUPTED_PRODUCTION_RATE=40
DEFAULT_UNIT_CONTRIBUTION_MARGIN=500000
```

---

## 8. Bukti Pengujian & Verifikasi (QA)

Pengujian dilakukan secara bertingkat untuk menjamin keandalan sistem industri:

### 8.1 Pengujian Backend Terisolasi (Automated Isolated PostgreSQL Checks)
Pengujian regresi backend dijalankan menggunakan cluster PostgreSQL 16 sementara yang dibuat dinamis pada socket lokal:
```bash
# Menjalankan seluruh pengujian unit & integrasi terisolasi
.venv/bin/python scripts/run_isolated_checks.py
```
- **Hasil Uji:** **145 passed**, 1 deselected (live model gateway call sengaja dipisahkan agar dapat dijalankan tanpa internet).
- **Cakupan Pengujian:**
  - `test_description_matching.py`: Ekstraksi deskripsi bebas & penanganan ambiguitas (364 baris uji).
  - `test_five_warehouse_demo.py`: Konsistensi data 5 gudang dan alias mapping `G2-BRG-017` (132 baris uji).
  - `test_negotiation.py`: Kebijakan negosiasi 90% benchmark dan batas 1 putaran (93 baris uji).
  - `test_purchase_orders.py`: Integritas snapshot PO, immutabilitas, dan render PDF ReportLab (176 baris uji).
  - `test_wa_routing.py` & `test_wa_plain_replies.py`: Penanganan chat WhatsApp polos, penolakan stok, dan parsing form (251 baris uji).

### 8.2 Pengujian Frontend & Browser Smoke Test (Playwright)
```bash
npm run lint:web
node frontend-web/tests/ranking.cjs
node frontend-web/tests/demo-ui-smoke.cjs
```
- Verifikasi sorting presisi desimal tanpa rounding error IEEE-754.
- Verifikasi alur UI responsif, form stepper, popup persetujuan mutasi, modal pembuatan PO, dan status offline gateway.

---

## 9. Keterbatasan & Batasan Bagian yang Disimulasikan

Demi transparansi penuh sesuai Pedoman TOR Hackathon ITB 2026:

| Fitur / Komponen | Status Implementasi | Penjelasan Batasan Demo |
|---|---|---|
| **Ekstraksi & Klarifikasi AI** | **Nyata (Real)** | Menggunakan panggilan langsung ke model Google Gemini 3.8 Flash via API. |
| **Koneksi WhatsApp** | **Nyata (Real)** | Menggunakan private Baileys WhatsApp Web bridge. Pesan RFQ benar-benar terkirim dan diterima di nomor HP peserta uji coba yang terdaftar di allowlist. |
| **Simulator Vendor Fallback** | **Simulasi (Simulated)** | Disediakan 5 persona vendor simulasi (SIM-ENOUGH, SIM-SHORT, SIM-REFUSE, SIM-REVISE, SIM-SILENT) untuk demonstrasi otomatis tanpa tergantung jeda ketik manusia. |
| **Katalog Stok & Gudang** | **Data Sintetis Terstandar** | Menggunakan data sintetis 5 gudang (`SYN-WH-01` s/d `SYN-WH-05`) dengan fokus suku cadang bearing industrial. |
| **Kalkulasi Kerugian Mesin** | **Model Sintetis** | Parameter biaya downtime (Rp500.000/unit output margin, 100 unit/jam) adalah model parameter simulasi berbasis skenario buku teks MRO. |
| **Penerbitan PO** | **Nyata (Real Generated)** | File PDF PO benar-benar digenerate secara on-the-fly dan dapat diunduh. Namun, mutasi saldo bank atau pengiriman PO ke sistem logistik ERP perusahaan nyata tidak dieksekusi. |

---

## 10. Susunan Tim & Pembagian Kontribusi Anggota

### Tim: **Five Agent**

| Foto / Nama | Peran Utama | Tanggung Jawab & Kontribusi Teknis | Wilayah Kode Utama |
|---|---|---|---|
| **Lukman** | **Hustler (Team Lead & QA)** | Koordinasi proyek, penyusunan Product Requirements Document (PRD), perancangan skenario evaluasi MRO, pengujian end-to-end, dan dokumentasi repositori. | `docs/`, `README.md`, `tests/` |
| **Hilmi** | **Hacker (Backend & Server)** | Arsitektur backend FastAPI, perancangan skema database PostgreSQL 16 terisolasi, pembuatan engine PDF ReportLab, dan manajemen deployment server. | `backend/wo/`, `backend/db/`, `backend/purchase_orders/`, `deploy/` |
| **Azziz** | **Hacker (AI Agent Architecture)** | Perancangan workflow agen, integrasi model Google Gemini 3.8 Flash via Google ADK / API Gateway, algoritma pencocokan part, dan prompt engineering ekstraksi kuotasi. | `backend/wo/matching.py`, `backend/whatsapp/extraction.py`, `backend/procurement/` |
| **Rifqi** | **Hacker (Frontend & Data)** | Pembangunan antarmuka web Next.js 15, sinkronisasi state real-time Meja Keputusan, integrasi API client terotentikasi, dan skrip seed data sintetis. | `frontend-web/src/`, `scripts/` |
| **Alifa** | **Hipster (UI/UX Design)** | Perancangan desain sistem industri, wireframe antarmuka teknisi & manajer, pembuatan aset grafis / logo PartPilot, dan penyusunan slide presentasi seleksi. | Desain Figma, UI Styling Tailwind, Slide Pitch Deck |

---

## 11. Sumber Daya & Deklarasi Penggunaan AI

Sesuai dengan ketentuan transparansi AI pada **TOR Hackathon ITB 2026**:

### 11.1 Penggunaan Asisten AI
- **Claude (Anthropic):** Digunakan selama fase ideasi pra-lomba untuk membantu menyusun kerangka analisis masalah industri, formulasi matematika downtime MRO, dan dokumen perencanaan awal (`Buku 1`, `Buku 2`, `Buku 3`).
- **Antigravity CLI / AI Pair Programmer (DeepMind):** Digunakan selama kompetisi untuk membantu implementasi kode, refactoring fungsi SQL PostgreSQL, integrasi skema Pydantic v2, dan penulisan berkas verifikasi otomatis.
- **Google Gemini 3.8 Flash:** Digunakan sebagai model AI operasional inti di dalam sistem runtime PartPilot untuk tugas klasifikasi part, ekstraksi teks, dan agen interaktif.

### 11.2 Sumber Pustaka & Referensi
- *Siemens True Cost of Downtime Report (2024)* — Rujukan statistik kerugian downtime mesin global.
- *Purnomo, A., & Triayudi, A. (2026)* — Analisis data duplikasi material suku cadang pada industri energi nasional.
- *Google Agent Development Kit (ADK)* — Pola arsitektur workflow multi-agent berbasis graf.
- *WhiskeySockets / Baileys* — Pustaka open-source komunikasi protokol WhatsApp Web WebSocket.
- *ReportLab PDF Library* — Pustaka open-source pembuatan dokumen PDF di Python.

---

## 12. Informasi Versi Beku (Freeze Version)

- **Hackathon:** Hackathon ITB 2026 - Agentic AI
- **Branch:** `main`
- **Commit Hash:** `c47d7059aeb6acaf9aef4ef1a800385cb88db836`
- **Waktu Pembekuan:** Kamis, 22 Oktober 2026, 14:47:22 WIB (+07:00)
- **Status Build:** ✅ Production Deployed & Verified at [https://partpilot.rifqisetiawan.my.id](https://partpilot.rifqisetiawan.my.id)

---
*PartPilot — Empowering Industry with Responsible Agentic AI.*
