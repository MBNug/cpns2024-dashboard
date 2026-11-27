"""Verified extra CPNS 2026 formation sources audited from the shared Google Drive folder.

Sources evaluated (Drive Folder 1Wu1DypB_oDZpfHs_OSIb48GFvWizXehc):
1. CPNS_Kemenkeu.pdf -> EXCLUDED (39/39 identical JPEG stream SHA-256 duplicate of KepmenPANRB 675/2026).
2. CPNS_Kemenkes_Info_STR_.pdf -> EXCLUDED (SE HK.02.02/F/4023/2026 STR rules; zero formasi/quota rows).
3. CPNS_Polri.pdf -> EXCLUDED FROM FORMASI TABLE (Canva briefing deck referencing KepmenPANRB 653/2026,
   750 estimated slots, but lacks education/location fields, has 513 vs 514 Teknis typo, and slide 13
   Keuangan/Kepegawaian has 16 titles vs 17 quota values with overwritten top cell).
4. CPNS_BSSN.pdf -> INCLUDED (PENG.102/BSSN/SU/KP.02.01/11/2026 / KepmenPANRB 676/2026: 200 seats).
5. CPNS_KEJAKSAAN_AGUNG.pdf -> INCLUDED PARTIAL VERIFIED ROWS ONLY (KepmenPANRB 638/2026: 6 of 69 lampiran
   pages uploaded = 94 verified rows / 176 seats; missing pages 3-7 & 11-68 are NOT extrapolated).
"""

from __future__ import annotations

import re

EXTRA_INSTANSI = [
    (
        "BPK",
        "Badan Pemeriksa Keuangan",
        "Pusat",
        2531250,
        33240000,
        "Perpres No. 188/2014 (Tukin Resmi Terverifikasi BPK — Simulasi Acuan)",
    ),
    (
        "BSSN",
        "Badan Siber dan Sandi Negara",
        "Pusat",
        2531250,
        33240000,
        "Perpres No. 88/2020 (Tukin Resmi Terverifikasi BSSN — Simulasi Acuan)",
    ),
    (
        "KEJAGUNG",
        "Kejaksaan Agung",
        "Pusat",
        2531250,
        29085000,
        "Perpres No. 29/2020 (Tukin Resmi Terverifikasi Kejaksaan Agung — Simulasi Acuan)",
    ),
    (
        "KEMENKES",
        "Kementerian Kesehatan",
        "Pusat",
        2531250,
        26320000,
        "Perpres No. 109/2016 (Tukin Resmi Terverifikasi Kemenkes — Simulasi Acuan)",
    ),
]

DRIVE_AUDIT_SUMMARY = [
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf",
        "status": "ingested_sscasn_live",
        "instansi": "Badan Pemeriksa Keuangan",
        "referensi": "SSCASN BKN Resmi TA 2026 (Seleksi CASN Nasional 2026 • 27 Nov 2026)",
        "rows_ingested": 51,
        "kuota_ingested": 952,
        "catatan": "Data resmi langsung portal SSCASN BKN (termasuk Jalur Formasi Umum/Disabilitas/Papua & Gaji Resmi BKN Rp 13–19 jt; pelamar belum dirilis).",
    },
    {
        "file_name": "CPNS_BSSN.pdf",
        "status": "ingested",
        "instansi": "Badan Siber dan Sandi Negara",
        "referensi": "PENG.102/BSSN/SU/KP.02.01/11/2026 (KepmenPANRB No. 676/2026)",
        "rows_ingested": 2,
        "kuota_ingested": 200,
        "catatan": "Lampiran I lengkap (196 Umum + 4 Disabilitas).",
    },
    {
        "file_name": "CPNS_KEJAKSAAN_AGUNG.pdf",
        "status": "ingested_partial",
        "instansi": "Kejaksaan Agung",
        "referensi": "KepmenPANRB No. 638/2026 (11 Nov 2026)",
        "rows_ingested": 94,
        "kuota_ingested": 175,
        "catatan": "PDF yang diunggah hanya berisi 6 dari 69 halaman lampiran (hal. 1, 2, 8, 9, 10, 69 dari total 1.660 kursi nasional). Baris hilang tidak direka.",
    },
    {
        "file_name": "CPNS_Kemenkes_Info_STR_.pdf",
        "status": "ingested_no_quota",
        "instansi": "Kementerian Kesehatan",
        "referensi": "SE Dirjen SDMK No. HK.02.02/F/4023/2026 (22 Okt 2026)",
        "rows_ingested": 49,
        "kuota_ingested": 0,
        "catatan": "Dimasukkan sesuai data dokumen persyaratan kualifikasi & STR bagi 30 Jabatan Fungsional Kesehatan (49 kelompok kategori/STR); kolom kuota dibiarkan kosong (NULL/—) karena tidak ada penetapan alokasi.",
    },
    {
        "file_name": "CPNS_Kemenkeu.pdf",
        "status": "skipped_duplicate",
        "instansi": "Kementerian Keuangan",
        "referensi": "KepmenPANRB No. 675/2026 (19 Nov 2026)",
        "rows_ingested": 0,
        "kuota_ingested": 0,
        "catatan": "Duplikat 100% (39/39 hash JPEG identik) dengan dokumen Kemenkeu yang sudah masuk (374 baris / 1.915 kursi). Dilewati agar tidak ganda.",
    },
    {
        "file_name": "CPNS_Polri.pdf",
        "status": "skipped_incomplete_draft",
        "instansi": "Kepolisian Negara Republik Indonesia",
        "referensi": "Paparan Canva Persiapan (24 Nov 2026, merujuk KepmenPANRB No. 653/2026)",
        "rows_ingested": 0,
        "kuota_ingested": 0,
        "catatan": "Paparan estimasi 750 formasi tanpa kolom kualifikasi pendidikan & lokasi penempatan; panel Keuangan/Kepegawaian memiliki 16 jabatan vs 17 angka & angka teratas tumpang tindih sehingga tidak dimasukkan ke tabel terverifikasi.",
    },
]

