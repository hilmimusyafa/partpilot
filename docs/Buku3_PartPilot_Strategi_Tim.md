Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

# Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

Oct 21, 2026 · @Azka 

## Ringkasan satu halaman 

**Lima orang, lima wilayah folder, lima awalan branch. Setiap orang vibe coding hanya di folder miliknya, menggabungkan ke** **`main` lewat pull request kecil minimal tiap 2 sampai 3 jam, dan** **`main` harus selalu bisa didemokan.** Konflik merge adalah risiko terbesar tim vibe coding, jadi seluruh buku ini disusun untuk mencegahnya. 

|Anggota|Peran|Wilayah utama|Awalan<br>branch|
|---|---|---|---|
|Azziz|Hacker, agen AI|`server/app/agents/`,<br>`server/app/workflows/`,<br>`server/app/tools/matcher*`|`agen/`|
|Hilmi|Hacker, backend dan<br>server,**penjaga main**|`server/app/`selain di atas, deploy, CI|`be/`|
|Rifqi|Hacker, frontend dan<br>data seed|`web/src/`inti,<br>`scripts/generate_seed.py`,<br>`data/seed/`|`fe/`dan<br>`data/`|
|Alifa|Hipster, desain dan<br>halaman pendukung|Figma, token warna,<br>`web/src/pages/`<br>pendukung, deck, video|`ui/`|
|Lukman|Hustler, ketua, QA dan<br>dokumen|`data/eval/`,<br>`docs/`,<br>`README.md`,<br>papan tugas, kontak panitia|`docs/`dan<br>`qa/`|



Aturan emas: 

1. **Jangan ubah folder orang lain.** Butuh perubahan di sana, buat issue atau minta pemiliknya. 

2. **File kontrak hanya diubah lewat PR kontrak** (skema data dan tipe API), diumumkan di grup sebelum digabung. 

3. **Tarik** **`main` setiap mulai sesi vibe coding** dan sebelum membuat PR. 

4. **PR kecil, sering.** Satu PR satu fitur yang jalan, bukan satu PR raksasa di jam terakhir. 

5. **Catat penggunaan AI** setiap selesai satu tugas (wajib TOR). 

6. **Kalau ragu, tanya grup dalam 15 menit** , jangan biarkan AI menebak kontrak. 

Page 1 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

#### Jadwal kunci (WIB): 

|Waktu|Kejadian|
|---|---|
|Rabu 09.15|Briefing teknis dan stack; cek daftar di Buku 2 Bab<br>9.5|
|Rabu 10.00 sampai 12.00|Pembagian credit; siapkan akun dan proyek|
|**Rabu 13.00**|**Countdown mulai; kode boleh ditulis**|
|Rabu 15.00|Tonggak M0: kontrak dan kerangka jalan|
|Kamis 00.00|Tonggak M3: fase 1 jalan untuk skenario A dan C|
|Kamis 06.00|Tonggak M5: alur penuh skenario B dengan<br>persetujuan|
|**Kamis 09.00**|**Batas fitur; sesudahnya hanya perbaikan dan**<br>**bukti**|
|**Kamis 13.00**|**Pembekuan versi**|
|Kamis 15.00|Semua luaran dan deck seleksi terkumpul|
|Kamis 15.00 sampai 16.00|Pitch seleksi Top 10|
|Jumat 08.15|Deck final, video cadangan, perangkat siap|



## Bab 1. Peran dan Kepemilikan 

**Setiap folder punya satu pemilik dan satu pemeriksa. Pemilik yang menulis (lewat vibe coding), pemeriksa yang menyetujui PR.** Pembagian ini mengikuti peran yang sudah ditulis di profil tim, lalu dipecah sampai level file agar AI masing-masing tidak saling menimpa. 

### 1.1 Peta kepemilikan folder 

|Folder atau file|Pemilik|Pemeriksa|Catatan|
|---|---|---|---|
|||PR||
|`server/app/agents/`|Azziz|Hilmi|Definisi agen dan|
||||instruksinya|
|`server/app/workflows/`|Azziz|Hilmi|Workflow fase 1, 2, 3|



Page 2 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Folder atau file|Pemilik|Pemeriksa<br>PR|Catatan|
|---|---|---|---|
|`server/app/tools/matcher.py`,<br>`tools/normalize.py`|Azziz|Lukman|Pencocok part dan<br>kamus istilah|
|`server/app/tools/`lainnya<br>(<br>`cek_stok`,<br>`hitung_biaya`,<br>`kirim_pesan`,<br>`cek_aturan`,<br>`tulis_log`)|Hilmi|Azziz|Fungsi kode murni<br>yang dipanggil agen|
|`server/app/main.py`,<br>`api/`,<br>`db/`,<br>`adapters/`,<br>`sim/`|Hilmi|Azziz|API, basis data,<br>simulator vendor,<br>penjadwal|
|`server/app/domain/`|Hilmi|Azziz dan<br>Rifqi|**File kontrak**(skema,<br>status, aturan)|
|`server/pyproject.toml`,<br>`uv.lock`|Hilmi||Hanya Hilmi yang<br>menambah paket<br>Python|
|`server/tests/`|pemilik<br>modul yang<br>diuji|Hilmi|Uji ikut modulnya|
|`web/src/api/`|Rifqi|Hilmi|**File kontrak**sisi web<br>(tipe dan klien API)|
|`web/src/`inti: layout, router,<br>komponen inti, halaman Form, Daftar<br>Kasus, Detail Kasus, Persetujuan|Rifqi|Alifa||
|`web/src/pages/`pendukung: Kotak<br>Masuk Vendor, Log, Bukti Uji,<br>Dashboard|Alifa|Rifqi|Memakai komponen<br>inti milik Rifqi|
|`web/src/styles/`, token warna, aset|Alifa|Rifqi|Dari palet Buku 2 Bab<br>8.4|
|`web/package.json`,<br>`package-`<br>`lock.json`|Rifqi||Hanya Rifqi yang<br>menambah paket web|
|`scripts/generate_seed.py`,<br>`data/seed/`|Rifqi|Lukman|Lukman memeriksa<br>kewajaran isi katalog|
|`data/eval/`,<br>`scripts/run_eval.py`|Lukman|Azziz|Set uji dibuat orang<br>yang tidak menyetel<br>pencocok|



Page 3 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Folder atau file|Pemilik|Pemeriksa<br>PR|Catatan|
|---|---|---|---|
|`docs/`,<br>`README.md`|Lukman|semua|Bukti uji, catatan<br>sumber dan AI|
|`AGENTS.md`|Hilmi|semua|File konteks untuk<br>semua AI coding (Bab<br>4)|
|`Dockerfile`,<br>`.github/`,<br>`.env.example`,<br>`.gitignore`|Hilmi|Azziz|Deploy dan CI|
|Deck, video, Figma (di luar repo)|Alifa|Lukman|Ekspor PDF deck<br>disimpan juga di<br>`docs/`|



### 1.2 Tanggung jawab di luar kode 

|Anggota|Selain kode, juga memegang|
|---|---|
|Azziz|Menjelaskan sisi agen ke mentor dan juri;<br>menjawab pertanyaan teknis agen saat tanya jawab|
|Hilmi|Penjaga<br>`main`(menggabung, menjalankan uji<br>asap); laptop dan akun demo; deploy Cloud Run|
|Rifqi|Operator demo (tangan di keyboard saat demo<br>langsung); menjaga tampilan stabil|
|Alifa|Wireframe Figma 2 jam pertama; deck seleksi dan<br>final; rekaman dan penyuntingan video cadangan|
|Lukman|Ketua dan penghubung panitia; papan tugas dan<br>pengatur waktu; pertanyaan untuk mentor;<br>pembicara utama pitch; pemeriksa akhir luaran|



### 1.3 Pasangan cadangan 

Bila satu orang tidur, sakit, atau macet, pasangannya yang melanjutkan. Karena itu pasangan wajib saling tahu status pekerjaan masing-masing. 

|Pasangan|Saling menggantikan di|
|---|---|
|Azziz dan Hilmi|Seluruh<br>`server/`|



Page 4 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Pasangan|Saling menggantikan di|
|---|---|
|Rifqi dan Alifa|Seluruh<br>`web/`|
|Lukman dan Alifa|Dokumen, deck, video|
|Lukman dan Rifqi|Data seed dan set uji (kecuali Lukman tidak boleh<br>menyetel pencocok)|



## Bab 2. Setup GitHub 

**Satu repo privat, satu papan tugas, delapan milestone sesuai tonggak Buku 2, dan CI ringan yang memeriksa setiap PR. Repo kosong dan akun boleh disiapkan sebelum countdown; isi kode baru masuk setelah Rabu 13.00.** Semua langkah di bawah dikerjakan Hilmi (teknis) dan Lukman (papan dan milestone). 

### 2.1 Buat repo dan undang anggota 

Perintah memakai GitHub CLI ( `gh` ). Pasang dulu: https://cli.github.com, lalu `gh auth login` . 

```
# Dijalankan Hilmi
```

```
gh repo create partpilot --private --description "PartPilot: agen AI
pengadaan suku cadang (Agentic AI Hackathon 2026)"
```

```
# Undang anggota (ganti dengan username GitHub masing-masing)
gh api -X PUT repos/USERNAME_HILMI/partpilot/collaborators/USERNAME_AZZIZ -f
permission=push
```

```
gh api -X PUT repos/USERNAME_HILMI/partpilot/collaborators/USERNAME_RIFQI -f
permission=push
```

```
gh api -X PUT repos/USERNAME_HILMI/partpilot/collaborators/USERNAME_ALIFA -f
permission=push
```

