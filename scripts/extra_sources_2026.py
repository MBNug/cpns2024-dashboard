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
    (
        "BPKP",
        "Badan Pengawasan Keuangan dan Pembangunan",
        "Pusat",
        2575000,
        41550000,
        "Perpres No. 34/2023 (Tukin Resmi Terverifikasi BPKP — Simulasi Acuan)",
    ),
    (
        "KEMENKUM",
        "Kementerian Hukum",
        "Pusat",
        2531250,
        27577500,
        "Perpres No. 130/2017 (Tukin Resmi Terverifikasi Kemenkum / eks Kemenkumham — Simulasi Acuan)",
    ),
    (
        "KEMENKOP",
        "Kementerian Koperasi",
        "Pusat",
        2531250,
        33240000,
        "Standar Tunjangan Kinerja K/L (Kementerian Koperasi / eks Kemenkop UKM — Simulasi Acuan)",
    ),
    (
        "MA",
        "Mahkamah Agung RI",
        "Pusat",
        2531250,
        37560000,
        "Perpres No. 8/2020 (Tukin Resmi Terverifikasi Mahkamah Agung RI — Simulasi Acuan)",
    ),
    (
        "KEMENHAM",
        "Kementerian Hak Asasi Manusia",
        "Pusat",
        2531250,
        27577500,
        "Perpres No. 130/2017 (Tukin Resmi Terverifikasi Kemenham / eks Kemenkumham — Simulasi Acuan)",
    ),
    (
        "POLRI",
        "Kepolisian Negara Republik Indonesia",
        "Pusat",
        2531250,
        24930000,
        "Estimasi Kisaran Standar KemenPAN-RB (Polri — Simulasi Acuan)",
    ),
    (
        "KEMENHUT",
        "Kementerian Kehutanan",
        "Pusat",
        2531250,
        33240000,
        "Perpres No. 121/2017 (Tukin Resmi Terverifikasi Kemenhut / eks KLHK — Simulasi Acuan)",
    ),
    (
        "KKP",
        "Kementerian Kelautan dan Perikanan",
        "Pusat",
        2531250,
        33240000,
        "Perpres No. 136/2017 (Tukin Resmi Terverifikasi KKP — Simulasi Acuan)",
    ),
    (
        "BGN",
        "Badan Gizi Nasional",
        "Pusat",
        2531250,
        24930000,
        "Estimasi Kisaran Standar KemenPAN-RB (Badan Gizi Nasional — Simulasi Acuan)",
    ),
]

