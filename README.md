# Portal Data Formasi CPNS 2024 & Analytics Dashboard

> **Database Relasional 3NF & Analisis Terbuka Seleksi Calon Pegawai Negeri Sipil (BKN 2024)**  
> *Research & Engineering by Eurekaa*

Aplikasi visualisasi, eksplorasi, dan analitik kompetisi formasi CPNS 2024 berskala penuh. Mengintegrasikan **111.921 data formasi resmi SSCASN BKN**, normalisasi relasi many-to-many program studi, pemetaan gaji pokok CPNS 80% (PP No. 5 Tahun 2024), serta perhitungan rasio kompetisi dan peluang kelulusan secara real-time.

---

## 📊 Ringkasan Data Resmi

| Indikator | Nilai | Keterangan |
| :--- | :---: | :--- |
| **Total Formasi Jabatan** | **111.921** | 100% data resmi SSCASN BKN 2024 |
| **Total Alokasi Kuota (Kursi)** | **247.202** | Total kapasitas penerimaan nasional |
| **Total Pelamar Riil (MS)** | **3.026.576** | Pelamar lolos verifikasi administrasi BKN |
| **Formasi Tanpa Pelamar (0 Pelamar)** | **25.007** | **Peluang Emas** (Peluang lolos 100%) |
| **Rata-rata Rasio Kompetisi** | **1 : 9.18** | Rata-rata persaingan pelamar per kursi |
| **Cakupan Instansi** | **544** | Seluruh K/L, Pemprov, Pemkab & Pemkot |
| **Program Studi / Jurusan Unik** | **5.289** | Dinormalisasi 3NF dari multivalued raw |
| **Relasi Formasi - Jurusan** | **670.994** | Junction table many-to-many |

---

## ⚡ Fitur Utama

- **Filter & Pencarian Real-Time (Server-Side):**
  - Pencarian debounced jabatan, instansi, lokasi, dan ID formasi.
  - Autocomplete pencarian program studi / jurusan.
  - Filter jenjang pendidikan (`SMA/SMK`, `D-III`, `D-IV`, `S-1`, `S-2`, `Profesi`, `S-3/Spesialis`).
  - Filter lingkup wilayah (`Pusat`, `Provinsi`, `Kabupaten/Kota`) dan 544 instansi spesifik.
  - Tombol 1-klik: **`⚡ Formasi 0 Pelamar (Peluang Emas)`**.
  - Filter tingkat keketatan: *Tanpa Pelamar, Sangat Longgar, Moderat, Sangat Ketat*.
  - Slider batas penghasilan minimal (Take-Home Pay).
  - Pengurutan dinamis: Peluang lolos tertinggi, persaingan terketat, kuota terbanyak, dan gaji tertinggi.
- **Visualisasi Dinamis (Chart.js):**
  - Bar chart *Top 10 Jurusan Paling Dibutuhkan*.
  - Bar chart *Top 10 Instansi dengan Kuota & Kompensasi Terbesar*.
  - Grafik otomatis bereaksi dan ter-update saat filter diubah.
- **Tabel Data Terpaginasi Lengkap:**
  - Paginasi server-side (`LIMIT` dan `OFFSET` SQLite) cepat (~0.1 detik).
  - Rincian gaji PP 5/2024 (CPNS 80% vs 100% PNS).
  - Modal detail komprehensif menampilkan nomor regulasi hukum tunjangan kinerja (tukin/TPP).
  - Unduh hasil filter query langsung ke format **CSV**.
- **Akses & Unduh Dataset Mentah:**
  - File mentah `raw_cpns_2024.csv` (44 MB) dan database SQLite `cpns2024.db` dapat diunduh langsung dari web.

---

## 🚀 Cara Menjalankan Secara Lokal

### Di Windows (One-Click Launcher)
1. Double-click file **`start_dashboard.bat`** di folder project.
2. Server otomatis berjalan dan membuka browser di `http://localhost:8000`.
3. Untuk menghentikan, double-click **`stop_dashboard.bat`**.

### Manual via Terminal / Command Prompt
```bash
# 1. Clone repository
git clone https://github.com/username/cpns2024-dashboard.git
cd cpns2024-dashboard

# 2. Buat virtual environment & aktifkan
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependensi
pip install -r requirements.txt

# 4. Jalankan FastAPI server
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Buka browser di **http://localhost:8000** (dan Swagger Docs di `http://localhost:8000/docs`).

> **Catatan Database:** Jika file `data/cpns2024.db` belum diekstrak, backend otomatis mengekstrak `data/cpns2024.db.gz` atau membangun database dari `data/raw_cpns_2024.csv` saat aplikasi pertama kali dijalankan.

---

## 🌐 Menjadikan Aplikasi Ini Online (Deployment Guide)

