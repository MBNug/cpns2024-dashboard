# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary — Calon Pelamar CPNS / Pejuang NIP di Indonesia:** Lulusan SMA/SMK, Diploma, Sarjana, Magister, Profesi, hingga Doktor di desktop maupun ponsel yang sedang mencari formasi jabatan sesuai kualifikasi jurusan mereka, menimbang peluang lolos berdasarkan rasio pelamar riil (`jumlah_ms`), dan menghitung simulasi penghasilan bersih (*take-home pay*) sebelum memilih instansi.
- **Secondary — Peneliti Kebijakan Publik & Kontributor Komunitas:** Pengguna yang mengunduh dataset mentah (CSV / SQLite 3NF), memeriksa metodologi regulasi gaji/tukin, atau mengirimkan koreksi regulasi TPP daerah melalui formulir komunitas.

## Product Purpose

Portal Data Formasi CPNS 2024 adalah platform eksplorasi data terbuka dan analitik kompetisi seleksi CPNS independen yang mengubah snapshot publik SSCASN BKN 2024 menjadi pencarian instan lintas jurusan, instansi, kuota, keketatan pelamar, dan simulasi penghasilan bersih bulanan. Keberhasilan produk tercapai ketika pelamar dapat menemukan formasi yang paling strategis bagi jurusannya dan membandingkan pilihannya dalam hitungan detik tanpa terhalang antarmuka yang berat.

## Positioning

Menggabungkan seluruh **111.921 formasi jabatan**, **247.202 kuota kursi**, **3.026.576 pelamar memenuhi syarat (`jumlah_ms`)**, **544 instansi**, dan **670.994 relasi formasi–jurusan** dalam skema relasional SQLite 3NF berkecepatan tinggi, dilengkapi filter 1-klik **Formasi 0 Pelamar (25.007 formasi)**, perbandingan *side-by-side* hingga 10 formasi, serta simulator interaktif *Take-Home Pay* (CPNS 80% vs PNS 100% sesuai PP No. 5 Tahun 2024 + estimasi Tukin/TPP + Uang Makan PMK 49/2023 - BPJS & Taspen).

## Operating Context

- Diakses langsung melalui peramban desktop dan seluler (mayoritas pelamar membuka dari ponsel dan membagikan tautan filter/detail formasi melalui WhatsApp, Telegram, atau media sosial).
- Halaman utama (`/`) berfokus pada aksi pencarian cepat jurusan/instansi dan eksplorasi hasil formasi secara langsung di layar pertama tanpa tertutup deretan kartu panjang.
- Halaman dokumentasi (`/sumber-data`) menyajikan transparansi sumber data SSCASN BKN, dasar hukum PP 5/2024 & Perpres/Pergub Tukin/TPP, formula rasio kompetisi, dan arsitektur database 3NF.

## Capabilities and Constraints

- **Backend tetap ringan & cepat:** FastAPI + SQLite3 WAL + GZip + in-memory LRU cache (`backend/main.py`). Seluruh endpoint API (`/api/stats`, `/api/filters`, `/api/filters/jurusan`, `/api/filters/instansi`, `/api/formasi`, `/api/formasi-batch`, `/api/formasi/{formasi_id}`, `/api/export`, `/api/download/raw-csv`, `/api/download/sqlite-db`) tetap dipertahankan 100% kompatibel.
- **Arsitektur Frontend Modular Tanpa Tailwind CDN Runtime:** Menggunakan stylesheet design-system murni (`frontend/css/app.css`) dan modul JavaScript terpisah (`frontend/js/app.js`) yang dilayani melalui `/static`, tanpa ketergantungan compiler runtime CDN yang membebani pemuatan awal.
- **Fitur Wajib Dipertahankan:**
  - Pencarian bebas (*debounced*), autocomplete jurusan (`/api/filters/jurusan`), combobox instansi *cascading* per lingkup (`Pusat`, `Provinsi`, `Kabupaten/Kota`), filter jenjang, jalur formasi, tingkat keketatan, slider penghasilan minimum, pengurutan, dan filter cepat 1-klik (`0 Pelamar`, preset strategis).
  - Sinkronisasi penuh *deep-link* URL query parameter (`q`, `jurusan`, `jurusan_id`, `jenjang`, `kategori_instansi`, `instansi_id`, `jenis_formasi`, `status_keketatan`, `zero_applicant_only`, `gaji_min`, `sort_by`, `page`, `limit`, `detail`).
  - Mode tampilan Tabel (desktop) & Kartu (nyaman di layar ponsel tanpa geser horizontal), beserta paginasi server-side dan ekspor CSV terfilter (`/api/export`).
  - Modal Detail Formasi beserta Simulator Slip Penghasilan Bersih interaktif (`CPNS 80%` vs `PNS 100%`, status keluarga `TK/0`–`K/2`, slider Tukin/TPP) dan tombol klik jurusan untuk langsung memfilter tabel.
  - Fitur Simpan & Bandingkan (*Bookmark* `localStorage` maks. 10 formasi, disinkronkan via `/api/formasi-batch`).
  - Modal & tautan Kontribusi/Koreksi TPP Daerah (terhubung ke Google Form komunitas dengan *prefill* parameter).
  - Pernyataan penyangkalan (*Disclaimer*) resmi: proyek independen tidak berafiliasi dengan BKN/pemerintah, Tukin/TPP bersifat estimasi indikatif (bukan angka mutlak), dan rasio peluang bukan jaminan kelulusan.

## Brand Commitments

- **Kredit & Riset:** `Eurekaa` (independen, transparan, berbasis open-data).
- **Dukungan Kreator (*Support Creator*):** Tetap mempertahankan kanal apresiasi resmi QRIS (`frontend/qris.png`, NMID `ID1025421073475`) dan Tako.id (`https://tako.id/Eurekaaa`, `@Eurekaaa`, `frontend/tako_logo.svg`), disajikan secara elegan dan proporsional tanpa tombol berkedip/agresif yang mendominasi navigasi utama.

## Evidence on Hand

- Database ternormalisasi `data/cpns2024.db.gz` & dataset mentah `data/raw_cpns_2024.csv` (111.921 formasi publikasi resmi SSCASN BKN 2024).
- Aset kreator terverifikasi di `frontend/qris.png` dan `frontend/tako_logo.svg`.
- Tidak ada klaim afiliasi pemerintah, testimoni fiktif, atau jaminan kelulusan.

## Product Principles

1. **Aksi Pencarian di Atas Segalanya:** Kolom pencarian jurusan, instansi, dan hasil formasi harus langsung terjangkau begitu halaman dibuka tanpa tertimbun dekorasi atau deretan kartu berlebih.
2. **Kejujuran Data & Regulasi:** Pisahkan secara tegas angka resmi publikasi SSCASN BKN dari angka simulasi indikatif Tukin/TPP dan potongan.
3. **Kecepatan Instan di Semua Perangkat:** Pertahankan beban jaringan ringan, ketiadaan *framework bloat*, dan keterbacaan angka tabular yang tajam baik di layar ponsel maupun monitor lebar.
