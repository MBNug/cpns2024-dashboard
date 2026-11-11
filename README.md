# Portal Data Formasi CPNS 2024 & Analytics Dashboard

> **Platform Eksplorasi Data Terbuka & Analitik Kompetisi Seleksi Calon Pegawai Negeri Sipil (BKN 2024)**  
> *Dikembangkan secara independen untuk transparansi data dan kemudahan pencarian formasi bagi calon pelamar ASN di Indonesia.*

---

## 📌 Ringkasan Dataset Resmi

Aplikasi ini mengolah seluruh dataset publik seleksi CPNS 2024 dari portal resmi SSCASN BKN ke dalam skema basis data relasional ternormalisasi (3NF):

| Indikator | Nilai | Keterangan |
| :--- | :---: | :--- |
| **Total Formasi Jabatan** | **111.921** | 100% data publikasi resmi SSCASN BKN 2024 |
| **Total Alokasi Kuota Kursi** | **247.202** | Total kapasitas penerimaan CPNS nasional |
| **Total Pelamar Riil (MS)** | **3.026.576** | Pelamar lolos verifikasi administrasi BKN |
| **Formasi Tanpa Pelamar (0 Pelamar)** | **25.007** | Peluang kelulusan tinggi (0 saingan di tahap administrasi) |
| **Rata-rata Rasio Kompetisi** | **1 : 9.18** | Rata-rata pelamar per 1 kursi formasi |
| **Cakupan Instansi** | **544** | Seluruh K/L Pusat, Pemerintah Provinsi, Kabupaten & Kota |
| **Kualifikasi Program Studi** | **5.289** | Dinormalisasi dari string multivalued menjadi entitas terpisah |
| **Relasi Formasi - Jurusan** | **670.994** | Junction table relasi *many-to-many* |

---

## ✨ Fitur Utama

- **Pencarian Cepat & Filter Multidimensi:**
  - Pencarian instan (*debounced*) untuk nama jabatan, instansi, lokasi penempatan, dan ID formasi.
  - Autocomplete interaktif untuk ribuan program studi / jurusan pendidikan.
  - Filter jenjang pendidikan (`SMA/SMK`, `D-III`, `D-IV`, `S-1`, `S-2`, `Profesi`, `S-3/Spesialis`).
  - Filter lingkup instansi (`Pusat`, `Provinsi`, `Kabupaten/Kota`) dan pilihan instansi spesifik.
  - Filter cepat 1-klik: **`Formasi 0 Pelamar`**.
  - Filter rentang gaji publikasi BKN dan tingkat keketatan kompetisi.
- **Tabel Responsif & Ramah Pengguna Mobile:**
  - Paginasi server-side super cepat menggunakan SQLite (`LIMIT` dan `OFFSET`).
  - Navigasi pintar di perangkat seluler dengan petunjuk geser tabel dan *auto-hide header* saat menggulir.
  - Ringkasan angka penting (kuota, pelamar, dan peluang) tampil langsung di kartu pertama pada layar HP.
- **Simulasi Slip Penghasilan Bulanan (Take-Home Pay):**
  - Rincian gaji pokok CPNS tahun pertama (80% sesuai Lampiran II PP No. 5 Tahun 2024).
  - Simulasi uang makan ASN per golongan (PMK No. 49 Tahun 2023) dan estimasi tunjangan.
  - Perhitungan estimasi potongan wajib (BPJS Kesehatan 1% dan Iuran Pensiun Taspen 8%).
- **Ekspor & Unduh Data:**
  - Unduh hasil pencarian dan filter aktif ke format **CSV**.
  - Akses unduh dataset mentah untuk keperluan riset akademis dan analisis open-data.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, FastAPI, Uvicorn
- **Database:** SQLite3 (3NF Normalized, WAL Mode)
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript (Zero heavy external dependencies)
- **Design:** Modern Dark Mode, Glassmorphism, Fully Responsive Mobile-First

---

## 🚀 Menjalankan Secara Lokal

### Prasyarat:
- Python 3.10 atau versi yang lebih baru
- Git

### Langkah Instalasi:

```bash
# 1. Clone repository
git clone https://github.com/MBNug/cpns2024-dashboard.git
cd cpns2024-dashboard

# 2. Buat virtual environment
python -m venv .venv

# 3. Aktifkan virtual environment
# Di Windows:
.venv\Scripts\activate
# Di Linux / macOS:
source .venv/bin/activate

# 4. Install dependensi
pip install -r requirements.txt

# 5. Jalankan aplikasi
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Buka peramban (browser) di alamat: **`http://localhost:8000`**

*(Di sistem operasi Windows, Anda juga dapat menjalankan aplikasi secara instan dengan mendua-klik file `start_dashboard.bat`).*

---

## ⚖️ Pernyataan Penyangkalan (Disclaimer) Resmi

1. **Independensi & Sumber Data:**  
   Website ini adalah proyek independen untuk memudahkan pencarian & analisis data formasi CPNS 2024 dan **TIDAK berafiliasi dengan Badan Kepegawaian Negara (BKN) atau instansi pemerintah mana pun**. Sumber data mengacu pada publikasi terbuka portal resmi SSCASN BKN.
2. **Karakteristik Data Tukin / TPP:**  
   Nominal Tukin/TPP dan simulasi take-home pay merupakan estimasi indikatif pemodelan standar kelas jabatan dan kapasitas fiskal APBD, bukan angka mutlak. Nilai riil di lapangan diatur oleh peraturan perundang-undangan dan keputusan internal di masing-masing instansi.
3. **Peluang Kelulusan:**  
   Rasio kompetisi dan persentase peluang merupakan perhitungan matematis objektif untuk referensi strategis, bukan merupakan jaminan atau garansi kelulusan seleksi.

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah [MIT License](LICENSE) — bebas digunakan dan dikembangkan untuk kepentingan edukasi, riset, dan transparansi publik.