```
gh api -X PUT repos/USERNAME_HILMI/partpilot/collaborators/USERNAME_LUKMAN -f
permission=maintain
```

Akses panitia dan juri diberikan saat pengumpulan (izin `pull` saja), sesuai TOR bagian 9. 

### 2.2 Lindungi `main` 

Pengaturan yang diinginkan (Settings, Rules atau Branches): 

- Tidak boleh push langsung ke `main` ; wajib lewat pull request. 

- Minimal 1 persetujuan dari pemeriksa (lihat Bab 1.1). 

- CI harus hijau sebelum merge. 

Page 5 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

Larang force push dan hapus branch `main` . 

Catatan jujur: perlindungan branch untuk **repo privat** butuh akun GitHub berbayar atau GitHub Pro (gratis lewat GitHub Student Developer Pack). Bila tidak tersedia, pakai aturan tim: **hanya Hilmi yang menekan tombol merge** , dan semua orang memasang pengingat di AGENTS.md agar AI tidak pernah menjalankan `git push origin main` . 

### 2.3 Label 

```
gh label create "area:agen" --color 7C3AED
gh label create "area:be" --color 1E2A5A
gh label create "area:fe" --color 3B5BDB
gh label create "area:ui" --color DB2777
gh label create "area:data" --color 0E7490
gh label create "area:docs" --color 4B5563
gh label create "P0" --color B91C1C
gh label create "P1" --color D97706
gh label create "kontrak" --color 92400E --description "Mengubah skema atau
tipe API bersama"
gh label create "terblokir" --color 000000
```

### 2.4 Milestone 

Satu milestone per tonggak Buku 2 Bab 10.3. Buat lewat halaman Issues, Milestones, atau perintah berikut (ganti `OWNER` ): 

```
for m in "M0 Kontrak" "M1 Data" "M2 Pencocok part" "M3 Fase 1" "M4 Fase 2"
"M5 Kendali" "M6 Rapi dan demo" "M7 Bukti dan beku"; do
  gh api repos/OWNER/partpilot/milestones -f title="$m"
done
```

### 2.5 Papan tugas (GitHub Projects) 

Buat satu Project bertampilan Board dengan kolom: **Siap dikerjakan** , **Sedang dikerjakan** , **Review** , **Selesai** , **Terblokir** . Tambahkan field `Pemilik` dan `Milestone` . Lukman memegang papan ini dan memeriksanya setiap standup. Aturan: satu orang paling banyak dua kartu di "Sedang dikerjakan". 

### 2.6 File `.github/` yang dibuat setelah countdown 

**`CODEOWNERS`** mengikuti tabel Bab 1.1, agar pemeriksa otomatis diminta saat PR dibuat. Contoh isi: 

Page 6 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

```
# Aturan umum dulu, yang spesifik di bawah (baris terakhir yang cocok yang
berlaku)
/server/                  @USERNAME_HILMI
/web/                     @USERNAME_RIFQI @USERNAME_ALIFA
/server/app/agents/       @USERNAME_AZZIZ
/server/app/workflows/    @USERNAME_AZZIZ
/server/app/domain/       @USERNAME_HILMI @USERNAME_AZZIZ @USERNAME_RIFQI
/web/src/api/             @USERNAME_RIFQI @USERNAME_HILMI
/data/eval/               @USERNAME_LUKMAN
/docs/                    @USERNAME_LUKMAN
```

#### **`pull_request_template.md`** : 

```
## Apa yang berubah
## Cara mengecek
## Tangkapan layar (bila menyentuh tampilan)
```

- `## Bantuan AI` 

```
Alat: ...  Bagian yang dibantu: ...
```

```
## Checklist
```

- `[ ] Sudah menarik main terbaru sebelum PR` 

- `[ ] Hanya mengubah folder milik sendiri (atau sudah izin pemilik)` 

- `[ ] Tidak ada API key, token, atau .env` 

- `[ ] Bila menyentuh alur agen: skenario A, B, C dicoba` 

- `[ ] Bila mengubah kontrak: label `kontrak` dan sudah diumumkan di grup` 

#### **CI ringan** ( `.github/workflows/ci.yml` ) yang berjalan di setiap PR, cukup tiga pekerjaan: 

|Pekerjaan|Langkah|Gagal bila|
|---|---|---|
|server|pasang uv,<br>`uv sync`,<br>`uv run ruff check`,<br>`uv`|ada galat lint atau uji gagal|
||`run pytest -q`||
|web|`npm ci`,<br>`npm run build`|build TypeScript gagal|
|rahasia|aksi gitleaks|ada pola API key atau<br>token|



CI **tidak** memanggil model Gemini, supaya cepat, gratis, dan tidak butuh rahasia di GitHub. Uji yang memanggil model dijalankan di laptop (Buku 2 Bab 11). 

Page 7 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

## Bab 3. Strategi Branch 

**Tim memakai pola trunk-based:** **`main` adalah satu-satunya branch panjang, semua pekerjaan di branch pendek yang hidup paling lama 3 jam lalu digabung lewat PR dengan squash merge.** Branch panjang yang baru digabung di malam hari adalah resep konflik besar, apalagi kalau kodenya ditulis AI. 



<!-- Start of picture text -->
Branch pendek keluar dari main dan kembali dalam hitungan jam<br>Pola branch tim, Rabu 13.00 sampai Kamis 13.00; jarak tidak sesuai skala waktu<br>Kamis 09.00 batas fitur<br>agen/ agen/fase-1 agen/fase-2 :<br>be/ be/kontrak be/api-kasus be/simulator :<br>fe/data/ fe/kerangka fe/persetujuan '<br>qa/ docs/ ga/set-uji :<br>main —_.-2 1 —20-0-» 0-5 —0-0-_____><br>Ujung kanan setiap branch = satu PR digabung (titik biru di main) tag versi-beku<br>: Kamis 13.00<br><!-- End of picture text -->

Pola branch tim · contoh 13 branch pendek, satu tag versi beku 

Setiap orang bekerja di jalurnya sendiri dan kembali ke `main` berkali-kali. Garis putus amber adalah batas fitur; setelah itu hanya perbaikan bug, bukti uji, dan dokumen yang boleh masuk. 

### 3.1 Penamaan branch 

Format: `<awalan>/<topik-pendek>` , huruf kecil, pakai tanda hubung. 

|Awalan|Pemilik|Contoh|
|---|---|---|
|`agen/`|Azziz|`agen/matcher`,<br>`agen/fase-1`,<br>`agen/fase-2`,<br>`agen/negosiasi`|
|`be/`|Hilmi|`be/kontrak`,<br>`be/db-seed-loader`,<br>`be/api-kasus`,<br>`be/simulator`,<br>`be/deploy`|
|`fe/`|Rifqi|`fe/kerangka`,<br>`fe/form-wo`,|
|||`fe/detail-kasus`,<br>`fe/persetujuan`|
|`data/`|Rifqi|`data/seed`|



Page 8 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Awalan|Pemilik|Contoh|
|---|---|---|
|`ui/`|Alifa|`ui/token-warna`,<br>`ui/kotak-masuk`,<br>`ui/log`,<br>`ui/bukti-uji`|
|`qa/`|Lukman|`qa/set-uji`,<br>`qa/skenario`|
|`docs/`|Lukman|`docs/readme`,<br>`docs/bukti-uji`,<br>`docs/sumber-ai`|
|`kontrak/`|Hilmi (atas permintaan siapa pun)|`kontrak/tambah-field-quote`|
|`hotfix/`|Siapa pun, hanya setelah pembekuan<br>dan atas izin PIC teknis|`hotfix/jeda-tidak-jalan`|



### 3.2 Siklus kerja satu branch (perintah siap tempel) 

```
# 1. Mulai dari main terbaru
git switch main && git pull
```

```
# 2. Buat branch baru
git switch -c agen/fase-1
```

```
# 3. Vibe coding, lalu commit kecil setiap ada yang jalan
git add -A && git commit -m "tambah node cek_stok di fase 1"
```

```
# 4. Sebelum PR, ambil perubahan main terbaru ke branch ini
git fetch origin && git rebase origin/main
```

```
# 5. Kirim dan buat PR
git push -u origin agen/fase-1
gh pr create --fill --base main
# 6. Setelah digabung, bersihkan
git switch main && git pull && git branch -d agen/fase-1
```

Bila `git rebase` menimbulkan konflik dan terasa membingungkan, batalkan dengan `git rebase --abort` lalu pakai `git merge origin/main` sebagai gantinya. Jangan pernah memakai `git push --force` ke branch orang lain. 

Page 9 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 3.3 Aturan merge 

|Aturan|Isi|
|---|---|
|Cara merge|**Squash and merge**: satu PR menjadi satu commit di<br>`main`, riwayat rapi dan mudah dibatalkan|
|Siapa yang merge|Hilmi sebagai penjaga<br>`main`; bila Hilmi tidur, Azziz|
|Syarat|CI hijau, disetujui pemeriksa (Bab 1.1), checklist PR<br>dicentang|
|Ukuran|Ideal di bawah 400 baris berubah. PR lebih besar<br>dipecah, kecuali kerangka awal|
|Setelah merge alur agen|Penjaga<br>`main`menjalankan uji asap (Bab 7.3) dalam<br>10 menit|
|Bila<br>`main`rusak|Langsung<br>`git revert`commit penyebab, baru<br>diperbaiki di branch baru. Jangan memperbaiki<br>langsung di<br>`main`|



### 3.4 File kontrak dan file kunci paket 

Dua jenis file paling sering memicu konflik dan bug diam-diam: 