SUMBER_BSSN = (
    "Pengumuman BSSN No. PENG.102/BSSN/SU/KP.02.01/11/2026 — Seleksi Pengadaan CPNS BSSN TA 2026 "
    "(KepmenPANRB No. 676 Tahun 2026, Tanggal 26 November 2026)"
)

SUMBER_KEJAGUNG = (
    "KepmenPANRB No. 638 Tahun 2026 — Penetapan Kebutuhan PNS Kejaksaan Agung RI TA 2026 "
    "(11 November 2026 • Lampiran Parsial Hal. 1, 2, 8, 9, 10, 69 dari 69)"
)

_BSSN_PENDIDIKAN = (
    "SMA IPA (atau semua jurusan jika Kurikulum Merdeka) | "
    "Madrasah Aliyah IPA (atau semua jurusan jika Kurikulum Merdeka) | "
    "SMK Komputer | "
    "SMK Teknik Elektronika Industri | "
    "SMK Teknik Elektronika Komunikasi | "
    "SMK Elektronika | "
    "SMK Elektro | "
    "SMK Informatika Jurusan Komputer Teknik Jaringan | "
    "SMK Rekayasa Perangkat Lunak | "
    "SMK Audio Video | "
    "SMK Teknik Audio Video | "
    "SMK Teknik Informatika | "
    "SMK Teknik Informasi dan Komunikasi"
)


def _format_unit_eselon1(raw_seg: str) -> str:
    return re.sub(r"\bDan\b", "dan", raw_seg.strip().title())


def get_bssn_rows(extract_jenjang_fn) -> list[dict]:
    rows = []
    for no, jenis, kuota in [(1, "UMUM", 196), (2, "PENYANDANG DISABILITAS", 4)]:
        rows.append(
            {
                "no_urut": no,
                "formasi_id": f"2026-BSSN-001-{jenis.split()[-1]}",
                "instansi_id": "BSSN",
                "instansi_nm": "Badan Siber dan Sandi Negara",
                "kategori_instansi": "Pusat",
                "unit_eselon1": "Badan Siber dan Sandi Negara (Sekretariat Utama)",
                "jabatan_nm": "PENGADMINISTRASI PERKANTORAN",
                "pendidikan_nm": _BSSN_PENDIDIKAN,
                "jenjang": extract_jenjang_fn(_BSSN_PENDIDIKAN),
                "jumlah_formasi": kuota,
                "lokasi_nm": "BSSN | JAKARTA / DEPOK / BOGOR / YOGYAKARTA / BATAM",
                "jenis_formasi": jenis,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_BSSN,
            }
        )
    return rows


_PEND_APOTEKER = "PROFESI APOTEKER"
_PEND_ASISTEN_APOTEKER = "D-III FARMASI"
_PEND_SUBSPESIALIS = (
    "DOKTER SUBSPESIALIS NEUROLOGI-NEUROVASKULAR, NEUROINTERVENSI, IMAGING, OTOLOGI, OFTALMOLOGI"
)
_PEND_PSIKOLOG = "PROFESI PSIKOLOGI (MINAT PSIKOLOGI KLINIS)"
_PEND_TERAPIS_GIGI = (
    "D-III KEPERAWATAN GIGI | D-III KESEHATAN GIGI | D-III KESEHATAN GIGI DAN MULUT | D-III TERAPIS GIGI DAN MULUT"
)
_PEND_JAKSA = "S-1 ILMU HUKUM | S-1 HUKUM"
_PEND_SANDIMAN = (
    "S-1 ILMU KOMPUTER | S-1 INFORMATIKA | S-1 TEKNIK INFORMATIKA | S-1 TEKNOLOGI INFORMASI | "
    "S-1 SISTEM INFORMASI | S-1 SISTEM KOMPUTER | S-1 TEKNIK KOMPUTER | "
    "D-IV KEAMANAN SISTEM INFORMASI | D-IV REKAYASA KEAMANAN SIBER | D-IV REKAYASA KRIPTOGRAFI | "
    "D-IV REKAYASA PERANGKAT KERAS KOMPUTER | D-IV TEKNIK KOMPUTER | D-IV TEKNIK KOMPUTER DAN JARINGAN"
)