### ❓ Apakah Aman / Bisa Pakai GitHub Pages Saja?
**GitHub Pages TIDAK BISA** menjalankan aplikasi ini secara langsung, karena:
1. **GitHub Pages hanya mendukung file statis (HTML/CSS/JS murni).**
2. Aplikasi ini memiliki backend Python (FastAPI) dan basis data SQLite berukuran 166 MB dengan 670.000 relasi yang memerlukan pemrosesan query SQL server-side (`LIMIT`/`OFFSET`, aggregasi, filter multi-tabel).

---

### ✅ Cara Paling Gampang & Gratis (Recommended)

#### Pilihan 1: Render.com (Gratis & Sangat Mudah)
1. Fork repository ini ke akun GitHub kamu.
2. Buka [Render.com](https://render.com) dan buat akun (gratis).
3. Klik **New +** $\rightarrow$ pilih **Web Service** $\rightarrow$ hubungkan dengan repository GitHub kamu.
4. Isi konfigurasi berikut:
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Klik **Create Web Service**. Dalam 2–3 menit web kamu sudah live dengan URL publik gratis seperti `https://cpns-dashboard.onrender.com`.

#### Pilihan 2: Railway.app (Gratis Trial / Performa Cepat)
1. Buka [Railway.app](https://railway.app), login dengan GitHub.
2. Klik **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Railway akan otomatis mendeteksi FastAPI dan langsung menjalankan aplikasi.

#### Pilihan 3: Hugging Face Spaces (Gratis & Tanpa Sleep/Tidur)
1. Buka [Hugging Face Spaces](https://huggingface.co/spaces) $\rightarrow$ Create new Space.
2. Pilih SDK **Docker** atau **Gradio/FastAPI**.
3. Push kode ini ke Space kamu. Web akan aktif online 24/7 tanpa batas kuota tidur.

---

## 📈 Bagaimana Jika Pengunjung Tiba-tiba Banyak (High Traffic)?

Jika dibagikan di media sosial (TikTok / X / Telegram) dan diakses ribuan hingga puluhan ribu pelamar sekaligus:

### 1. Pasang Cloudflare (Gratis 100%)
- Hubungkan domain kamu ke **Cloudflare**.
- Tambahkan **Page Rules / Cache Rules**:
  - URL `*.domain.com/static/*` $\rightarrow$ Cache Everything (1 bulan).
  - URL `*.domain.com/api/stats` $\rightarrow$ Cache Everything (TTL: 1 jam).
  - URL `*.domain.com/api/filters*` $\rightarrow$ Cache Everything (TTL: 1 jam).
  - URL `*.domain.com/api/analytics/*` $\rightarrow$ Cache Everything (TTL: 1 jam).
- **Efek:** 90–95% permintaan tidak akan membebani server kamu karena langsung dijawab oleh CDN Cloudflare terdekat di kota pengunjung!

### 2. Jalankan Uvicorn Multi-Workers
Di server VPS (misal VPS $4/bulan IDCloudHost/DigitalOcean):
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```
SQLite sudah menggunakan mode **WAL (`Write-Ahead Logging`)**, sehingga mampu melayani ribuan pembacaan konkuren per detik tanpa hambatan (*read concurrency*).

---

## 🍴 Cara Fork & Berkontribusi (How to Fork)

1. **Fork Repository Ini:**
   - Klik tombol **Fork** di pojok kanan atas halaman GitHub repository ini.
   - Pilih akun personal atau organisasi kamu.

2. **Clone Hasil Fork ke Komputer Kamu:**
   ```bash
   git clone https://github.com/<username-kamu>/cpns2024-dashboard.git
   cd cpns2024-dashboard
   ```

3. **Buat Branch Fitur Baru:**
   ```bash
   git checkout -b fitur-analisis-baru
   ```

4. **Lakukan Perubahan & Commit:**
   ```bash
   git add .
   git commit -m "Menambahkan fitur analisis perbandingan regional"
   ```

5. **Push ke GitHub & Buat Pull Request:**
   ```bash
   git push origin fitur-analisis-baru
   ```
   Buka repository kamu di GitHub dan klik tombol **Compare & pull request**.

---

## ⚖️ Lisensi & Sumber Data

- **Sumber Data Formasi:** Portal Resmi Seleksi Calon ASN Badan Kepegawaian Negara (BKN) 2024.
- **Mirror Data Riil:** Nubisub Open Data (`api-sscasn.vercel.app` / `nubisub/sscasn`).
- **Standar Gaji Pokok:** Peraturan Pemerintah Republik Indonesia Nomor 5 Tahun 2024.
- **Regulasi Tunjangan:** Peraturan Presiden Republik Indonesia & Peraturan Daerah tentang Tukin/TPP.
- **Lisensi Software:** MIT License — bebas digunakan, dikembangkan, dan dibagikan untuk kepentingan edukasi dan transparansi publik.