|Jenis|File|Prosedur|
|---|---|---|
|Kontrak<br>data|`server/app/domain/`(skema, status),<br>`web/src/api/`(tipe)|Perubahan hanya lewat branch<br>`kontrak/`, berlabel<br>`kontrak`,<br>diumumkan di grup, disetujui Azziz,<br>Hilmi, dan Rifqi. Server dan web<br>diperbarui di PR yang sama atau<br>berurutan dalam 30 menit|
|Kunci<br>paket|`server/uv.lock`,<br>`web/package-`<br>`lock.json`|Hanya Hilmi (server) dan Rifqi<br>(web) yang menambah paket.<br>Anggota lain meminta lewat grup; AI<br>dilarang menjalankan<br>`uv add`atau<br>`npm install <paket>`di laptop<br>orang lain|



Kontrak dibuat **paling awal** (tonggak M0, Rabu 13.00 sampai 15.00), berdasar skema Buku 2 Bab 4.3 dan contoh JSON Bab 7.2. Setelah itu frontend dan backend bisa bekerja paralel. 

Page 10 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 3.5 Mencegah dan menangani konflik 

Pencegahan: 

- Pembagian folder di Bab 1.1 adalah pagar utama. 

- File bersama yang tak terhindarkan ( `server/app/main.py` untuk mendaftarkan router, `web/src/App.tsx` untuk rute) hanya diubah pemiliknya. Pihak lain cukup membuat 

- modul baru, lalu meminta pemilik mendaftarkannya. 

- Instruksikan AI agar tidak "merapikan" atau mengganti format file di luar tugas. Perubahan format massal membuat konflik di seluruh file. 

Penanganan: 

1. Konflik di folder sendiri: selesaikan sendiri, boleh dibantu AI, lalu jalankan uji. 

2. Konflik di folder orang lain: **jangan diselesaikan sendiri** . Panggil pemiliknya, selesaikan berdua. 

3. Konflik di file kontrak: berhenti, umumkan di grup, Hilmi yang memutuskan. 

### 3.6 Setelah pembekuan 

Setelah tag `versi-beku` dibuat Kamis 13.00, tidak ada branch fitur baru. Perbaikan kendala eksekusi hanya lewat `hotfix/` dengan persetujuan PIC teknis panitia, dicatat di `docs/catatan-perubahan.md` (apa, kenapa, kapan, disetujui siapa), sesuai TOR 6.1. Tag versi beku tidak pernah dipindah. 

## Bab 4. Aturan Vibe Coding 

**AI yang menulis, manusia yang memiliki. Semua AI coding tim membaca satu file konteks yang sama (** **`AGENTS.md` ), bekerja satu tugas kecil per sesi, dan setiap hasilnya dijalankan serta dibaca sebelum di-commit.** TOR membolehkan AI coding assistant, tetapi tim wajib memahami dan mempertanggungjawabkan kodenya, dan wajib mencatat penggunaannya. 

### 4.1 Satu sumber konteks untuk semua AI 

Tiap anggota boleh memakai alat berbeda (Claude Code, Gemini CLI, Cursor, Copilot, dan lain-lain). Agar semua AI "tahu aturan rumah" yang sama: 

- Isi aturan ditulis sekali di **`AGENTS.md`** di akar repo. 

- File khusus alat cukup menunjuk ke sana. Contoh: `CLAUDE.md` berisi satu baris `@AGENTS.md` ; `GEMINI.md` berisi "Ikuti AGENTS.md". Cek nama file konteks yang dibaca 

- alat masing-masing. 

Page 11 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

Bab-bab Buku 2 yang relevan diekspor ke Markdown dan disimpan di `docs/desain/` (misalnya `bab4-agen.md` , `bab6-data.md` , `bab7-api.md` ), agar AI bisa diminta membacanya. 

Semua ini di-commit **setelah** countdown, sebagai commit pertama oleh Hilmi. 

### 4.2 Isi `AGENTS.md` 

```
# AGENTS.md: aturan untuk semua AI coding di repo PartPilot
```

```
## Proyek
```

```
PartPilot: agen AI pengadaan suku cadang, dari work order sampai draf PO yang
disetujui manusia. Detail desain ada di docs/desain/. Baca file desain yang
relevan
```

```
sebelum menulis kode.
```

```
## Arsitektur singkat
```

```
- server/: Python 3.11+, FastAPI, Google ADK (Workflow + Agent), SQLModel +
SQLite
- web/: React + Vite + TypeScript + Tailwind + shadcn/ui, TanStack Query
(polling 2 detik)
```

```
- Status kasus dan nama tabel: lihat server/app/domain/ (KONTRAK, jangan
diubah tanpa izin)
```

```
## Kepemilikan folder (hanya ubah folder milik orang yang sedang memakaimu)
- server/app/agents, server/app/workflows, tools/matcher*, tools/normalize*:
Azziz
```

- `server/app lainnya, Dockerfile, .github: Hilmi` 

- `web/src inti, web/src/api, scripts/generate_seed.py, data/seed: Rifqi` 

- `web/src/pages pendukung, web/src/styles: Alifa` 

- `data/eval, scripts/run_eval.py, docs, README.md: Lukman` 

##### `## Aturan keras` 

```
1. Jangan pernah menulis API key, token, atau isi .env ke kode, log, atau
commit.
```

```
2. Jangan mengubah file di luar folder pemilik tanpa diminta eksplisit.
3. Jangan menambah dependensi. Bila perlu, berhenti dan sebutkan paket yang
dibutuhkan.
```

`4. Jangan mengubah server/app/domain atau web/src/api kecuali tugasnya adalah PR kontrak.` 

`5. Jangan menjalankan git push ke main, git push --force, atau git reset -- hard.` 

`6. Jangan merapikan format atau mengganti nama di file yang tidak terkait tugas.` 

`7. Angka uang, stok, dan biaya hanya dihitung di fungsi kode, tidak oleh model.` 

Page 12 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

```
8. Tidak ada tool atau endpoint yang mengirim PO selain endpoint persetujuan
manusia.
```

```
9. Nama model Gemini dibaca dari variabel lingkungan, tidak ditulis langsung.
10. Semua teks antarmuka dan pesan agen dalam bahasa Indonesia.
11. ADK berubah cepat (sekarang 2.x). Bila ragu nama kelas atau parameter,
katakan
```

```
    ragu dan minta potongan dokumentasi resmi, jangan menebak.
```

##### `## Gaya kode` 

- `Python: ruff, type hints, fungsi kecil, docstring satu baris. - TypeScript: strict, komponen fungsi, tanpa any.` 

- `Setiap tool menulis satu baris ke audit_log.` 

##### `## Cara menjalankan` 

```
- Server: cd server && uv run uvicorn app.main:app --reload --port 8000
- Web: cd web && npm run dev
- Uji: cd server && uv run pytest -q
```

### 4.3 Siklus satu tugas vibe coding 

1. **Ambil satu issue** dari papan (Bab 5). Pindahkan ke "Sedang dikerjakan". 

2. **Buat branch** sesuai Bab 3.2. 

3. **Buka sesi AI baru** (sesi lama yang panjang membuat AI lupa aturan dan boros kuota). 

4. **Minta rencana dulu, bukan kode.** Baca rencananya; koreksi bila menyentuh folder lain atau menambah paket. 

5. **Minta kode per langkah kecil** , lalu jalankan. Jangan menumpuk lima langkah tanpa mencoba. 

6. **Uji** sesuai kriteria issue (ID FR atau T dari Buku 2). 

7. **Commit** setiap kali ada yang jalan. 

8. **Isi log AI** (4.6), lalu buat PR. 

### 4.4 Templat prompt pembuka per peran 

Tempel di awal sesi, lalu ganti bagian dalam kurung siku. 

**Azziz (agen):** 

Page 13 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

```
Baca AGENTS.md, docs/desain/bab4-agen.md, dan docs/desain/bab5-ai.md.
Tugas: [nama issue, misalnya node standardisasi fase 1].
Batas: hanya ubah server/app/agents, server/app/workflows,
server/app/tools/matcher.py.
Pakai skema dari server/app/domain, jangan ubah skemanya.
Kriteria selesai: [FR-05, FR-06, FR-07; uji T-02 dan T-03 lulus].
Langkah pertama: tulis rencana file dan fungsi yang akan dibuat, belum kode.
```

#### **Hilmi (backend):** 

```
Baca AGENTS.md, docs/desain/bab6-data.md, dan docs/desain/bab7-api.md.
Tugas: [misalnya endpoint POST /approvals/{po_id}].
Batas: server/app/api, server/app/db, server/app/tools (kecuali matcher),
server/tests.
Kriteria selesai: [FR-23, FR-24; uji T-12 dan T-13 lulus dengan pytest].
Langkah pertama: rencana dulu.
```

#### **Rifqi (frontend dan data):** 

```
Baca AGENTS.md, docs/desain/bab7-api.md, dan docs/desain/bab8-uiux.md.
Tugas: [misalnya halaman Detail Kasus sesuai wireframe].
Batas: web/src kecuali web/src/pages pendukung milik Alifa.
Pakai tipe dari web/src/api/types.ts. Data diambil dengan TanStack Query,
refetch 2 detik.
Kriteria selesai: [daftar elemen di wireframe tampil dari data tiruan dan
dari API asli].
Langkah pertama: rencana komponen.
```

#### **Alifa (halaman pendukung):** 