# Tuple structure: (bagian_kode, no_urut, jabatan_nm, pendidikan_nm, jumlah_formasi, unit_penempatan)
_KEJAGUNG_RAW: list[tuple[str, int, str, str, int, str]] = [
    # Halaman 1 dari 69 — B | TENAGA KESEHATAN (NO 1..17)
    ("B", 1, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN BANGKA BELITUNG | KLINIK ADHYAKSA KEJAKSAAN TINGGI KEPULAUAN BANGKA BELITUNG"),
    ("B", 2, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU UTARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU UTARA"),
    ("B", 3, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 3, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | KLINIK ADHYAKSA PUSAT KESEHATAN YUSTISIAL"),
    ("B", 4, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI BARAT"),
    ("B", 5, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI JAWA BARAT"),
    ("B", 6, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU"),
    ("B", 7, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI NUSA TENGGARA TIMUR | KLINIK ADHYAKSA KEJAKSAAN TINGGI NUSA TENGGARA TIMUR"),
    ("B", 8, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN RIAU | KLINIK ADHYAKSA KEJAKSAAN TINGGI KEPULAUAN RIAU"),
    ("B", 9, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI TENGGARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI TENGGARA"),
    ("B", 10, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI DAERAH ISTIMEWA YOGYAKARTA | KLINIK ADHYAKSA KEJAKSAAN TINGGI DAERAH ISTIMEWA YOGYAKARTA"),
    ("B", 11, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI PAPUA BARAT"),
    ("B", 12, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 4, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA JAKARTA"),
    ("B", 13, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 2, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA JAMBI"),
    ("B", 14, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI GORONTALO | KLINIK ADHYAKSA KEJAKSAAN TINGGI GORONTALO"),
    ("B", 15, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 2, "KEJAKSAAN AGUNG | BADAN PENDIDIKAN DAN PELATIHAN | KLINIK ADHYAKSA BADAN PENDIDIKAN DAN PELATIHAN KEJAKSAAN AGUNG"),
    ("B", 16, "APOTEKER AHLI PERTAMA", _PEND_APOTEKER, 4, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA JAWA TIMUR"),
    ("B", 17, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KALIMANTAN SELATAN | KLINIK ADHYAKSA KEJAKSAAN TINGGI KALIMANTAN SELATAN"),
    # Halaman 2 dari 69 — B | TENAGA KESEHATAN (NO 18..37)
    ("B", 18, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU UTARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU UTARA"),
    ("B", 19, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU"),
    ("B", 20, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI UTARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI UTARA"),
    ("B", 21, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI BARAT"),
    ("B", 22, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI GORONTALO | KLINIK ADHYAKSA KEJAKSAAN TINGGI GORONTALO"),
    ("B", 23, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI DAERAH ISTIMEWA YOGYAKARTA | KLINIK ADHYAKSA KEJAKSAAN TINGGI DAERAH ISTIMEWA YOGYAKARTA"),
    ("B", 24, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BALI | KLINIK ADHYAKSA KEJAKSAAN TINGGI BALI"),
    ("B", 25, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KALIMANTAN TENGAH | KLINIK ADHYAKSA KEJAKSAAN TINGGI KALIMANTAN TENGAH"),
    ("B", 26, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 2, "KEJAKSAAN AGUNG | BADAN PENDIDIKAN DAN PELATIHAN | KLINIK ADHYAKSA BADAN PENDIDIKAN DAN PELATIHAN KEJAKSAAN AGUNG"),
    ("B", 27, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI TENGGARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI TENGGARA"),
    ("B", 28, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BENGKULU | KLINIK ADHYAKSA KEJAKSAAN TINGGI BENGKULU"),
    ("B", 29, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI PAPUA BARAT"),
    ("B", 30, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN RIAU | KLINIK ADHYAKSA KEJAKSAAN TINGGI KEPULAUAN RIAU"),
    ("B", 31, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI NUSA TENGGARA BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI NUSA TENGGARA BARAT"),
    ("B", 32, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA | KLINIK ADHYAKSA KEJAKSAAN TINGGI PAPUA"),
    ("B", 33, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 3, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | KLINIK ADHYAKSA PUSAT KESEHATAN YUSTISIAL"),
    ("B", 34, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN BANGKA BELITUNG | KLINIK ADHYAKSA KEJAKSAAN TINGGI KEPULAUAN BANGKA BELITUNG"),
    ("B", 35, "ASISTEN APOTEKER TERAMPIL", _PEND_ASISTEN_APOTEKER, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI TENGAH | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI TENGAH"),
    ("B", 36, "DOKTER AHLI MUDA - DOKTER SUB SPESIALIS NEUROLOGI-NEUROVASKULAR, NEUROINTERVENSI, IMAGING, OTOLOGI, OFTALMOLOGI", _PEND_SUBSPESIALIS, 1, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA JAWA TIMUR"),
    ("B", 37, "DOKTER AHLI MUDA - DOKTER SUB SPESIALIS NEUROLOGI-NEUROVASKULAR, NEUROINTERVENSI, IMAGING, OTOLOGI, OFTALMOLOGI", _PEND_SUBSPESIALIS, 1, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA BANTEN"),
    # Halaman 8 dari 69 — B | TENAGA KESEHATAN (NO 147..155)
    ("B", 147, "PSIKOLOG KLINIS AHLI PERTAMA", _PEND_PSIKOLOG, 2, "KEJAKSAAN AGUNG | PUSAT KESEHATAN YUSTISIAL | RUMAH SAKIT ADHYAKSA JAWA TIMUR"),
    ("B", 148, "PSIKOLOG KLINIS AHLI PERTAMA", _PEND_PSIKOLOG, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KLINIK ADHYAKSA KEJAKSAAN TINGGI JAWA TENGAH"),
    ("B", 149, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU"),
    ("B", 150, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI NUSA TENGGARA TIMUR | KLINIK ADHYAKSA KEJAKSAAN TINGGI NUSA TENGGARA TIMUR"),
    ("B", 151, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA | KLINIK ADHYAKSA KEJAKSAAN TINGGI PAPUA"),
    ("B", 152, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI SULAWESI BARAT"),
    ("B", 153, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA BARAT | KLINIK ADHYAKSA KEJAKSAAN TINGGI PAPUA BARAT"),
    ("B", 154, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU UTARA | KLINIK ADHYAKSA KEJAKSAAN TINGGI MALUKU UTARA"),
    ("B", 155, "TERAPIS GIGI DAN MULUT TERAMPIL", _PEND_TERAPIS_GIGI, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI GORONTALO | KLINIK ADHYAKSA KEJAKSAAN TINGGI GORONTALO"),
    # Halaman 9 dari 69 — C | TENAGA TEKNIS (NO 1..24)
    ("C", 1, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI CIMAHI"),
    ("C", 2, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KEJAKSAAN NEGERI SURAKARTA"),
    ("C", 3, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KALIMANTAN SELATAN | KEJAKSAAN NEGERI HULU SUNGAI UTARA"),
    ("C", 4, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TIMUR | KEJAKSAAN NEGERI BOJONEGORO"),
    ("C", 5, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KEJAKSAAN NEGERI KABUPATEN TEGAL"),
    ("C", 6, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KEJAKSAAN NEGERI KOTA SEMARANG"),
    ("C", 7, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI KABUPATEN TASIKMALAYA"),
    ("C", 8, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KEJAKSAAN NEGERI KOTA PEKALONGAN"),
    ("C", 9, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI KOTA SUKABUMI"),
    ("C", 10, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TENGAH | KEJAKSAAN NEGERI KOTA MAGELANG"),
    ("C", 11, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI KOTA CIREBON"),
    ("C", 12, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI KABUPATEN SUKABUMI"),
    ("C", 13, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BENGKULU | KEJAKSAAN NEGERI KAUR"),
    ("C", 14, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SUMATERA SELATAN | KEJAKSAAN NEGERI OGAN KOMERING ILIR"),
    ("C", 15, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAMBI | KEJAKSAAN NEGERI TEBO"),
    ("C", 16, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BENGKULU | KEJAKSAAN NEGERI BENGKULU UTARA"),
    ("C", 17, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAMBI | KEJAKSAAN NEGERI MERANGIN"),
    ("C", 18, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI CIANJUR"),
    ("C", 19, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA BARAT | KEJAKSAAN NEGERI KABUPATEN BOGOR"),
    ("C", 20, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAMBI | KEJAKSAAN NEGERI JAMBI"),
    ("C", 21, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI RIAU | KEJAKSAAN NEGERI KAMPAR"),
    ("C", 22, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI RIAU | KEJAKSAAN NEGERI PEKANBARU"),
    ("C", 23, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI ACEH | KEJAKSAAN NEGERI LHOKSEUMAWE"),
    ("C", 24, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SUMATERA UTARA | KEJAKSAAN NEGERI ASAHAN"),
    # Halaman 10 dari 69 — C | TENAGA TEKNIS (NO 25..47)
    ("C", 25, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SUMATERA SELATAN | KEJAKSAAN NEGERI OGAN KOMERING ULU TIMUR"),
    ("C", 26, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SUMATERA UTARA | KEJAKSAAN NEGERI LABUHAN BATU"),
    ("C", 27, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BANTEN | KEJAKSAAN NEGERI KABUPATEN TANGERANG"),
    ("C", 28, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU UTARA | KEJAKSAAN NEGERI TERNATE"),
    ("C", 29, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA | KEJAKSAAN NEGERI JAYAPURA"),
    ("C", 30, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BALI | KEJAKSAAN NEGERI DENPASAR"),
    ("C", 31, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI SELATAN | KEJAKSAAN NEGERI MAKASSAR"),
    ("C", 32, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI TENGGARA | KEJAKSAAN NEGERI BAU-BAU"),
    ("C", 33, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN RIAU | KEJAKSAAN NEGERI BATAM"),
    ("C", 34, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI NUSA TENGGARA BARAT | KEJAKSAAN NEGERI MATARAM"),
    ("C", 35, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KALIMANTAN TIMUR | KEJAKSAAN NEGERI KUTAI KARTANEGARA"),
    ("C", 36, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI JAWA TIMUR | KEJAKSAAN NEGERI TANJUNG PERAK"),
    ("C", 37, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI TENGAH | KEJAKSAAN NEGERI PALU"),
    ("C", 38, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA BARAT | KEJAKSAAN NEGERI SORONG"),
    ("C", 39, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI PAPUA BARAT | KEJAKSAAN NEGERI MANOKWARI"),
    ("C", 40, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI GORONTALO | KEJAKSAAN NEGERI KOTA GORONTALO"),
    ("C", 41, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KEPULAUAN RIAU | KEJAKSAAN NEGERI TANJUNG PINANG"),
    ("C", 42, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BANTEN | KEJAKSAAN NEGERI TANGERANG SELATAN"),
    ("C", 43, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BANTEN | KEJAKSAAN NEGERI KOTA TANGERANG"),
    ("C", 44, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI MALUKU | KEJAKSAAN NEGERI AMBON"),
    ("C", 45, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI SULAWESI SELATAN | KEJAKSAAN NEGERI PALOPO"),
    ("C", 46, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 3, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI BALI | KEJAKSAAN NEGERI BADUNG"),
    ("C", 47, "JAKSA AHLI PERTAMA", _PEND_JAKSA, 2, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI KALIMANTAN TIMUR | KEJAKSAAN NEGERI BALIKPAPAN"),
    # Halaman 69 dari 69 — C | TENAGA TEKNIS (NO 943)
    ("C", 943, "SANDIMAN AHLI PERTAMA", _PEND_SANDIMAN, 1, "KEJAKSAAN AGUNG | KEJAKSAAN TINGGI RIAU | KEJAKSAAN NEGERI ROKAN HILIR"),
]


def get_kejagung_rows(extract_jenjang_fn) -> list[dict]:
    rows = []
    for bag, no, jab, pend, kuota, unit in _KEJAGUNG_RAW:
        segs = [s.strip() for s in unit.split("|") if s.strip()]
        eselon1 = _format_unit_eselon1(segs[1]) if len(segs) >= 2 else "Kejaksaan Agung"
        rows.append(
            {
                "no_urut": no,
                "formasi_id": f"2026-KEJAGUNG-{bag}-{no:03d}",
                "instansi_id": "KEJAGUNG",
                "instansi_nm": "Kejaksaan Agung",
                "kategori_instansi": "Pusat",
                "unit_eselon1": eselon1,
                "jabatan_nm": jab,
                "pendidikan_nm": pend,
                "jenjang": extract_jenjang_fn(pend),
                "jumlah_formasi": kuota,
                "lokasi_nm": unit,
                "jenis_formasi": None,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_KEJAGUNG,
            }
        )
    return rows


_INSTANSI_CODE_MAP = {
    "Badan Pemeriksa Keuangan": "BPK",
    "Kementerian Keuangan": "KEMENKEU",
    "Badan Siber dan Sandi Negara": "BSSN",
    "Kejaksaan Agung": "KEJAGUNG",
}

SUMBER_SSCASN = (
    "SSCASN BKN Resmi TA 2026 — Seleksi CASN Nasional 2026 "
    "(api-rekrutmen.bkn.go.id/portal/api/spf)"
)


def _sscasn_instansi_id(instansi_nm: str) -> str:
    if instansi_nm in _INSTANSI_CODE_MAP:
        return _INSTANSI_CODE_MAP[instansi_nm]
    slug = re.sub(r"[^A-Z0-9]+", "_", instansi_nm.upper()).strip("_")
    return f"KL_{slug[:24]}"


def _sscasn_kategori(instansi_nm: str) -> str:
    n = instansi_nm.strip()
    if n.startswith("Pemerintah Provinsi"):
        return "Provinsi"
    if n.startswith("Pemerintah Kab.") or n.startswith("Pemerintah Kota"):
        return "Kabupaten/Kota"
    return "Pusat"


def get_sscasn_live_rows(extract_jenjang_fn, csv_path) -> list[dict]:
    """Load official SSCASN 2026 CPNS rows saved by the live scraper without inventing missing pelamar."""
    import csv

    if not csv_path.exists():
        return []
    rows = []
    per_agency_counter: dict[str, int] = {}
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            jp = (r.get("jenis_pengadaan") or "").strip().lower()
            if "cpns" not in jp and "nasional" not in (r.get("nama_event") or "").lower():
                continue
            if "pppk" in jp and "cpns" not in jp:
                continue

            instansi_nm = (r.get("instansi") or "").strip()
            instansi_id = _sscasn_instansi_id(instansi_nm)
            per_agency_counter[instansi_id] = per_agency_counter.get(instansi_id, 0) + 1
            no = per_agency_counter[instansi_id]

            lokasi_nm = re.sub(r"\s+", " ", (r.get("lokasi_formasi") or "").strip())
            segs = [s.strip() for s in lokasi_nm.split("|") if s.strip()]
            if len(segs) >= 2:
                eselon1 = _format_unit_eselon1(segs[1]).replace("Bpk Ri", "BPK RI")
            else:
                eselon1 = lokasi_nm or instansi_nm

            raw_pend = (r.get("nama_pendidikan") or r.get("group_pendidikan") or "").strip()
            pend_nm = re.sub(r"\s+/\s+", " | ", raw_pend)
            pend_nm = " | ".join(p.strip() for p in pend_nm.split("|") if p.strip())

            jabatan_nm = re.sub(r"\s+", " ", (r.get("nama_jabatan") or "").strip()).upper()
            jenis_formasi = (r.get("jenis_formasi") or "").strip() or None
            kuota = int(float(r.get("jumlah") or 0))
            gmin_raw = int(float(r.get("penghasilan_min") or 0))
            gmax_raw = int(float(r.get("penghasilan_max") or 0))
            gaji_min = gmin_raw if gmin_raw > 0 else None
            gaji_max = gmax_raw if gmax_raw > 0 else None

            rows.append(
                {
                    "no_urut": no,
                    "formasi_id": (r.get("id") or f"2026-{instansi_id}-{no:03d}").strip(),
                    "instansi_id": instansi_id,
                    "instansi_nm": instansi_nm,
                    "kategori_instansi": _sscasn_kategori(instansi_nm),
                    "unit_eselon1": eselon1,
                    "jabatan_nm": jabatan_nm,
                    "pendidikan_nm": pend_nm,
                    "jenjang": extract_jenjang_fn(pend_nm),
                    "jumlah_formasi": kuota,
                    "lokasi_nm": lokasi_nm,
                    "jenis_formasi": jenis_formasi,
                    "jumlah_pelamar": None,
                    "rasio_kompetisi": None,
                    "peluang_lolos_pct": None,
                    "status_keketatan": None,
                    "gaji_min": gaji_min,
                    "gaji_max": gaji_max,
                    "sumber_dokumen": SUMBER_SSCASN,
                }
            )
    return rows


SUMBER_KEMENKES_STR = (
    "SE Dirjen SDMK Kemenkes No. HK.02.02/F/4023/2026 — "
    "Persyaratan Kualifikasi Pendidikan & STR CASN JF Kesehatan TA 2026 (22 Oktober 2026)"
)


def _parse_kemenkes_pend_and_note(raw_pend: str) -> tuple[str, str]:
    s = re.sub(r"\s+", " ", raw_pend).strip()
    note = ""
    if "Catatan:" in s:
        s, note_part = s.split("Catatan:", 1)
        s = s.strip()
        note = "Catatan: " + note_part.strip()
    s = re.sub(r"^(?:S-1 Sarjana Bidang Kesehatan/[^:]+:|Diploma III Bidang Kesehatan:)\s*", "", s)
    s = re.sub(r"^1\.\s*", "", s)
    parts = re.split(r"\s+\d+\.\s+", s)
    cleaned = [p.strip(" ;,") for p in parts if p.strip(" ;,")]
    return " | ".join(cleaned), note


def get_kemenkes_str_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 49 STR/qualification groups for 30 health functional positions from SE HK.02.02/F/4023/2026.

    Leaves jumlah_formasi, jenis_formasi, pelamar, and gaji_min/max strictly None (NULL) because the
    circular regulates eligibility & STR requirements without publishing seat quotas.
    """
    import json

    if not json_path.exists():
        return []
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    grouped: list[dict] = []
    cur_no = cur_jab = cur_kat = ""
    for _pg, r in raw:
        if r[0] == "No" or (len(r) >= 5 and r[4] == "YA"):
            continue
        no, jab, kat, pend, ya, no_str = [str(x or "").strip() for x in r]
        if no:
            cur_no = no
        if jab:
            cur_jab = jab
        if kat:
            cur_kat = kat
        new_str = "YA" if ya else ("TIDAK" if no_str else "")
        if no or kat or (new_str and grouped and grouped[-1]["str"] != new_str and not no and not kat):
            grouped.append(
                {
                    "no": int(cur_no),
                    "jab": cur_jab,
                    "kat": cur_kat,
                    "str": new_str or grouped[-1]["str"],
                    "pend_parts": [pend],
                }
            )
        else:
            grouped[-1]["pend_parts"].append(pend)

    rows = []
    for idx, g in enumerate(grouped, 1):
        pend_nm, note = _parse_kemenkes_pend_and_note(" ".join(g["pend_parts"]))
        jab_clean = re.sub(r"\s+", " ", g["jab"]).strip().upper()
        kat = g["kat"].strip()
        str_label = "YA (Wajib STR)" if g["str"] == "YA" else "TIDAK (Tanpa STR)"
        lok = f"Ketentuan Nasional JF Kesehatan ({kat}) | Syarat STR: {str_label}"
        if note:
            lok += f" | {note}"
        rows.append(
            {
                "no_urut": g["no"],
                "formasi_id": f"2026-KEMENKES-{g['no']:02d}-{kat[:4].upper()}-{g['str']}",
                "instansi_id": "KEMENKES",
                "instansi_nm": "Kementerian Kesehatan",
                "kategori_instansi": "Pusat",
                "unit_eselon1": f"JF Kesehatan — {kat} (Syarat STR: {g['str']})",
                "jabatan_nm": jab_clean,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": None,
                "lokasi_nm": lok,
                "jenis_formasi": None,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_KEMENKES_STR,
            }
        )
    return rows


def _classify_keketatan_2024(kursi: int, pelamar: int) -> tuple[float, float, str]:
    """Match cpns2024.db classification thresholds cleanly without rounding drift."""
    if not kursi or kursi <= 0:
        return 0.0, 0.0, "Tanpa Formasi"
    if not pelamar or pelamar <= 0:
        return 0.0, 100.0, "Tanpa Pelamar"
    rasio = round(pelamar / kursi, 2)
    peluang = round(min(100.0, (kursi / pelamar) * 100.0), 2)
    if rasio <= 1.0:
        status = "Sangat Longgar"
    elif rasio <= 15.0:
        status = "Moderat"
    else:
        status = "Sangat Ketat"
    return rasio, peluang, status


def _norm_bpk_region(lokasi: str) -> str:
    up = re.sub(r"\s+", " ", (lokasi or "").upper()).strip()
    if up.startswith("REGIONAL SULAWESI"):
        return "REGIONAL SULAWESI_MALUKU_PAPUA_BALI_NUSRA"
    if up.startswith("REGIONAL "):
        return up
    return ""


def compute_2024_comparison_map(rows_2026: list[dict], cpns2024_db_path) -> dict[str, dict]:
    """Compute historical CPNS 2024 comparison records per 2026 formasi_id from cpns2024.db."""
    import sqlite3

    result: dict[str, dict] = {}
    if not cpns2024_db_path.exists():
        for r in rows_2026:
            result[r["formasi_id"]] = {
                "formasi_id": r["formasi_id"],
                "match_level_2024": None,
                "match_label_2024": "Tidak ada pembanding di 2024",
                "kursi_2024": None,
                "pelamar_2024": None,
                "rasio_2024": None,
                "peluang_2024_pct": None,
                "status_keketatan_2024": None,
                "row_count_2024": 0,
            }
        return result

    c24 = sqlite3.connect(f"file:{cpns2024_db_path}?mode=ro", uri=True)
    try:
        inst_map = {
            r[1].strip().lower(): r[0]
            for r in c24.execute("SELECT instansi_id, nama_instansi FROM instansi").fetchall()
        }
        # Preload 2024 formasi rows only for agencies present in 2026
        needed_iids = {inst_map.get(r["instansi_nm"].strip().lower()) for r in rows_2026}
        needed_iids.discard(None)

        by_inst_jab: dict[tuple[int, str], list[tuple[str, str, int, int]]] = {}
        by_inst_all: dict[int, list[tuple[str, int, int]]] = {}
        if needed_iids:
            placeholders = ",".join("?" for _ in needed_iids)
            q_rows = c24.execute(
                f"""
                SELECT instansi_id, UPPER(jabatan_nm), lokasi_nm, jenis_formasi,
                       COALESCE(jumlah_formasi, 0), COALESCE(jumlah_pelamar, 0)
                FROM formasi
                WHERE instansi_id IN ({placeholders})
                """,
                list(needed_iids),
            ).fetchall()
            for iid, jab, lok, jf, k, p in q_rows:
                by_inst_jab.setdefault((iid, jab), []).append((lok or "", jf or "", int(k), int(p)))
                by_inst_all.setdefault(iid, []).append((jab, int(k), int(p)))

        for r in rows_2026:
            fid = r["formasi_id"]
            iid = inst_map.get(r["instansi_nm"].strip().lower())
            jab26 = (r.get("jabatan_nm") or "").strip().upper()
            matched_rows: list[tuple[int, int]] = []
            match_level = None
            match_label = "Tidak ada pembanding di 2024"

            if iid is not None:
                reg26 = _norm_bpk_region(r.get("lokasi_nm") or "")
                exact_list = by_inst_jab.get((iid, jab26), [])

                # Tier 1: Same Instansi + Exact Jabatan + Same Regional (e.g., BPK Regional)
                if exact_list and reg26:
                    reg_matches = [
                        (k, p, jf)
                        for lok, jf, k, p in exact_list
                        if _norm_bpk_region(lok) == reg26
                    ]
                    if reg_matches:
                        jf26 = (r.get("jenis_formasi") or "").upper()
                        same_jf = [(k, p) for k, p, jf in reg_matches if jf26 and jf.upper() == jf26]
                        if same_jf:
                            matched_rows = same_jf
                            match_level = "regional_exact"
                            match_label = f"Regional & jalur sama di 2024 ({jf26})"
                        else:
                            matched_rows = [(k, p) for k, p, _ in reg_matches]
                            match_level = "regional_exact"
                            match_label = "Regional sama di 2024 (jalur Umum)" if jf26 else "Regional sama di 2024"

                # Tier 2: Same Instansi + Exact Jabatan (Kemenkeu Kapal, Kejagung, BPK Analis Kerja Sama)
                if not matched_rows and exact_list:
                    matched_rows = [(k, p) for _, _, k, p in exact_list]
                    match_level = "instansi_jabatan"
                    match_label = "Jabatan sama di instansi yang sama (2024)"

                # Tier 3: Kemenkes SE STR JF Rumpun + Kategori (Keahlian vs Keterampilan)
                if not matched_rows and r["instansi_id"] == "KEMENKES":
                    ue1 = r.get("unit_eselon1") or ""
                    kat = "Keahlian" if "Keahlian" in ue1 else "Keterampilan"
                    clean = re.sub(r"\(\*\)", "", jab26).replace("*", "").strip()
                    aliases = [a.strip() for a in clean.split("/") if a.strip()]
                    kat_rows: list[tuple[int, int]] = []
                    for jab24, k24, p24 in by_inst_all.get(iid, []):
                        if kat == "Keahlian" and any(t in jab24 for t in ("TERAMPIL", "PEMULA", "MAHIR", "PENYELIA")):
                            continue
                        if kat == "Keterampilan" and any(t in jab24 for t in ("AHLI", "SPESIALIS", "DOKTER")):
                            continue
                        for al in aliases:
                            if (
                                jab24 == al
                                or jab24.startswith(al + " ")
                                or jab24.startswith(al + " -")
                            ):
                                kat_rows.append((k24, p24))
                                break
                    if kat_rows:
                        matched_rows = kat_rows
                        match_level = "instansi_jf_kategori"
                        match_label = f"Rumpun JF {kat} Kemenkes di 2024 (rekap unit)"

            if matched_rows:
                kursi24 = sum(k for k, _ in matched_rows)
                pelamar24 = sum(p for _, p in matched_rows)
                if kursi24 > 0:
                    rasio24, peluang24, status24 = _classify_keketatan_2024(kursi24, pelamar24)
                    result[fid] = {
                        "formasi_id": fid,
                        "match_level_2024": match_level,
                        "match_label_2024": match_label,
                        "kursi_2024": kursi24,
                        "pelamar_2024": pelamar24,
                        "rasio_2024": rasio24,
                        "peluang_2024_pct": peluang24,
                        "status_keketatan_2024": status24,
                        "row_count_2024": len(matched_rows),
                    }
                    continue

            result[fid] = {
                "formasi_id": fid,
                "match_level_2024": None,
                "match_label_2024": "Tidak ada pembanding di 2024",
                "kursi_2024": None,
                "pelamar_2024": None,
                "rasio_2024": None,
                "peluang_2024_pct": None,
                "status_keketatan_2024": None,
                "row_count_2024": 0,
            }
    finally:
        c24.close()

    return result