DRIVE_AUDIT_SUMMARY = [
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + BPK.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Badan Pemeriksa Keuangan",
        "referensi": "SSCASN BKN Live + Pengumuman BPK No. 01/B/S.Peng/SETJEN/KPG.02.01/11/2026 (KepmenPANRB No. 641/2026)",
        "rows_ingested": 51,
        "kuota_ingested": 952,
        "catatan": "Data resmi SSCASN BKN (termasuk Jalur Formasi Umum/Disabilitas/Papua & Gaji Resmi BKN Rp 13–19 jt; pelamar belum dirilis). File BPK.pdf di Drive memuat total alokasi identik 952 kursi sehingga tidak digandakan.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + KKP.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kementerian Kelautan dan Perikanan",
        "referensi": "SSCASN BKN Live + Pengumuman Sekjen KKP No. B.1389/SJ/KP.310/XI/2026 (27 Nov 2026)",
        "rows_ingested": 606,
        "kuota_ingested": 2132,
        "catatan": "Data resmi SSCASN BKN Live lengkap 606 baris penempatan unit KKP seluruh Indonesia (2.091 Umum, 35 Putra/Putri Papua, 6 Penyandang Disabilitas) beserta Gaji Resmi BKN Rp 5,0–8,8 jt, usia 18–35 th, uraian tugas, dokumen/sertifikasi khusus per formasi, serta aturan lengkap Pengumuman B.1389/SJ/KP.310/XI/2026 (tanpa ambang IPK minimal, bobot SKB 50% CAT + 50% Tambahan, ikatan dinas 5 tahun).",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Pengumuman BGN 001/PANSELNAS.BGN/XI/2026",
        "status": "ingested_sscasn_live",
        "instansi": "Badan Gizi Nasional",
        "referensi": "SSCASN BKN Live + Pengumuman BGN No. 001/PANSELNAS.BGN/XI/2026 (28 Nov 2026)",
        "rows_ingested": 552,
        "kuota_ingested": 1618,
        "catatan": "Data resmi SSCASN BKN Live lengkap 552 baris penempatan KPPG Kelas II & Pusat Badan Gizi Nasional (1.563 Umum, 33 Disabilitas, 16 Lulusan Terbaik, 6 Putra/Putri Papua) beserta Gaji Resmi BKN Rp 6,36–8,73 jt, usia 18–35 th, uraian tugas, berkas SSCASN, serta aturan Pengumuman 001/PANSELNAS.BGN/XI/2026 (IPK min. 3,00 Umum / 2,75 Disabilitas & Papua, akreditasi PT & prodi min. B/Baik Sekali, SKB CAT BKN, tidak pindah min. 5 tahun).",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Kemenkop.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kementerian Koperasi",
        "referensi": "SSCASN BKN Live + Pengumuman Kemenkop No. 12/Pum/SM.KOP/2026 (KepmenPANRB No. 642/2026)",
        "rows_ingested": 274,
        "kuota_ingested": 986,
        "catatan": "Data resmi SSCASN BKN Live lengkap 274 baris penempatan unit Deputi/Inspektorat/Setmen (936 Umum, 10 Lulusan Terbaik, 20 Disabilitas, 20 Putra/Putri Papua; Gaji Resmi BKN Rp 5,0–8,3 jt; pelamar belum dirilis). Berkas Kemenkop.pdf di Drive memuat total identik 986 kursi sehingga tidak digandakan.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + BPKP_PENGUMUMAN/RINCIAN/ALOKASI.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Badan Pengawasan Keuangan dan Pembangunan",
        "referensi": "SSCASN BKN Live + Pengumuman BPKP No. KP.00.01/PENG-2/SU/02/2026 (KepmenPANRB No. 640/2026)",
        "rows_ingested": 27,
        "kuota_ingested": 2007,
        "catatan": "Data resmi SSCASN BKN Live 27 baris rumpun pelamaran nasional dengan total identik 2.007 kursi (1.966 Umum, 41 Penyandang Disabilitas) beserta Gaji Resmi BKN Rp 7,7–11,5 jt. Menggantikan 554 baris rincian unit PDF pra-rilis agar sesuai struktur pendaftaran SSCASN tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Kemenkum.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kementerian Hukum",
        "referensi": "SSCASN BKN Live + Pengumuman Kemenkum No. SEK.2-KP.02.01-326 (KepmenPANRB No. 647/2026)",
        "rows_ingested": 53,
        "kuota_ingested": 1297,
        "catatan": "Data resmi SSCASN BKN Live lengkap 53 baris penempatan (Unit Utama, Kantor Wilayah, Ditjen KI, Ditjen PP, BPSDM/Poltek Pengayoman) dengan total 1.297 kursi identik pengumuman (1.219 Umum, 26 Lulusan Terbaik, 26 Disabilitas, 26 Putra/Putri Papua) beserta Gaji Resmi BKN Rp 5,3–9,8 jt. Menggantikan Kemenkum.pdf pra-rilis tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Mahkamah Agung.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Mahkamah Agung RI",
        "referensi": "SSCASN BKN Live + Pengumuman Sekretaris MA No. 34/SEK/PENG.KP1.1.2/XI/2026 (KepmenPANRB No. 643/2026)",
        "rows_ingested": 22,
        "kuota_ingested": 4430,
        "catatan": "Data resmi SSCASN BKN Live lengkap 22 baris (18 kode formasi, 4.321 Umum, 89 Disabilitas, 20 Putra/Putri Papua) termasuk Analis Perkara Peradilan / Calon Hakim (1.600 kursi), PSTI (716), dan Pengadministrasi Perkantoran / PTP (906), beserta Gaji Resmi BKN Rp 2,5–10,9 jt. Menggantikan Mahkamah Agung.pdf pra-rilis tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Kemenham.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kementerian Hak Asasi Manusia",
        "referensi": "SSCASN BKN Live + Pengumuman Kemenham No. SEK-1143.KP.02.01 Tahun 2026 (KepmenPANRB No. 672/2026)",
        "rows_ingested": 16,
        "kuota_ingested": 1000,
        "catatan": "Data resmi SSCASN BKN Live lengkap 16 baris penempatan (8 jabatan; 895 Umum, 25 Disabilitas, 10 Lulusan Terbaik, 70 Putra/Putri Papua) beserta Gaji Resmi BKN Rp 5,3–9,4 jt (15/16 baris), uraian tugas, dan berkas unggah per formasi. Menggantikan Kemenham.pdf pra-rilis tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + POLRI CPNS.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kepolisian Negara Republik Indonesia",
        "referensi": "SSCASN BKN Live + Pengumuman Kapolri No. Peng/33/XI/KEP./2026 (KepmenPANRB No. 653/2026)",
        "rows_ingested": 633,
        "kuota_ingested": 750,
        "catatan": "Data resmi SSCASN BKN Live lengkap 633 baris penempatan satker Polda & Mabes Polri dengan total identik 750 kursi (722 Umum, 15 Disabilitas, 9 Lulusan Terbaik, 4 Putra/Putri Papua) beserta Gaji Resmi BKN Rp 5,5–7,5 jt (632/633 baris). Menggantikan POLRI CPNS.pdf pra-rilis tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + Kemenhut Pengumuman.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kementerian Kehutanan",
        "referensi": "SSCASN BKN Live + Pengumuman Sekjen Kemenhut No. PG.2/MENHUT-SETJEN/ROSDM/PEG.02/11/2026 (KepmenPANRB No. 639/2026)",
        "rows_ingested": 3782,
        "kuota_ingested": 70000,
        "catatan": "Data resmi SSCASN BKN Live lengkap 3.782 baris / 70.000 kursi identik dengan lampiran 630 halaman PG.2/MENHUT/2026 (69.274 Umum, 26 Penyandang Disabilitas, 700 Putra/Putri Papua; 32 jabatan termasuk 60.000 Polisi Kehutanan & 5.465 Manggala Agni) beserta Gaji Resmi BKN Rp 2,18–8,50 jt, uraian tugas, dan berkas unggah SSCASN per formasi. Menggantikan ekstraksi PDF pra-rilis tanpa duplikasi.",
    },
    {
        "file_name": "Mekanisme_CPNS_dan_Passing_Grade.pdf",
        "status": "reference_policy",
        "instansi": "Kementerian PANRB (Nasional)",
        "referensi": "KepmenPANRB No. 674 Tahun 2026 (20 Nov 2026)",
        "rows_ingested": 0,
        "kuota_ingested": 0,
        "catatan": "Regulasi mekanisme seleksi & Nilai Ambang Batas SKD CPNS 2026 (Umum: TWK >= 65, TIU >= 80, TKP >= 166; Cum Laude/Diaspora >= 311, TIU >= 85; Disabilitas/Papua >= 286, TIU >= 60; plus opsi pakai nilai SKD 2024). Ditampilkan sebagai acuan di Detail Formasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + CPNS_BSSN.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Badan Siber dan Sandi Negara",
        "referensi": "SSCASN BKN Live + PENG.102/BSSN/SU/KP.02.01/11/2026 (KepmenPANRB No. 676/2026)",
        "rows_ingested": 2,
        "kuota_ingested": 200,
        "catatan": "Data resmi SSCASN BKN Live (196 Umum + 4 Disabilitas, Gaji Resmi BKN Rp 5,1–5,8 jt; pelamar belum dirilis). Menggantikan catatan PDF CPNS_BSSN.pdf secara bersih tanpa duplikasi.",
    },
    {
        "file_name": "api-rekrutmen.bkn.go.id/portal/api/spf + CPNS_KEJAKSAAN_AGUNG.pdf",
        "status": "ingested_sscasn_live",
        "instansi": "Kejaksaan Agung",
        "referensi": "SSCASN BKN Live (Kejaksaan RI) + KepmenPANRB No. 638/2026",
        "rows_ingested": 30,
        "kuota_ingested": 1660,
        "catatan": "Data resmi SSCASN BKN Live lengkap nasional 1.660 kursi (1.510 Umum, 86 Lulusan Terbaik, 34 Disabilitas, 30 Putra/Putri Papua; Gaji Resmi BKN Rp 7,0–11,2 jt). Menggantikan sepenuhnya lampiran PDF parsial 6/69 halaman (94 baris / 175 kursi) tanpa duplikasi.",
    },
    {
        "file_name": "CPNS_Kemenkes_Info_STR_.pdf",
        "status": "ingested_no_quota",
        "instansi": "Kementerian Kesehatan",
        "referensi": "SE Dirjen SDMK No. HK.02.02/F/4023/2026 (22 Okt 2026)",
        "rows_ingested": 49,
        "kuota_ingested": 0,
        "catatan": "Persyaratan kualifikasi & STR bagi 30 Jabatan Fungsional Kesehatan (49 kelompok kategori/STR); kuota dibiarkan NULL/—. Berkas salinan identik SHA-256 dilewati.",
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
        "file_name": "KEMENKEU/Rincian Komposisi Penempatan Unit Eselon I.pdf & Format Surat 2024.docx",
        "status": "skipped_2024_archive",
        "instansi": "Kementerian Keuangan",
        "referensi": "Arsip Pengadaan CPNS Kemenkeu TA 2024 (1.230 kursi / jalur IKN)",
        "rows_ingested": 0,
        "kuota_ingested": 0,
        "catatan": "Berkas di subfolder KEMENKEU Drive terverifikasi merupakan arsip CPNS 2024 (1.230 kursi), bukan pengumuman CPNS 2026. Dilewati agar tidak mencemari data 2026.",
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


_UPPER_ACRONYMS = {
    "Ri": "RI",
    "Bpk": "BPK",
    "Bpkp": "BPKP",
    "Bssn": "BSSN",
    "Kkp": "KKP",
    "Bgn": "BGN",
    "Kppg": "KPPG",
    "Diy": "DIY",
    "Dki": "DKI",
    "Ntb": "NTB",
    "Ntt": "NTT",
    "Sdm": "SDM",
    "Sdmk": "SDMK",
    "Tik": "TIK",
    "Bpsdm": "BPSDM",
    "Bappenas": "Bappenas",
    "Ii": "II",
    "Iii": "III",
    "Iv": "IV",
    "Vi": "VI",
    "Vii": "VII",
    "Viii": "VIII",
}


def _format_unit_eselon1(raw_seg: str) -> str:
    s = re.sub(r"\s+", " ", (raw_seg or "").strip()).title()
    s = re.sub(r"\bDan\b", "dan", s)
    s = re.sub(r"\bDi\b", "di", s)
    for src, dst in _UPPER_ACRONYMS.items():
        s = re.sub(rf"\b{src}\b", dst, s)
    s = re.sub(
        r"Regional Sulawesi, Maluku, Papua, Bali,\s*Nusa Tenggara$",
        "Regional Sulawesi, Maluku, Papua, Bali, dan Nusa Tenggara",
        s,
    )
    return s


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
    "Badan Pemeriksa Keuangan Republik Indonesia": "BPK",
    "Kementerian Keuangan": "KEMENKEU",
    "Kementerian Keuangan Republik Indonesia": "KEMENKEU",
    "Badan Siber dan Sandi Negara": "BSSN",
    "Badan Siber dan Sandi Negara Republik Indonesia": "BSSN",
    "Kejaksaan Agung": "KEJAGUNG",
    "Kejaksaan Republik Indonesia": "KEJAGUNG",
    "Kementerian Kesehatan": "KEMENKES",
    "Kementerian Kesehatan Republik Indonesia": "KEMENKES",
    "Badan Pengawasan Keuangan dan Pembangunan": "BPKP",
    "Badan Pengawasan Keuangan dan Pembangunan Republik Indonesia": "BPKP",
    "Kementerian Hukum": "KEMENKUM",
    "Kementerian Hukum Republik Indonesia": "KEMENKUM",
    "Kementerian Koperasi": "KEMENKOP",
    "Kementerian Koperasi Republik Indonesia": "KEMENKOP",
    "Mahkamah Agung": "MA",
    "Mahkamah Agung RI": "MA",
    "Mahkamah Agung Republik Indonesia": "MA",
    "Sekretariat Mahkamah Agung": "MA",
    "Kementerian Hak Asasi Manusia": "KEMENHAM",
    "Kementerian Hak Asasi Manusia Republik Indonesia": "KEMENHAM",
    "Kepolisian Negara": "POLRI",
    "Kepolisian Negara Republik Indonesia": "POLRI",
    "Polri": "POLRI",
    "Kementerian Kehutanan": "KEMENHUT",
    "Kementerian Kehutanan Republik Indonesia": "KEMENHUT",
    "Kementerian Kelautan dan Perikanan": "KKP",
    "Kementerian Kelautan dan Perikanan Republik Indonesia": "KKP",
    "Badan Gizi Nasional": "BGN",
    "Badan Gizi Nasional Republik Indonesia": "BGN",
}