```
Baca AGENTS.md dan docs/desain/bab8-uiux.md.
Tugas: [misalnya halaman Kotak Masuk Vendor gaya aplikasi chat].
Batas: hanya web/src/pages/[nama halaman] dan web/src/styles.
Pakai komponen yang sudah ada di web/src/components; jangan membuat ulang
tombol atau kartu.
Pakai token warna dari palet di bab8, kontras minimal 4,5:1.
Langkah pertama: rencana tata letak.
```

#### **Lukman (set uji dan dokumen):** 

Page 14 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

```
Baca AGENTS.md dan docs/desain/bab11-testing.md.
Tugas: [misalnya skrip run_eval.py yang membaca
data/eval/part_queries_dev.csv
lalu menghitung akurasi, tingkat bertanya, dan tingkat yakin salah].
Batas: scripts/run_eval.py, data/eval, docs.
Panggil fungsi pencocok lewat antarmuka yang sudah ada; jangan ubah kodenya.
Langkah pertama: rencana dulu.
```

### 4.5 Memeriksa hasil AI sebelum commit 

Sudah dijalankan, bukan hanya "kelihatannya benar". 

- `git diff` dibaca: hanya file di folder sendiri yang berubah. 

- Tidak ada paket baru di `pyproject.toml` atau `package.json` . 

- Tidak ada rahasia, URL internal, atau data pribadi. 

- Nama kelas dan fungsi ADK dicocokkan dengan dokumentasi resmi (AI sering memakai API versi lama). 

- Tidak ada data tiruan yang tertinggal di jalur produksi. 

- Pemilik bisa menjelaskan kode itu dalam dua kalimat (juri boleh bertanya). 

### 4.6 Log penggunaan AI (wajib TOR) 

Setiap orang punya file `docs/ai-log/<nama>.md` , diisi setiap selesai satu tugas: 

|Waktu|Alat dan|Tugas|File yang dibantu|Cara|
|---|---|---|---|---|
||model|||memverifikasi|
|Rabu|Claude|Node|`server/app/workflows/fase1.py`|Uji T-02, T-03|
|16.40|Code|standardisasi|||



Lukman merangkum semua log ke `docs/sumber-dan-ai.md` pada Kamis 13.00 sampai 15.00. Masukkan juga bahwa Buku 1 sampai 3 (perencanaan) disusun dengan bantuan Claude. 

### 4.7 Mengelola kuota dan sesi AI 

- Siapkan **dua alat cadangan** per orang (misalnya satu berbayar, satu gratis) untuk berjaga bila kuota habis tengah malam. 

- Satu tugas, satu sesi. Sesi baru lebih murah dan lebih patuh aturan. 

- Jangan menempelkan file `.env` atau API key ke chat AI mana pun. 

Page 15 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

Untuk pertanyaan konsep ("bagaimana ADK Workflow memilih route?"), tanya ke dokumentasi atau mentor dulu; kode yang dibangun di atas tebakan AI paling mahal diperbaiki. 

## Bab 5. Backlog Tugas 

**Ada 40 issue yang dibagi ke delapan milestone. Setiap orang punya 6 sampai 11 issue, dan tidak ada yang menunggu orang lain lebih dari satu milestone karena semua bekerja di atas kontrak dan data tiruan sejak M0.** Lukman memasukkan seluruh tabel ini ke GitHub Issues di jam pertama. 

### 5.1 Daftar issue 

|ID|Judul|Pemilik|Milestone|Butuh<br>dulu|Selesai bila|
|---|---|---|---|---|---|
|I-01|Kerangka repo,<br>`AGENTS.md`,<br>`docs/desain/`,<br>`.gitignore`,<br>`.env.example`|Hilmi|M0||Semua orang bisa clone dan<br>menjalankan server kosong|
|I-02|Skema domain, daftar status,<br>endpoint tiruan sesuai<br>kontrak|Hilmi|M0|I-01|`GET /cases/{id}`<br>mengembalikan contoh JSON<br>Buku 2 Bab 7.2|
|I-03|Kerangka web: Vite, Tailwind,<br>router, layout, klien API,<br>`types.ts`, data tiruan|Rifqi|M0|I-01, I-02|Halaman kosong tiap rute<br>tampil|
|I-04|Wireframe Figma 4 layar inti<br>dan token warna|Alifa|M0||Disetujui Rifqi dan Lukman|
|I-05|Papan tugas, label, milestone,<br>semua issue|Lukman|M0||Papan berisi 40 kartu|
|I-06|Uji coba ADK: satu Workflow<br>sederhana memanggil Gemini<br>dengan credit panitia|Azziz|M0|credit|Ada respons model; nama<br>model dan region dicatat di<br>`.env.example`|
|I-07|Generator seed: 300 part,<br>alias, duplikat, substitusi,<br>stok, vendor, mesin, aturan;<br>part skenario ditanam|Rifqi|M1|I-02|CSV lengkap; skenario A, B, C<br>ada|
|I-08|Model basis data, pemuat<br>seed,<br>`/demo/reset`, endpoint<br>master|Hilmi|M1|I-02, I-07|`GET /master/parts`berisi<br>300 part|
|I-09|Periksa kewajaran katalog dan<br>harga|Lukman|M1|I-07|Daftar koreksi dikirim ke Rifqi|
|I-10|Token warna ke tema Tailwind,<br>gaya<br>`StatusBadge`|Alifa|M1|I-03, I-04|Semua status tampil dengan<br>warna dan ikon|



Page 16 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|ID|Judul|Pemilik|Milestone|Butuh<br>dulu|Selesai bila|
|---|---|---|---|---|---|
|I-11|Normalisasi teks dan kamus<br>istilah|Azziz|M2|I-07|Uji unit normalisasi lulus|
|I-12|Embedding katalog, cache,<br>skor gabungan, keputusan<br>jelas atau tanya|Azziz|M2|I-08|Fungsi<br>`cocokkan(teks)`<br>mengembalikan<br>`PartMatch`|
|I-13|Set uji<br>`part_queries_dev.csv`dan<br>`_test.csv`(40 + 40)|Lukman|M2|I-07|File terisi, dicek satu orang<br>lain|
|I-14|`scripts/run_eval.py`untuk<br>pencocok part|Lukman|M2|I-12|Keluar tabel 4 ukuran (Buku 2<br>Bab 11.3)|
|I-15|Halaman Form Work Order<br>dan Daftar Kasus|Rifqi|M2|I-03|Bisa membuat kasus ke API<br>tiruan|
|I-16|Tools<br>`cek_stok`,<br>`cari_duplikat`,<br>`hitung_biaya`,<br>`buat_transfer`,<br>`tulis_log`<br>+ uji unit|Hilmi|M3|I-08|Uji unit lulus; angka sama<br>dengan hitungan tangan|
|I-17|Workflow fase 1 lengkap|Azziz|M3|I-12, I-16|Skenario A berakhir<br>`transfer_diminta`; C<br>bertanya|
|I-18|API kasus:<br>`POST /cases`,<br>`GET`<br>`/cases/{id}`,<br>`/log`,<br>`/reply`,<br>runner latar belakang dengan<br>kunci per kasus|Hilmi|M3|I-08|Kasus berjalan otomatis<br>setelah dibuat|
|I-19|Halaman Detail Kasus<br>(linimasa, kartu keputusan,<br>tabel tawaran)|Rifqi|M3|I-15|Sesuai wireframe; data dari<br>API asli|
|I-20|Kartu Pertanyaan untuk<br>teknisi|Rifqi|M3|I-18|Jawaban melanjutkan kasus<br>(T-03, T-04)|
|I-21|Halaman Log|Alifa|M3|I-18|Tabel log dengan lencana<br>aktor|
|I-22|Simulator vendor 5 persona,<br>`tampil_setelah`, percepatan<br>waktu|Hilmi|M4|I-18|Balasan muncul sesuai jeda|
|I-23|Penjadwal pengadaan: tagih<br>vendor diam, picu fase 2|Hilmi|M4|I-22|T-08 lulus|
|I-24|Tools<br>`pilih_vendor`,<br>`cek_aturan`,<br>`buat_draf_po`<br>+ uji unit|Hilmi|M4|I-08|T-09 lulus di uji unit|
|I-25|Agen RFQ, pembaca tawaran,<br>penagih; workflow fase 2 dan<br>eskalasi|Azziz|M4|I-17, I-22,<br>I-24|Skenario B sampai<br>`menunggu_persetujuan`; T-10<br>lulus|



Page 17 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|ID|Judul|Pemilik|Milestone|Butuh<br>dulu|Selesai bila|
|---|---|---|---|---|---|
|I-26|Halaman Kotak Masuk Vendor<br>+ balas manual|Alifa|M4|I-22|Pesan agen dan vendor tampil<br>seperti chat|
|I-27|`vendor_replies.csv`dan<br>`scenarios.json`|Lukman|M4|I-22|30 balasan dan 15 sampai 20<br>skenario|
|I-28|Endpoint persetujuan, jeda,<br>lanjut, pemicu fase 3|Hilmi|M5|I-25|T-12, T-13, T-14 lulus|
|I-29|Fase 3,<br>`before_tool_callback`,<br>jatah panggilan model, cek<br>jeda di setiap node|Azziz|M5|I-28|Log mencatat jumlah<br>panggilan|
|I-30|Antrian Persetujuan,<br>`ApprovalCard`,<br>`PauseButton`|Rifqi|M5|I-28|Alur manajer jalan dari layar|
|I-31|Ketahanan injeksi perintah|Azziz|M5|I-25|T-15 lulus|
|I-32|Tombol isi contoh skenario,<br>reset demo, mode presentasi|Rifqi|M6|I-30|Satu klik per skenario|
|I-33|Rapikan tampilan, microcopy,<br>halaman Bukti Uji, Dashboard<br>(P1)|Alifa|M6|I-30|Lolos cek kontras dan<br>tampilan proyektor|
|I-34|Negosiasi (P1, hanya bila M5<br>selesai)|Azziz|M6|I-29|Vendor penawar turun harga<br>dalam 2 putaran|
|I-35|Dockerfile, deploy Cloud Run,<br>`/health`|Hilmi|M6|I-28|Tautan publik menjalankan<br>skenario B|
|I-36|Gladi tiga skenario tiga kali,<br>laporkan bug|Lukman|M6|I-32|Daftar bug di papan, label<br>`P0`|
|I-37|Jalankan set uji sekali, isi<br>`docs/bukti-uji.md`|Lukman<br>(dibantu<br>Azziz)|M7|I-36|Semua bagian bukti uji terisi<br>hasil nyata|
|I-38|`README.md`dan<br>`docs/sumber-dan-ai.md`|Lukman|M7|log AI<br>semua<br>orang|Memenuhi isi minimum TOR|
|I-39|Rekam video cadangan dan<br>deck seleksi|Alifa|M7|I-36|Video satu putaran penuh,<br>deck PDF|
|I-40|Pindai rahasia, tag<br>`versi-`<br>`beku`, petunjuk akses juri|Hilmi|M7|I-37|Tag terdorong sebelum Kamis<br>13.00|



Page 18 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 5.2 Beban per orang 

|Anggota|Jumlah issue|Issue yang paling menentukan|
|---|---|---|
|Azziz|8|I-12 pencocok, I-17 fase 1, I-25 fase 2|
|Hilmi|11|I-02 kontrak, I-18 runner, I-22 simulator, I-28<br>persetujuan|
|Rifqi|7|I-07 seed, I-19 Detail Kasus|
|Alifa|6|I-04 wireframe, I-26 Kotak Masuk, I-39 video dan<br>deck|
|Lukman|8|I-13 set uji, I-37 bukti uji, I-38 README|



Hilmi memegang paling banyak issue karena backend adalah titik temu semua bagian. Bila Hilmi tertinggal, I-24 (tools pengadaan) dipindah ke Azziz, dan I-35 (deploy) dipindah ke Lukman dengan panduan Buku 2 Bab 12. 

### 5.3 Memasukkan issue ke GitHub 

Contoh satu perintah (ulangi per baris tabel, atau minta AI Lukman mengubah tabel ini menjadi skrip): 

```
gh issue create \
```

```
  --title "I-12 Embedding katalog, skor gabungan, keputusan jelas atau tanya"
\
  --body "Selesai bila: fungsi cocokkan(teks) mengembalikan PartMatch. Butuh:
I-08. Rujukan: Buku 2 Bab 5.1, FR-05..07." \
  --label "area:agen,P0" \
  --milestone "M2 Pencocok part" \
  --assignee USERNAME_AZZIZ
```

## Bab 6. Jadwal 24 Jam 

**Setiap orang tidur sekitar 3 sampai 3,5 jam, bergantian sehingga pasangan cadangan tidak pernah tidur bersamaan: Hilmi lalu Azziz untuk server, Rifqi lalu Alifa untuk web.** TOR menyatakan timer tetap berjalan saat istirahat dan peserta tidak wajib begadang 24 jam; tim yang tidur bergiliran biasanya lebih sedikit membuat bug di pagi hari. 

### 6.1 Jadwal per orang 

Kode issue merujuk Bab 5. "Zz" berarti tidur. 

Page 19 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Jam<br>(WIB)|Acara panitia|Azziz|Hilmi|Rifqi|Alifa|Lukman|
|---|---|---|---|---|---|---|
|Rabu<br>08.00<br>sampai<br>13.00|Registrasi,<br>briefing, credit|Persiapan<br>Bab 8|Persiapan<br>Bab 8|Persiapan<br>Bab 8|Persiapan Bab<br>8|Persiapan Bab 8,<br>catat hasil<br>briefing|
|13.00<br>sampai<br>15.00|Countdown,<br>rancangan<br>awal|I-06 uji ADK<br>+ credit|I-01, I-02<br>kontrak|I-03 mulai,<br>lalu I-07 seed|I-04 wireframe|I-05 papan dan<br>issue|
|14.00<br>sampai<br>16.00|Mentoring 1|Validasi<br>desain agen<br>dengan<br>mentor|Lanjut I-02|I-07 seed|I-04|Pimpin sesi<br>mentor|
|15.00<br>sampai<br>17.00|Hacking|I-11<br>normalisasi|I-08 basis<br>data|I-07 seed|I-10 token<br>warna|Riset harga dan<br>spesifikasi<br>untuk<br>memeriksa<br>katalog (bukan<br>untuk kamus,<br>agar set uji<br>tetap<br>independen)|
|17.00<br>sampai<br>19.00|Hacking|I-12<br>pencocok|I-16, I-24 tools|I-03 selesai,<br>I-15 form|Kerangka<br>deck bersama<br>Lukman|I-09 periksa<br>katalog, mulai I-<br>13|
|19.00<br>sampai<br>21.00|Mentoring 2|I-12,<br>konsultasi<br>ADK|I-16, I-24|I-15 daftar<br>kasus|I-21 halaman<br>log|I-13 set uji|
|21.00<br>sampai<br>00.00|Hacking|I-17 fase 1|I-18 API kasus<br>dan runner|I-19 Detail<br>Kasus|I-26 Kotak<br>Masuk (data<br>tiruan)|I-14<br>`run_eval.py`|
|Kamis<br>00.00<br>sampai|Hacking<br>malam|I-25 fase 2|I-22<br>simulator<br>sampai|**Zz**|I-26<br>tersambung<br>API, I-33|I-27 skenario<br>sampai 01.00,<br>lalu Zz|
|03.30|||00.30, lalu Zz||rapikan||
|03.30<br>sampai<br>05.00|Hacking<br>malam|**Zz**|I-23<br>penjadwal|I-20 kartu<br>pertanyaan|**Zz**|Zz sampai<br>04.30, lalu<br>kerangka<br>README|
|05.00|Hacking pagi|Zz sampai|I-28|I-30 antrian|Zz|I-36 gladi|
|sampai<br>07.00||06.30, lalu I-<br>29|persetujuan<br>dan jeda|persetujuan||putaran 1|



Page 20 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Jam<br>(WIB)|Acara panitia|Azziz|Hilmi|Rifqi|Alifa|Lukman|
|---|---|---|---|---|---|---|
|07.00<br>sampai<br>09.00|Materi<br>pitching 08.00|I-31 injeksi, I-<br>29 selesai|I-35 deploy,<br>merge|I-32 tombol<br>demo|I-33 (bangun<br>07.00), lalu<br>materi<br>pitching|Materi pitching<br>08.00|
|**09.00**|**Batas fitur**||||||
|09.00<br>sampai<br>10.30|Mentoring 3<br>(09.30)|Perbaikan<br>bug agen|Perbaikan<br>bug, uji asap|Perbaikan<br>tampilan|Rekam bahan<br>video|I-36 gladi<br>putaran 2,<br>laporan bug|
|10.30<br>sampai<br>12.00|Mentoring 4,<br>cek<br>pengumpulan|Bantu latihan<br>set uji,<br>perbaiki bug<br>kecil|I-40 pindai<br>rahasia|Gladi<br>operator<br>demo|Deck seleksi|Latihan set uji<br>(belum resmi), I-<br>38 README|
|12.00<br>sampai<br>13.00|Makan siang|Gladi<br>terakhir|**Tag versi-**<br>**beku**|Gladi|Siapkan<br>perekam dan<br>naskah video|Cek luaran|
|13.00<br>sampai<br>15.00|Unggah dan<br>dokumentasi|Catatan<br>teknis agen<br>untuk<br>README|Petunjuk<br>akses juri|Tangkapan<br>layar untuk<br>deck|Rekam video<br>dari versi<br>beku, finalkan<br>deck seleksi|**Set uji resmi di**<br>**versi beku, lalu**<br>**kumpulkan**<br>**semua luaran**|
|15.00<br>sampai<br>16.00|Pitch seleksi|Jawab<br>pertanyaan<br>teknis|Siapkan<br>laptop demo|Operator<br>demo|Pegang deck|Pembicara<br>utama|



Kalau Top 10, malamnya (Mentoring 5, 19.00 sampai 21.00) dipakai hanya untuk latihan presentasi dan perbaikan deck. Prototipe tidak boleh ditambah fitur. 

### 6.2 Aturan waktu 

- **Batas lunak per issue** : bila sebuah issue memakan waktu 1,5 kali dari jatah di tabel, pemiliknya wajib lapor di standup berikutnya dan Lukman memutuskan: dibantu, dipotong, atau ditunda. 

- **Jangan begadang melewati giliran tidur.** Orang yang kurang tidur jam 05.00 membuat bug yang ditemukan jam 10.00. 

- **Alarm** : setiap orang memasang alarm bangun di ponsel, dan pasangan cadangannya membangunkan bila alarm terlewat. 

- **Makan dan ibadah** mengikuti jadwal panitia; pekerjaan diserahterimakan dulu ke pasangan sebelum pergi. 

Page 21 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

## Bab 7. Sinkronisasi dan Integrasi 

**Tim bertemu 10 menit setiap sekitar 3 jam, mengintegrasikan bagian yang sudah jadi di tiga "titik sambung" yang terjadwal, dan setiap penggabungan alur agen langsung diuji asap oleh penjaga main.** Vibe coding membuat tiap orang cepat sendiri-sendiri; standup menjaga agar kecepatan itu menuju arah yang sama. 

### 7.1 Standup 