_CANONICAL_INSTANSI_NM = {
    "Badan Pemeriksa Keuangan Republik Indonesia": "Badan Pemeriksa Keuangan",
    "Kementerian Keuangan Republik Indonesia": "Kementerian Keuangan",
    "Badan Siber dan Sandi Negara Republik Indonesia": "Badan Siber dan Sandi Negara",
    "Kejaksaan Republik Indonesia": "Kejaksaan Agung",
    "Kementerian Kesehatan Republik Indonesia": "Kementerian Kesehatan",
    "Badan Pengawasan Keuangan dan Pembangunan Republik Indonesia": "Badan Pengawasan Keuangan dan Pembangunan",
    "Kementerian Hukum Republik Indonesia": "Kementerian Hukum",
    "Kementerian Koperasi Republik Indonesia": "Kementerian Koperasi",
    "Mahkamah Agung": "Mahkamah Agung RI",
    "Mahkamah Agung Republik Indonesia": "Mahkamah Agung RI",
    "Sekretariat Mahkamah Agung": "Mahkamah Agung RI",
    "Kementerian Hak Asasi Manusia Republik Indonesia": "Kementerian Hak Asasi Manusia",
    "Kepolisian Negara": "Kepolisian Negara Republik Indonesia",
    "Kementerian Kehutanan Republik Indonesia": "Kementerian Kehutanan",
    "Kementerian Kelautan dan Perikanan Republik Indonesia": "Kementerian Kelautan dan Perikanan",
    "Badan Gizi Nasional": "Badan Gizi Nasional",
    "Badan Gizi Nasional Republik Indonesia": "Badan Gizi Nasional",
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


def _clean_html_text(val: str) -> str:
    txt = re.sub(r"<[^>]+>", "", str(val or ""))
    return re.sub(r"\s+", " ", txt).strip()


def _parse_sscasn_persyaratan(raw_json: str) -> str | None:
    """Sanitize SSCASN persyaratan_json into a compact, plain-text JSON list."""
    import json

    raw = (raw_json or "").strip()
    if not raw or raw == "[]":
        return None
    try:
        items = json.loads(raw)
    except Exception:
        return None
    if not isinstance(items, list) or not items:
        return None
    cleaned = []
    seen: set[tuple[str, bool]] = set()
    for it in items:
        if not isinstance(it, dict):
            continue
        nama = _clean_html_text(it.get("nama") or "")
        if not nama:
            continue
        wajib = bool(it.get("mandatory", 1))
        jf = _clean_html_text(it.get("jenis_formasi_nama") or "") or None
        key = (nama.lower(), wajib)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append({"nama": nama, "wajib": wajib, "jenis_formasi": jf})
    cleaned.sort(key=lambda x: (not x["wajib"], (x["jenis_formasi"] or "").lower(), x["nama"].lower()))
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


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

            raw_instansi_nm = (r.get("instansi") or "").strip()
            instansi_id = _sscasn_instansi_id(raw_instansi_nm)
            instansi_nm = _CANONICAL_INSTANSI_NM.get(raw_instansi_nm, raw_instansi_nm)
            per_agency_counter[instansi_id] = per_agency_counter.get(instansi_id, 0) + 1
            no = per_agency_counter[instansi_id]

            lokasi_nm = re.sub(r"\s+", " ", (r.get("lokasi_formasi") or "").strip())
            segs = [s.strip() for s in lokasi_nm.split("|") if s.strip()]
            if len(segs) >= 2:
                eselon1 = _format_unit_eselon1(segs[1])
            else:
                raw_es1 = lokasi_nm or instansi_nm
                eselon1 = _format_unit_eselon1(raw_es1) if raw_es1.isupper() else raw_es1

            raw_pend = (r.get("nama_pendidikan") or r.get("group_pendidikan") or "").strip()
            pend_nm = re.sub(r"\s+/\s+", " | ", raw_pend)
            pend_parts: list[str] = []
            seen_pend: set[str] = set()
            for p in pend_nm.split("|"):
                clean_p = re.sub(r"\s+", " ", p).strip()
                if clean_p and clean_p.upper() not in seen_pend:
                    seen_pend.add(clean_p.upper())
                    pend_parts.append(clean_p)
            pend_nm = " | ".join(pend_parts)

            jabatan_nm = re.sub(r"\s+", " ", (r.get("nama_jabatan") or "").strip()).upper()
            jenis_formasi = (r.get("jenis_formasi") or "").strip() or None
            kuota = int(float(r.get("jumlah") or 0))
            gmin_raw = int(float(r.get("penghasilan_min") or 0))
            gmax_raw = int(float(r.get("penghasilan_max") or 0))
            gaji_min = gmin_raw if gmin_raw > 0 else None
            gaji_max = gmax_raw if gmax_raw > 0 else None
            umin_raw = int(float(r.get("usia_min") or 0))
            umax_raw = int(float(r.get("usia_max") or 0))
            usia_min = umin_raw if umin_raw > 0 else None
            usia_max = umax_raw if umax_raw > 0 else None
            jobdesc = _clean_html_text(r.get("jobdesc") or "") or None
            persyaratan_json = _parse_sscasn_persyaratan(r.get("persyaratan_json") or "")

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
                    "usia_min": usia_min,
                    "usia_max": usia_max,
                    "jobdesc": jobdesc,
                    "persyaratan_json": persyaratan_json,
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
    s = re.sub(r"^\d+\.\s*", "", s)
    parts = re.split(r"\s+\d+\.\s+", s)
    cleaned: list[str] = []
    seen_p: set[str] = set()
    for p in parts:
        tok = re.sub(r"^\d+\.\s*", "", p).strip(" ;,")
        tok = re.sub(r"\bImu\b", "Ilmu", tok)
        tok = re.sub(r"\s+", " ", tok).strip()
        if tok and tok.upper() not in seen_p:
            seen_p.add(tok.upper())
            cleaned.append(tok)
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
        jab_clean = re.sub(r"\s*(?:\(\*\)|\*)+$", "", re.sub(r"\s+", " ", g["jab"]).strip()).upper()
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


SUMBER_BPKP = (
    "Pengumuman BPKP No. KP.00.01/PENG-2/SU/02/2026 — Pengadaan PNS BPKP TA 2026 "
    "(KepmenPANRB No. 640 Tahun 2026, 27 November 2026)"
)


def _bpkp_unit_eselon1(unit: str) -> str:
    u = re.sub(r"\s+", " ", unit).strip()
    if u.startswith("Perwakilan BPKP"):
        return "Perwakilan BPKP Daerah (34 Provinsi)"
    if u.startswith("Deputi Bidang"):
        return u
    if u == "Inspektorat":
        return "Inspektorat"
    return "Sekretariat Utama / Biro / Pusat"


def get_bpkp_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 554 verified BPKP CPNS 2026 placement rows (2,007 seats) from Lampiran I & II."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for r in payload.get("rows", []):
        no = int(r["no_lampiran2"])
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        unit = re.sub(r"\s+", " ", str(r["unit_penempatan"])).strip()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_parts = [re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_raw"]).split(";") if p.strip()]
        pend_nm = " | ".join(pend_parts)
        rows.append(
            {
                "no_urut": no,
                "formasi_id": f"2026-BPKP-{no:03d}",
                "instansi_id": "BPKP",
                "instansi_nm": "Badan Pengawasan Keuangan dan Pembangunan",
                "kategori_instansi": "Pusat",
                "unit_eselon1": _bpkp_unit_eselon1(unit),
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": f"BPKP | {unit.upper()}",
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": int(r["gaji_min"]),
                "gaji_max": int(r["gaji_max"]),
                "sumber_dokumen": SUMBER_BPKP,
            }
        )
    return rows


SUMBER_KEMENKUM = (
    "Pengumuman Kemenkum No. SEK.2-KP.02.01-326 — Seleksi Pengadaan CPNS Kementerian Hukum RI TA 2026 "
    "(KepmenPANRB No. 647 Tahun 2026, 27 November 2026)"
)


def _kemenkum_unit_eselon1(unit: str) -> str:
    u = re.sub(r"\s+", " ", unit).strip()
    if u.lower() == "unit pusat":
        return "Unit Pusat Kementerian Hukum"
    return u


def get_kemenkum_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 45 verified Kementerian Hukum CPNS 2026 rows (15 jabatan / 1,297 seats) from SEK.2-KP.02.01-326."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for r in payload.get("rows", []):
        no = int(r["no_urut"])
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        unit = re.sub(r"\s+", " ", str(r["unit_penempatan"])).strip()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_parts = [re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_raw"]).split(";") if p.strip()]
        pend_nm = " | ".join(pend_parts)
        rows.append(
            {
                "no_urut": no,
                "formasi_id": str(r["formasi_id"]).strip(),
                "instansi_id": "KEMENKUM",
                "instansi_nm": "Kementerian Hukum",
                "kategori_instansi": "Pusat",
                "unit_eselon1": _kemenkum_unit_eselon1(unit),
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": f"KEMENTERIAN HUKUM | {unit.upper()}",
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_KEMENKUM,
            }
        )
    return rows


SUMBER_MA = (
    "Pengumuman Sekretaris Mahkamah Agung RI No. 34/SEK/PENG.KP1.1.2/XI/2026 — Seleksi Pengadaan PNS MA RI TA 2026 "
    "(KepmenPANRB No. 643 Tahun 2026, 27 November 2026)"
)

SUMBER_KEMENHAM = (
    "Pengumuman Kemenham No. SEK-1143.KP.02.01 Tahun 2026 — Pengadaan CPNS Kementerian Hak Asasi Manusia RI TA 2026 "
    "(KepmenPANRB No. 672 Tahun 2026, 27 November 2026)"
)

SUMBER_POLRI = (
    "Pengumuman Kapolri No. Peng/33/XI/KEP./2026 — Pengadaan CPNS di Lingkungan Polri TA 2026 "
    "(KepmenPANRB No. 653 Tahun 2026, 27 November 2026)"
)

SUMBER_KEMENHUT = (
    "Pengumuman Sekjen Kemenhut No. PG.2/MENHUT-SETJEN/ROSDM/PEG.02/11/2026 — Pengadaan CPNS Kementerian Kehutanan TA 2026 "
    "(KepmenPANRB No. 639 Tahun 2026, 27 November 2026)"
)


def get_ma_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 22 verified Mahkamah Agung RI CPNS 2026 rows (18 formasi codes / 4,430 seats)."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for r in payload.get("rows", []):
        no = int(r["no_urut"])
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        unit = re.sub(r"\s+", " ", str(r["unit_penempatan"])).strip()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_nm = " | ".join(re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_nm"]).split("|") if p.strip())
        if unit.startswith("Peradilan "):
            eselon1 = unit.split("(")[0].strip()
        else:
            eselon1 = "Mahkamah Agung dan Badan Peradilan di Bawahnya"
        rows.append(
            {
                "no_urut": no,
                "formasi_id": str(r["formasi_id"]).strip(),
                "instansi_id": "MA",
                "instansi_nm": "Mahkamah Agung RI",
                "kategori_instansi": "Pusat",
                "unit_eselon1": eselon1,
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": f"MAHKAMAH AGUNG RI | {unit.upper()}",
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_MA,
            }
        )
    return rows


def get_kemenham_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 15 verified Kementerian Hak Asasi Manusia CPNS 2026 rows (8 jabatan / 1,000 seats) with official salaries."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for r in payload.get("rows", []):
        no = int(r["no_urut"])
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        unit = re.sub(r"\s+", " ", str(r["unit_penempatan"])).strip()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_nm = " | ".join(re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_nm"]).split("|") if p.strip())
        eselon1 = "Unit Pusat Kementerian HAM" if unit.lower() == "unit pusat" else "Unit Pusat dan Kantor Wilayah (20 Kanwil)"
        rows.append(
            {
                "no_urut": no,
                "formasi_id": str(r["formasi_id"]).strip(),
                "instansi_id": "KEMENHAM",
                "instansi_nm": "Kementerian Hak Asasi Manusia",
                "kategori_instansi": "Pusat",
                "unit_eselon1": eselon1,
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": f"KEMENTERIAN HAM | {unit.upper()}",
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": int(r["gaji_min"]),
                "gaji_max": int(r["gaji_max"]),
                "usia_min": 18,
                "usia_max": 35,
                "sumber_dokumen": SUMBER_KEMENHAM,
            }
        )
    return rows


def _polri_unit_eselon1(unit: str) -> str:
    u = re.sub(r"\s+", " ", unit).strip().upper()
    m = re.search(r"\b(POLDA\s+[A-Z.\s]+)$", u)
    if m:
        polda = re.sub(r"\s+", " ", m.group(1)).strip()
        polda_tc = polda.title().replace("Diy", "DIY").replace("Ntb", "NTB").replace("Ntt", "NTT").replace("Dki", "DKI")
        return polda_tc
    return "Mabes Polri (Satker Pusat)"


def get_polri_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 633 verified Polri CPNS 2026 rows (605 placement items / 750 seats) from Peng/33/XI/KEP./2026."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for r in payload.get("rows", []):
        no = int(r["no_urut"])
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        unit = re.sub(r"\s+", " ", str(r["unit_penempatan"])).strip().upper()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_nm = " | ".join(re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_nm"]).split("|") if p.strip())
        rows.append(
            {
                "no_urut": no,
                "formasi_id": str(r["formasi_id"]).strip(),
                "instansi_id": "POLRI",
                "instansi_nm": "Kepolisian Negara Republik Indonesia",
                "kategori_instansi": "Pusat",
                "unit_eselon1": _polri_unit_eselon1(unit),
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": f"POLRI | {unit}",
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_POLRI,
            }
        )
    return rows


def get_kemenhut_rows(extract_jenjang_fn, json_path) -> list[dict]:
    """Load 3,782 verified Kemenhut CPNS 2026 rows (3,281 lampiran items / 70,000 seats) from PG.2/2026."""
    import json

    if not json_path.exists():
        return []
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    rows = []
    for idx, r in enumerate(payload, 1):
        jab = re.sub(r"\s+", " ", str(r["jabatan_nm"])).strip().upper()
        lokasi = re.sub(r"\s+", " ", str(r["lokasi_nm"])).strip().upper()
        eselon1 = re.sub(r"\s+", " ", str(r["unit_eselon1"])).strip()
        jf = re.sub(r"\s+", " ", str(r["jenis_formasi"])).strip().upper()
        pend_nm = " | ".join(re.sub(r"\s+", " ", p).strip() for p in str(r["pendidikan_nm"]).split("|") if p.strip())
        jf_code = "UMM" if jf == "UMUM" else ("DIS" if "DISABILITAS" in jf else "PAP")
        rows.append(
            {
                "no_urut": idx,
                "formasi_id": f"2026-KEMENHUT-{int(r['no_lampiran']):04d}-{jf_code}",
                "instansi_id": "KEMENHUT",
                "instansi_nm": "Kementerian Kehutanan",
                "kategori_instansi": "Pusat",
                "unit_eselon1": eselon1,
                "jabatan_nm": jab,
                "pendidikan_nm": pend_nm,
                "jenjang": extract_jenjang_fn(pend_nm),
                "jumlah_formasi": int(r["jumlah_formasi"]),
                "lokasi_nm": lokasi,
                "jenis_formasi": jf,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": int(r["gaji_min"]),
                "gaji_max": int(r["gaji_max"]),
                "usia_min": 18,
                "usia_max": 35,
                "sumber_dokumen": SUMBER_KEMENHUT,
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


def _load_scores_2024_raw_map() -> dict[str, dict]:
    """Load parsed CPNS 2024 per-formation score distributions keyed by cpns2024.db formasi_id."""
    import json
    from pathlib import Path

    all_raw_path = Path(r"D:\AG Files\cpns2026-scraper\data\parsed\scores_2024_all_raw.json")
    raw_path = Path(r"D:\AG Files\cpns2026-scraper\data\parsed\scores_2024_6instansi_raw.json")
    summary_path = Path(__file__).resolve().parents[1] / "data" / "scores_2024_6instansi.json"
    src = all_raw_path if all_raw_path.exists() else (raw_path if raw_path.exists() else summary_path)
    if not src.exists():
        return {}
    payload = json.loads(src.read_text(encoding="utf-8"))
    by_fid: dict[str, dict] = {}
    for sec in payload.get("sections", []):
        fid24 = sec.get("formasi_id_2024")
        if fid24:
            by_fid[fid24] = sec
    return by_fid


def _aggregate_2024_scores(fids: list[str], scores_by_fid: dict[str, dict]) -> dict:
    """Aggregate exact sample score stats across one or more matched 2024 formations."""
    import statistics

    empty = {
        "n_peserta_skb_2024": None,
        "n_lulus_2024": None,
        "nilai_akhir_2024_min": None,
        "nilai_akhir_2024_median": None,
        "nilai_akhir_2024_max": None,
        "skd_2024_lulus_min": None,
        "skd_2024_lulus_median": None,
        "skd_2024_lulus_max": None,
        "skd_2024_skb_min": None,
        "skb_2024_lulus_min": None,
        "skb_2024_lulus_median": None,
        "skb_2024_lulus_max": None,
        "sumber_nilai_2024": None,
    }
    secs = [scores_by_fid[f] for f in fids if f in scores_by_fid]
    if not secs:
        return empty

    n_skb = sum(int(s.get("peserta_skb") or 0) for s in secs)
    n_lulus = sum(int(s.get("n_lulus") or 0) for s in secs)
    sumber = next((s.get("sumber") for s in secs if s.get("sumber")), None)

    # Prefer pooling raw candidate lists (never median-of-medians). If single section summary only, use summary directly.
    has_raw = all("pl_na" in s for s in secs)
    if has_raw:
        pl_na = [float(x) for s in secs for x in (s.get("pl_na") or [])]
        pl_skd = [int(x) for s in secs for x in (s.get("pl_skd") or [])]
        pl_skb = [float(x) for s in secs for x in (s.get("pl_skb") or [])]
        skb_skd = [int(x) for s in secs for x in (s.get("skb_skd") or [])]
        out = {
            "n_peserta_skb_2024": n_skb,
            "n_lulus_2024": len(pl_na),
            "nilai_akhir_2024_min": round(min(pl_na), 3) if pl_na else None,
            "nilai_akhir_2024_median": round(statistics.median(pl_na), 3) if pl_na else None,
            "nilai_akhir_2024_max": round(max(pl_na), 3) if pl_na else None,
            "skd_2024_lulus_min": min(pl_skd) if pl_skd else None,
            "skd_2024_lulus_median": round(statistics.median(pl_skd), 1) if pl_skd else None,
            "skd_2024_lulus_max": max(pl_skd) if pl_skd else None,
            "skd_2024_skb_min": min(skb_skd) if skb_skd else None,
            "skb_2024_lulus_min": round(min(pl_skb), 3) if pl_skb else None,
            "skb_2024_lulus_median": round(statistics.median(pl_skb), 3) if pl_skb else None,
            "skb_2024_lulus_max": round(max(pl_skb), 3) if pl_skb else None,
            "sumber_nilai_2024": sumber,
        }
        return out

    if len(secs) == 1:
        s = secs[0]
        na = s.get("nilai_akhir_lulus") or {}
        skd_l = s.get("skd_lulus") or {}
        skb_l = s.get("skb_lulus") or {}
        skd_all = s.get("skd_peserta_skb") or {}
        return {
            "n_peserta_skb_2024": n_skb,
            "n_lulus_2024": n_lulus,
            "nilai_akhir_2024_min": na.get("min"),
            "nilai_akhir_2024_median": na.get("median"),
            "nilai_akhir_2024_max": na.get("max"),
            "skd_2024_lulus_min": int(skd_l["min"]) if skd_l.get("min") is not None else None,
            "skd_2024_lulus_median": skd_l.get("median"),
            "skd_2024_lulus_max": int(skd_l["max"]) if skd_l.get("max") is not None else None,
            "skd_2024_skb_min": int(skd_all["min"]) if skd_all.get("min") is not None else None,
            "skb_2024_lulus_min": skb_l.get("min"),
            "skb_2024_lulus_median": skb_l.get("median"),
            "skb_2024_lulus_max": skb_l.get("max"),
            "sumber_nilai_2024": sumber,
        }

    return {**empty, "n_peserta_skb_2024": n_skb, "n_lulus_2024": n_lulus, "sumber_nilai_2024": sumber}


def compute_2024_comparison_map(rows_2026: list[dict], cpns2024_db_path) -> dict[str, dict]:
    """Compute historical CPNS 2024 comparison records per 2026 formasi_id from cpns2024.db."""
    import sqlite3

    empty_scores = _aggregate_2024_scores([], {})
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
                **empty_scores,
            }
        return result

    scores_by_fid = _load_scores_2024_raw_map()
    c24 = sqlite3.connect(f"file:{cpns2024_db_path}?mode=ro", uri=True)
    try:
        inst_map = {
            r[1].strip().lower(): r[0]
            for r in c24.execute("SELECT instansi_id, nama_instansi FROM instansi").fetchall()
        }
        # Preload 2024 formasi rows only for agencies present in 2026
        needed_iids = {inst_map.get(r["instansi_nm"].strip().lower()) for r in rows_2026}
        needed_iids.discard(None)

        by_inst_jab: dict[tuple[int, str], list[tuple[str, str, str, int, int]]] = {}
        by_inst_all: dict[int, list[tuple[str, str, int, int]]] = {}
        if needed_iids:
            placeholders = ",".join("?" for _ in needed_iids)
            q_rows = c24.execute(
                f"""
                SELECT formasi_id, instansi_id, UPPER(jabatan_nm), lokasi_nm, jenis_formasi,
                       COALESCE(jumlah_formasi, 0), COALESCE(jumlah_pelamar, 0)
                FROM formasi
                WHERE instansi_id IN ({placeholders})
                """,
                list(needed_iids),
            ).fetchall()
            for fid24, iid, jab, lok, jf, k, p in q_rows:
                by_inst_jab.setdefault((iid, jab), []).append((fid24, lok or "", jf or "", int(k), int(p)))
                by_inst_all.setdefault(iid, []).append((fid24, jab, int(k), int(p)))

        for r in rows_2026:
            fid = r["formasi_id"]
            iid = inst_map.get(r["instansi_nm"].strip().lower())
            jab26 = (r.get("jabatan_nm") or "").strip().upper()
            matched_rows: list[tuple[str, int, int]] = []
            match_level = None
            match_label = "Tidak ada pembanding di 2024"

            if iid is not None:
                reg26 = _norm_bpk_region(r.get("lokasi_nm") or "")
                exact_list = by_inst_jab.get((iid, jab26), [])

                # Tier 1: Same Instansi + Exact Jabatan + Same Regional (e.g., BPK Regional)
                if exact_list and reg26:
                    reg_matches = [
                        (fid24, k, p, jf)
                        for fid24, lok, jf, k, p in exact_list
                        if _norm_bpk_region(lok) == reg26
                    ]
                    if reg_matches:
                        jf26 = (r.get("jenis_formasi") or "").upper()
                        same_jf = [(fid24, k, p) for fid24, k, p, jf in reg_matches if jf26 and jf.upper() == jf26]
                        if same_jf:
                            matched_rows = same_jf
                            match_level = "regional_exact"
                            match_label = f"Regional & jalur sama di 2024 ({jf26})"
                        else:
                            matched_rows = [(fid24, k, p) for fid24, k, p, _ in reg_matches]
                            match_level = "regional_exact"
                            match_label = "Regional sama di 2024 (jalur Umum)" if jf26 else "Regional sama di 2024"

                # Tier 2: Same Instansi + Exact Jabatan (Kemenkeu Kapal, Kejagung, BPK Analis Kerja Sama, BPKP)
                if not matched_rows and exact_list:
                    matched_rows = [(fid24, k, p) for fid24, _, _, k, p in exact_list]
                    match_level = "instansi_jabatan"
                    match_label = "Jabatan sama di instansi yang sama (2024)"

                # Tier 2b: BPKP verified equivalents (KONSELOR SDM & Auditor Ahli Pertama parent rumpun)
                if not matched_rows and r["instansi_id"] == "BPKP":
                    if jab26 == "KONSELOR SUMBER DAYA MANUSIA":
                        alt = by_inst_jab.get((iid, "KONSELOR SDM"), [])
                        if alt:
                            matched_rows = [(fid24, k, p) for fid24, _, _, k, p in alt]
                            match_level = "instansi_jabatan"
                            match_label = "Jabatan sama (KONSELOR SDM) di BPKP 2024"
                    elif jab26.startswith("AUDITOR AHLI PERTAMA - RUMPUN"):
                        alt = by_inst_jab.get((iid, "AUDITOR AHLI PERTAMA"), [])
                        if alt:
                            matched_rows = [(fid24, k, p) for fid24, _, _, k, p in alt]
                            match_level = "instansi_jabatan"
                            match_label = "Jabatan induk AUDITOR AHLI PERTAMA di BPKP 2024 (semua rumpun)"

                # Tier 3: Kemenkes SE STR JF Rumpun + Kategori (Keahlian vs Keterampilan)
                if not matched_rows and r["instansi_id"] == "KEMENKES":
                    ue1 = r.get("unit_eselon1") or ""
                    kat = "Keahlian" if "Keahlian" in ue1 else "Keterampilan"
                    clean = re.sub(r"\(\*\)", "", jab26).replace("*", "").strip()
                    aliases = [a.strip() for a in clean.split("/") if a.strip()]
                    kat_rows: list[tuple[str, int, int]] = []
                    for fid24, jab24, k24, p24 in by_inst_all.get(iid, []):
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
                                kat_rows.append((fid24, k24, p24))
                                break
                    if kat_rows:
                        matched_rows = kat_rows
                        match_level = "instansi_jf_kategori"
                        match_label = f"Rumpun JF {kat} Kemenkes di 2024 (rekap unit)"

            if matched_rows:
                kursi24 = sum(k for _, k, _ in matched_rows)
                pelamar24 = sum(p for _, _, p in matched_rows)
                if kursi24 > 0:
                    rasio24, peluang24, status24 = _classify_keketatan_2024(kursi24, pelamar24)
                    score_stats = _aggregate_2024_scores([fid24 for fid24, _, _ in matched_rows], scores_by_fid)
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
                        **score_stats,
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
                **empty_scores,
            }
    finally:
        c24.close()

    return result