|Waktu|Fokus tambahan|
|---|---|
|Rabu 13.00|Kickoff: baca ulang Bab 1, Bab 3, Bab 5; konfirmasi<br>stack hasil briefing|
|Rabu 15.00|Kontrak M0 dikunci|
|Rabu 18.00|Data seed dan basis data masuk<br>`main`|
|Rabu 21.00|Hasil mentoring 2; prioritas malam|
|Kamis 00.00|Titik sambung 1 (lihat 7.2)|
|Kamis 03.30|Serah terima giliran tidur server|
|Kamis 06.00|Titik sambung 2|
|Kamis 09.00|Batas fitur; daftar bug P0|
|Kamis 12.00|Siap beku|



Format, maksimal 1 menit per orang, dipimpin Lukman sambil membuka papan: 

1. Yang selesai sejak standup lalu (sebut nomor issue). 

2. Yang dikerjakan sampai standup berikutnya. 

3. Yang menghambat, dan butuh siapa. 

Masalah yang butuh diskusi lebih dari 2 menit dibawa keluar standup oleh orang yang terlibat saja. 

### 7.2 Titik sambung 

|Titik|Waktu|Yang disambung|Harus terbukti|
|---|---|---|---|
|0|Rabu<br>15.00|Web membaca API tiruan|Detail kasus tiruan tampil di layar|



Page 22 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Titik|Waktu|Yang disambung|Harus terbukti|
|---|---|---|---|
|1|Kamis|Web + API + fase 1 agen + seed|Skenario A dan C jalan dari form|
||00.00|asli|sampai status akhir|
|2|Kamis|Ditambah simulator, fase 2,|Skenario B jalan sampai PO terkirim|
||06.00|persetujuan|lewat tombol Setuju|
|3|Kamis|Ditambah tampilan rapi dan|Tiga skenario tiga kali tanpa error|
||09.00|mode demo||



Saat titik sambung, semua yang sedang tidak tidur berhenti membuat fitur baru selama 30 menit dan membantu menyambung. 

### 7.3 Penjaga main dan uji asap 

Hilmi (atau Azziz saat Hilmi tidur) menjalankan uji asap setelah setiap PR yang menyentuh server atau alur agen. Perintah siap tempel (server berjalan di port 8000): 

```
# 1. Server hidup?
curl -s localhost:8000/health
# 2. Reset data demo
curl -s -X POST localhost:8000/demo/reset
# 3. Buat kasus skenario A
```

```
curl -s -X POST localhost:8000/cases -H "Content-Type: application/json" \
  -d '{"teks_kebutuhan": "bearing 6205 karet buat conveyor line 2, urgent",
"machine_id": "M-01", "qty": 2, "urgensi": "tinggi"}'
```

```
# 4. Lihat statusnya beberapa detik kemudian (ganti ID sesuai hasil langkah
3)
```

```
curl -s localhost:8000/cases/WO-0001 | python3 -m json.tool
```

Nilai `machine_id` dan nama field mengikuti kontrak yang dikunci di M0; sesuaikan bila `uv run` berubah. Setelah I-27 selesai (sekitar Kamis 01.00), ganti langkah 3 dan 4 dengan `python scripts/run_eval.py --scenarios --cepat` buatan Lukman. 

Bila uji asap gagal setelah sebuah merge: revert dulu (Bab 3.3), baru diskusikan. 

Page 23 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 7.4 Saluran komunikasi 

|Saluran|Untuk|
|---|---|
|Grup chat "PartPilot teknis"|Pengumuman merge, perubahan kontrak, minta<br>bantuan|
|Komentar di issue GitHub|Status pekerjaan, serah terima, keputusan teknis|
|Bicara langsung|Konflik merge, debugging berdua, standup|



Aturan pengumuman di grup memakai awalan agar mudah dipindai: `[MERGE]` , `[KONTRAK]` , `[BUTUH]` , `[RUSAK]` , `[TIDUR]` , `[BANGUN]` . 

### 7.5 Serah terima sebelum tidur 

Sebelum tidur, tulis komentar di issue yang sedang dikerjakan dan kirim tautannya ke pasangan cadangan: 

```
[TIDUR] I-22 Simulator vendor
Branch: be/simulator (sudah di-push, belum PR)
Sudah jalan: persona cepat, hemat, diam
Belum: persona mahal dan penawar
Cara mencoba: POST /cases skenario B, lihat tabel messages
Bug diketahui: tampil_setelah belum memakai VENDOR_DELAY_SCALE
Bangun: 03.30
```

Selalu push branch sebelum tidur, walau belum selesai. Laptop yang tertutup bukan tempat penyimpanan. 

### 7.6 Memanfaatkan mentor 

TOR meminta tim menyiapkan progres singkat, kendala utama, dan pertanyaan sebelum mentor datang. Lukman menyiapkan kartu ini sebelum setiap sesi mentoring: 

|Bagian|Contoh untuk Mentoring 2|
|---|---|
|Progres dalam satu kalimat|Kontrak, data seed, dan pencocok part sudah jalan;<br>fase 1 sedang dibangun|
|Kendala utama|Belum yakin cara terbaik melanjutkan workflow<br>ADK setelah input manusia|



Page 24 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Bagian|Contoh untuk Mentoring 2|
|---|---|
|Pertanyaan (maksimal 3)|Apakah pola status di basis data + fase terpisah<br>wajar, atau sebaiknya<br>`RequestInput`? Model mana|
||yang paling hemat credit untuk ekstraksi? Apa|
||yang juri paling ingin lihat di demo agentic?|



Pertanyaan teknis ADK dan Google Cloud diarahkan ke mentor dari mitra Google Cloud karena paling relevan dengan keahlian mereka. 

### 7.7 Kerangka Scrum tim 

Tim memakai **Scrum yang dipadatkan untuk 24 jam** : unsur yang membantu koordinasi diambil, ritual yang memakan waktu dipangkas. 

|Unsur Scrum|Di PartPilot|
|---|---|
|Product Owner|Lukman: memutuskan prioritas backlog dan apa<br>yang dipotong|
|Scrum Master|Hilmi: menjaga proses, menyingkirkan hambatan<br>teknis, menjaga<br>`main`|
|Developers|Azziz, Rifqi, Alifa, ditambah Hilmi dan Lukman di<br>wilayah masing-masing|
|Product Backlog|40 issue di Bab 5, urut P0 lalu P1|
|Sprint|Milestone M0 sampai M7, masing-masing 2 sampai<br>4 jam|
|Sprint Planning|5 menit di standup awal sprint: ambil issue<br>milestone itu|
|Daily Scrum|Standup 10 menit setiap sekitar 3 jam (7.1)|
|Sprint Review|Titik sambung 0 sampai 3 (7.2)|
|Retrospective|5 menit setelah titik sambung 1 dan 2: satu hal yang<br>berjalan baik, satu hal yang diubah|
|Definition of Done|Kolom "Selesai bila" di setiap issue, PR digabung, uji<br>asap lolos|



Sprint goal satu kalimat per milestone: 

Page 25 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Sprint|Goal|
|---|---|
|M0|Web menampilkan detail kasus dari kontrak API<br>tiruan|
|M1|Katalog 300 part dan stok 3 gudang bisa dibaca<br>lewat API|
|M2|Pencocok part memutuskan jelas atau tanya<br>dengan akurasi tercatat|
|M3|Skenario A dan C jalan dari form sampai status<br>akhir|
|M4|Skenario B sampai draf PO dengan vendor diam<br>dan vendor mahal|
|M5|Tidak ada jalan menuju PO terkirim selain<br>persetujuan manusia|
|M6|Tiga skenario jalan tiga kali berturut-turut tanpa<br>error|
|M7|Semua luaran TOR siap dari versi beku|



Kalimat untuk juri bila ditanya cara kerja tim: _"Kami memakai Scrum yang dipadatkan: sprint 2 sampai 4 jam, standup berkala, dan review di setiap titik integrasi."_ 

## Bab 8. Persiapan Sebelum Countdown 

**Pagi ini sampai Rabu 13.00 hanya untuk alat, akun, bacaan, dan perlengkapan; tidak ada satu baris kode solusi pun yang ditulis.** Yang disiapkan dengan baik di sini menghemat 1 sampai 2 jam pertama hacking. 

### 8.1 Checklist semua anggota 

- Tidur yang cukup malam ini; besok malam tidur hanya 3 jam. Akun GitHub aktif, username dikirim ke Hilmi. Akun Google untuk credit panitia siap; tahu kata sandinya. Langganan atau kuota AI coding aktif, plus satu alat cadangan (Bab 4.7). Laptop: Git, VS Code, Python 3.11+, Node 20+, `uv` terpasang (Buku 2 Bab 10.1). Baca bab yang ditugaskan (8.3). 

- Nomor ponsel semua anggota tersimpan; grup "PartPilot teknis" dibuat. 

Page 26 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 8.2 Checklist per orang 

|Anggota|Siapkan|
|---|---|
|Azziz|`gcloud`terpasang dan login; simpan offline<br>halaman dokumentasi ADK (Workflow, routes,<br>human input, tool confirmation) dan daftar model<br>Gemini; daftar pertanyaan ADK untuk mentor|
|Hilmi|Repo<br>`partpilot`privat kosong dibuat dan anggota<br>diundang (boleh, karena belum berisi kode);<br>`gh`<br>CLI terpasang dan login;<br>`gcloud`terpasang; draf isi<br>`AGENTS.md`disimpan di catatan pribadi, di-commit<br>setelah 13.00|
|Rifqi|Node dan npm siap; akun shadcn tidak perlu;<br>contoh daftar kategori dan rentang harga suku<br>cadang dari Buku 2 Bab 6.3 dibaca ulang|
|Alifa|Figma siap; font Plus Jakarta Sans dan JetBrains<br>Mono terpasang; palet Buku 2 Bab 8.4 dibuat<br>sebagai style di Figma (desain, bukan kode, jadi<br>boleh); templat deck kosong dengan logo tim|
|Lukman|Membawa TOR cetak atau PDF; kartu pertanyaan<br>mentoring 1; daftar 40 issue Bab 5 siap ditempel;<br>kontak PIC panitia; tahu siapa yang mengumpulkan<br>berkas|



### 8.3 Bacaan wajib sebelum 13.00 

|Anggota|Buku 1|Buku 2|Buku 3|
|---|---|---|---|
|Semua|Ringkasan, Bab 6|Cara memakai, Bab 1, Bab 3|Ringkasan, Bab 1, 3, 4|
|Azziz|Bab 6.3|Bab 4, 5, 11|Bab 5, 6|
|Hilmi||Bab 6, 7, 9, 10, 12|Bab 2, 5, 7|
|Rifqi||Bab 6.3, 7, 8|Bab 5, 6|
|Alifa|Bab 5 (persona)|Bab 8|Bab 9|
|Lukman|Semua, terutama Bab 12|Bab 1, 2, 11|Semua|



Page 27 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 8.4 Perlengkapan fisik 

- Laptop dan charger, **terminal listrik (colokan T)** satu per tim. 

- Adaptor HDMI atau USB-C ke HDMI untuk laptop demo, diuji dengan monitor. 

- Mouse, earphone untuk fokus. 

- Ponsel dengan kuota cukup untuk hotspot cadangan bila Wi-Fi acara lambat. 

- Flashdisk berisi salinan repo dan video cadangan (diisi Kamis). 

- Jaket (ruang ber-AC semalaman), obat pribadi, botol minum. 

- Pakaian rapi untuk Final Demo Day Jumat. 

### 8.5 Yang dilakukan saat briefing (Rabu 09.15 sampai 12.00) 

- Lukman dan Azziz mencatat semua ketentuan teknis, terutama daftar di Buku 2 Bab 9.5. 

- Saat pembagian credit, Azziz dan Hilmi langsung mencoba login ke proyek dan mengaktifkan layanan (Buku 2 Bab 10.1 langkah 3 dan 4). Masalah akses dilaporkan ke panitia saat itu juga, bukan setelah 13.00. 

- Bila briefing mengubah stack, Hilmi dan Azziz memperbarui Bab 9 Buku 2 dan draf `AGENTS.md` sebelum countdown. 

## Bab 9. Presentasi 

**Ada dua presentasi yang sangat berbeda: pitch seleksi sekitar 2 menit pada Kamis 15.00, dan Final 10 menit plus 3 menit tanya jawab pada Jumat. Lukman membuka dan menutup, Azziz menjelaskan agen, Rifqi memegang keyboard demo, Alifa memegang deck dan waktu, Hilmi menjaga sistem.** Isi cerita ada di Buku 1 Bab 12; bab ini mengatur siapa, kapan, dan bagaimana. 

### 9.1 Pitch seleksi (Kamis 15.00 sampai 16.00) 

TOR: deck seleksi berisi masalah, solusi, alur agen, bukti kerja, manfaat, dan tim, ringkas untuk pitch 2 menit. Dua puluh tim tampil dalam satu jam, jadi waktu per tim sangat pendek. 

|Detik|Slide|Pembicara|Isi|
|---|---|---|---|
|0 sampai 20|1. Masalah|Lukman|Mesin berhenti karena menunggu part, bukan|
||||karena teknisi|
|20 sampai 40|2. Solusi|Lukman|PartPilot dalam satu kalimat (Buku 1 Bab 6.1)|
|40 sampai 75|3. Alur agen|Azziz|Diagram 7 langkah, 3 titik kendali manusia|



Page 28 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Detik|Slide|Pembicara|Isi|
|---|---|---|---|
|75 sampai 95|4. Bukti<br>kerja|Azziz|Satu tangkapan layar atau klip 15 detik titik<br>persetujuan + satu angka hasil uji nyata|
|95 sampai 110|5. Manfaat|Lukman|Satu kalimat dampak (Buku 1 Bab 9.6)|
|110 sampai<br>120|6. Tim|Lukman|Lima nama dan peran, satu kalimat penutup|



Demo langsung di pitch seleksi **tidak disarankan** kecuali panitia memberi waktu lebih. Klip pendek dari versi beku lebih aman dan tetap jujur, asal disebut "rekaman dari prototipe versi beku". 

### 9.2 Final Demo Day (Jumat) 

Format TOR: 15 menit per tim, yaitu 10 menit pitching dan demo, 3 menit tanya jawab, 2 menit pergantian. 

|Menit|Bagian|Bicara|Di layar|
|---|---|---|---|
|0:00<br>sampai 1:30|Masalah|Lukman|Slide cerita mesin berhenti,<br>bukti Indonesia|
|1:30 sampai<br>2:30|Solusi dan<br>arsitektur|Azziz|Diagram alur dan arsitektur|
|2:30<br>sampai<br>7:00|Demo<br>langsung|Azziz menarasikan, Rifqi<br>mengoperasikan|Skenario B lengkap, lalu<br>potongan skenario A atau C<br>bila waktu cukup|
|7:00<br>sampai<br>8:30|Dampak dan<br>bukti uji|Lukman|Tabel hasil uji nyata, contoh<br>hitungan berlabel asumsi|
|8:30<br>sampai<br>9:30|Bisnis dan<br>rencana|Lukman|Segmen, model pendapatan,<br>peta jalan|
|9:30<br>sampai<br>10:00|Penutup|Lukman|Satu kalimat yang diingat juri|



Yang **wajib terlihat** di demo menurut TOR: tujuan, masukan, langkah agen, penggunaan tools atau data, hasil eksekusi, titik kendali manusia, satu kondisi gagal, dan penyebutan bagian yang disimulasikan. 

Page 29 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 9.3 Pembagian menjawab pertanyaan juri 

|Topik pertanyaan|Penjawab utama|Cadangan|
|---|---|---|
|Masalah, pasar, bisnis, regulasi|Lukman|Alifa|
|Agen, AI, akurasi, model, prompt|Azziz|Hilmi|
|Arsitektur, keamanan, deploy, skala|Hilmi|Azziz|
|Data, katalog, tampilan|Rifqi|Alifa|
|Pengalaman pengguna, desain|Alifa|Rifqi|



Aturan: satu pertanyaan dijawab satu orang. Lukman yang menunjuk bila juri tidak mengarah ke orang tertentu. Jawaban mulai dengan inti dalam satu kalimat (Buku 1 Bab 12.5). 

### 9.4 Deck 

|Deck|Pemilik|Jumlah slide|Batas|
|---|---|---|---|
|Seleksi|Alifa (visual), Lukman (isi)|6|Kamis 15.00|
|Final|Alifa dan Lukman|12 sampai 15|Jumat 08.15|



Aturan desain deck: memakai palet dan font yang sama dengan aplikasi (Buku 2 Bab 8.4 dan 8.5), satu pesan per slide, angka yang dikutip harus ada sumbernya di slide (kecil di bawah), tangkapan layar diambil dari versi beku. 

### 9.5 Video cadangan 

|Aspek|Ketentuan|
|---|---|
|Isi|Satu putaran skenario B penuh + potongan<br>skenario A atau C, sama persis dengan versi beku|
|Durasi|3 sampai 4 menit|
|Alat rekam|OBS Studio atau perekam layar bawaan; 1080p|
|Suara|Narasi Azziz atau teks keterangan; tanpa musik<br>keras|
|Keamanan|Tidak ada terminal,<br>`.env`, atau token yang terlihat|



Page 30 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Aspek|Ketentuan|
|---|---|
|Nama file|Mengikuti format panitia; bila belum ada:|
||`PartPilot_FiveAgent_VideoCadangan.mp4`|
|Salinan|Google Drive tim, flashdisk, dan laptop demo|



### 9.6 Jadwal latihan 

|Waktu|Latihan|
|---|---|
|Kamis 12.00|Pitch seleksi 2 menit, dua kali, dengan stopwatch|
|Kamis 14.30|Gladi pitch seleksi di laptop yang akan dipakai|
|Kamis 17.00 sampai 19.00 (bila Top 10)|Susun deck final; latihan demo berdua (Azziz dan<br>Rifqi)|
|Kamis 19.00 sampai 21.00|Mentoring 5: presentasi penuh di depan mentor,<br>catat masukan|
|Kamis 21.00 sampai 23.00|Tiga kali latihan penuh 13 menit, termasuk simulasi<br>tanya jawab dari Buku 1 Bab 12.5|
|Jumat 07.00|Uji perangkat, uji video, satu latihan cepat; tidur<br>cukup sebelumnya|



## Bab 10. Rencana Darurat 

**Setiap masalah besar sudah punya keputusan cadangan dan orang yang memutuskannya, supaya tim tidak berdebat jam 3 pagi.** Dua pengaman terpenting: branch `stabil` yang selalu menunjuk versi terakhir yang lolos uji asap, dan video cadangan. 

### 10.1 Branch `stabil` 

Setiap kali uji asap lolos (Bab 7.3), Hilmi memajukan branch `stabil` ke commit itu: 

```
git switch main && git pull
git branch -f stabil main
git push -f origin stabil
```

Page 31 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

`stabil` adalah satu-satunya branch yang boleh di-force-push, dan hanya oleh penjaga main. Bila `main` rusak dan waktu mepet (misalnya Kamis 12.30), versi beku diambil dari `stabil` . 

### 10.2 Tabel keputusan darurat 

|Kejadian|Tanda|Tindakan|Yang memutuskan|
|---|---|---|---|
|Kuota AI coding<br>seseorang habis|AI menolak atau<br>sangat lambat|Pindah ke alat<br>cadangan; bila semua<br>habis, berpasangan<br>memakai alat anggota<br>lain|Pemilik sendiri|
|Credit Google<br>Cloud atau Gemini<br>bermasalah|Galat 403 atau<br>kuota|Lapor PIC teknis<br>segera; turunkan ke<br>model Flash-Lite;<br>kurangi panggilan per<br>kasus|Azziz|
|ADK terlalu sulit<br>atau berperilaku<br>aneh|Fase 1 belum jalan<br>dengan ADK pada<br>standup Rabu 21.00|Ganti ke SDK<br>`google-`<br>`genai`langsung<br>dengan orkestrasi<br>Python biasa. Node,<br>tools, dan status tetap<br>sama|Azziz dan Hilmi,<br>diputuskan di<br>standup 21.00|
|Konflik merge<br>besar|PR berisi konflik di<br>banyak file|Hentikan merge 30<br>menit; pemilik folder<br>menyelesaikan berdua;<br>bila buntu, revert|Hilmi|
|`main`rusak|Uji asap gagal|Revert commit<br>penyebab; kerja lanjut<br>dari<br>`stabil`bila perlu|Hilmi atau Azziz|
|Laptop mati atau<br>rusak||Semua sudah di-push<br>(Bab 7.5); pasangan<br>cadangan melanjutkan;<br>pinjam laptop panitia<br>bila ada|Lukman|
|Anggota sakit atau<br>tumbang||Pasangan cadangan<br>mengambil issue P0;<br>issue P1 milik orang itu<br>dipotong|Lukman|



Page 32 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Kejadian|Tanda|Tindakan|Yang memutuskan|
|---|---|---|---|
|Wi-Fi acara mati|Tidak bisa push<br>atau memanggil<br>model|Hotspot ponsel; kerja<br>lokal dan push nanti|Siapa pun|
|Deploy Cloud Run<br>gagal|Kamis 09.00 belum<br>ada tautan hidup|Demo dari laptop; TOR<br>hanya mewajibkan<br>tautan aplikasi "bila<br>tersedia"|Hilmi|
|Fitur P0 belum<br>selesai di batas<br>fitur|Kamis 09.00|Potong sesuai Buku 2<br>Bab 10.6; jangan<br>pernah memotong<br>persetujuan, jeda, log,<br>kondisi gagal, bukti uji|Lukman dengan<br>Azziz|
|Demo langsung<br>gagal di panggung|Galat, layar beku,<br>model lambat lebih<br>dari 15 detik|Dalam 10 detik pindah<br>ke video cadangan.<br>Lukman: "Kami<br>lanjutkan dengan<br>rekaman dari versi<br>beku yang sama."|Rifqi memberi<br>tanda, Lukman<br>bicara|
|Juri menemukan<br>bug saat tanya<br>jawab||Akui, jelaskan<br>penyebab dan rencana<br>perbaikan; jangan<br>membela diri|Penjawab topik<br>terkait|



### 10.3 Titik keputusan yang sudah dijadwalkan 

|Waktu|Pertanyaan|Bila jawabannya tidak|
|---|---|---|
|Rabu|Apakah Gemini bisa dipanggil dari|Pakai jalur cadangan panitia; Azziz|
|15.00|proyek credit?|lanjut dengan data tiruan sambil<br>menunggu|
|Rabu|Apakah ADK Workflow fase 1 sudah|Beralih ke SDK langsung (10.2)|
|21.00|jalan untuk satu skenario?||
|Kamis|Titik sambung 1 lolos?|Negosiasi (I-34) dan Dashboard|
|00.00||dicoret sekarang|
|Kamis|Titik sambung 2 lolos?|Deploy Cloud Run dicoret; fokus|
|06.00||demo lokal dan video|



Page 33 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Waktu|Pertanyaan|Bila jawabannya tidak|
|---|---|---|
|Kamis|Tiga skenario stabil?|Pilih dua skenario terkuat untuk|
|09.00||demo; yang ketiga cukup di bukti uji|



## Bab 11. Pembekuan dan Pengumpulan 

**Merge terakhir Kamis 12.30, tag** **`versi-beku` paling lambat 12.55, lalu dua jam berikutnya hanya untuk bukti uji resmi, dokumen, deck, dan video dari versi yang sama.** Menunggu sampai 12.59 untuk merge adalah cara tercepat kehilangan versi beku yang bersih. 

### 11.1 Urutan Kamis 

|Waktu|Langkah|Pemilik|
|---|---|---|
|12.00|Umumkan<br>`[BEKU 30 MENIT]`: tidak ada PR baru,<br>kecuali perbaikan P0 yang sudah dalam review|Lukman|
|12.30|Merge terakhir. Uji asap penuh tiga skenario|Hilmi|
|12.40|Pindai rahasia:<br>`gitleaks detect --source . -v`<br>harus bersih|Hilmi|
|12.45|Buat tag dan arsip (perintah 11.2); catat hash<br>commit; tangkap layar halaman tag GitHub<br>sebagai bukti waktu|Hilmi|
|12.55|Ikuti mekanisme pencatatan waktu panitia bila ada<br>(formulir atau lainnya)|Lukman|
|**13.00**|**Pembekuan. Kode, prompt, konfigurasi workflow,**<br>**dan data uji tidak berubah lagi**|Semua|
|13.00 sampai<br>13.45|Jalankan set uji resmi di versi beku (sekali), isi<br>`docs/bukti-uji.md`dengan hasil apa adanya|Lukman dan<br>Azziz|
|13.00 sampai<br>14.00|Rekam video cadangan dari versi beku|Alifa dan Rifqi|
|13.00 sampai 14.15|Selesaikan README,<br>`docs/sumber-dan-ai.md`,<br>gabungan log AI|Lukman|
|14.15 sampai 14.40|Deck seleksi final dengan angka hasil uji resmi|Alifa dan Lukman|



Page 34 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

|Waktu|Langkah|Pemilik|
|---|---|---|
|14.40|Beri akses repo ke panitia dan juri; isi formulir|Lukman dan Hilmi|
||pengumpulan||
|14.50|Satu orang membuka semua tautan dari jendela<br>penyamaran (incognito) dan mengikuti petunjuk<br>akses dari nol|Rifqi|
|**15.00**|**Semua luaran diterima panitia**|Lukman|



Perubahan dokumen setelah tag (README, bukti uji, catatan sumber) boleh di-commit karena bukan kode, prompt, konfigurasi, atau data uji. Tulis di README bahwa commit setelah tag `versi-beku` hanya berisi dokumentasi. 

### 11.2 Perintah pembekuan 

```
git switch main && git pull
```

```
# Tag versi beku
```

```
git tag -a versi-beku -m "Versi beku PartPilot, Agentic AI Hackathon 2026,
Kamis 22 Oktober 2026 13.00 WIB"
```

```
git push origin versi-beku
```

```
# Catat hash commit untuk README dan formulir
git rev-parse versi-beku
```

```
# Arsip cadangan (bila panitia meminta arsip, atau untuk flashdisk)
git archive --format=zip -o PartPilot_FiveAgent_versi-beku.zip versi-beku
```

Bila setelah pembekuan ada kendala eksekusi yang harus diperbaiki, ikuti Bab 3.6: izin PIC teknis, branch `hotfix/` , catat di `docs/catatan-perubahan.md` , dan tag `versi-beku` tidak dipindah. 

### 11.3 Isi paket pengumpulan 

Tautan repo + tag `versi-beku` + hash commit + petunjuk akses penilai 

Tautan aplikasi Cloud Run (bila tersedia) dan PIN demo bila dipakai 

- README sesuai isi minimum TOR 

- `docs/sumber-dan-ai.md` 

- `docs/bukti-uji.md` dengan hasil nyata, termasuk kegagalan 

- Deck seleksi (PDF) 

Video cadangan (untuk finalis, wajib Jumat 08.15; lebih aman disiapkan Kamis) 

Page 35 of 36 

Buku 3 PartPilot: Strategi Tim dan Pelaksanaan Teknis 

### 11.4 Jumat pagi (bila masuk Top 10) 

|Waktu|Langkah|Pemilik|
|---|---|---|
|Kamis 23.00|Tidur. Tidak ada perubahan prototipe|Semua|
|06.30|Bangun, sarapan|Semua|
|07.00|Laptop demo: baterai penuh, notifikasi mati,<br>mode jangan ganggu, tab browser siap, zoom<br>125%, server lokal menyala dari versi beku,<br>video cadangan terbuka di tab lain|Hilmi dan Rifqi|
|07.45|Registrasi finalis|Lukman|
|**08.15**|**Deck final dan video cadangan terkumpul; uji**<br>**perangkat dengan proyektor panitia**|Alifa dan<br>Lukman|
|Selama penjurian tim<br>lain|Tetap di ruangan, catat pertanyaan juri ke tim<br>lain untuk antisipasi|Alifa|



### 11.5 Setelah acara 

- Matikan layanan Cloud Run dan sumber daya lain (TOR 6.4). 

- Cabut atau putar ulang API key yang pernah dipakai. 

- Simpan semua buku, deck, video, dan repo; bahan ini dipakai bila PartPilot lanjut ke inkubasi (Buku 1 Bab 11). 

Page 36 of 36 

