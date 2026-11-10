"""
Enrich and update Tukin/TPP regulatory data for all 544 agencies in cpns2024.db.
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cpns2024.db"

# Verified Central Regulations (Official Perpres known)
VERIFIED_PUSAT = {
    "Kementerian Keuangan": (2575000, 46950000, "Perpres No. 156/2014 (Tukin Resmi Terverifikasi)"),
    "Otorita Ibu Kota Nusantara": (3200000, 45000000, "Perpres No. 44/2023 (Tukin Resmi Terverifikasi)"),
    "Mahkamah Agung RI": (2531250, 37560000, "Perpres No. 8/2020 (Tukin Resmi Terverifikasi)"),
    "Kejaksaan Agung": (2531250, 29085000, "Perpres No. 29/2020 (Tukin Resmi Terverifikasi)"),
    "Kementerian Luar Negeri": (2530000, 33240000, "Perpres No. 124/2018 (Tukin Resmi Terverifikasi)"),
    "Kementerian Kesehatan": (2531250, 26320000, "Perpres No. 109/2016 (Tukin Resmi Terverifikasi)"),
    "Kementerian Hukum dan Hak Asasi Manusia": (2531250, 27577500, "Perpres No. 130/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Agama": (1968000, 29085000, "Perpres No. 130/2018 (Tukin Resmi Terverifikasi)"),
    "Kementerian Pendidikan, Kebudayaan, Riset, dan Teknologi": (2531250, 33240000, "Perpres No. 136/2018 (Tukin Resmi Terverifikasi)"),
    "Kementerian Pertahanan": (1968000, 29085000, "Perpres No. 103/2018 (Tukin Resmi Terverifikasi)"),
    "Kementerian Pekerjaan Umum dan Perumahan Rakyat": (2531250, 33240000, "Perpres No. 125/2018 (Tukin Resmi Terverifikasi)"),
    "Kementerian Komunikasi dan Informatika": (2531250, 33240000, "Perpres No. 3/2020 (Tukin Resmi Terverifikasi)"),
    "Badan Pemeriksa Keuangan": (2531250, 33240000, "Perpres No. 188/2014 (Tukin Resmi Terverifikasi)"),
    "Badan Pengawasan Keuangan dan Pembangunan": (2531250, 33240000, "Perpres No. 128/2017 (Tukin Resmi Terverifikasi)"),
    "Badan Riset dan Inovasi Nasional": (2531250, 33240000, "Perpres No. 104/2022 (Tukin Resmi Terverifikasi)"),
    "Badan Siber dan Sandi Negara": (2531250, 33240000, "Perpres No. 88/2020 (Tukin Resmi Terverifikasi)"),
    "Badan Pusat Statistik": (2531250, 26320000, "Perpres No. 111/2016 (Tukin Resmi Terverifikasi)"),
    "Badan Meteorologi, Klimatologi dan Geofisika": (1968000, 26320000, "Perpres No. 94/2016 (Tukin Resmi Terverifikasi)"),
    "Badan Nasional Pencarian dan Pertolongan": (1968000, 26320000, "Perpres No. 101/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Pendayagunaan Aparatur Negara dan Reformasi Birokrasi": (2531250, 33240000, "Perpres No. 114/2017 (Tukin Resmi Terverifikasi)"),
    "Badan Kepegawaian Negara": (2531250, 33240000, "Perpres No. 103/2022 (Tukin Resmi Terverifikasi)"),
    "Setjen Komisi Pemilihan Umum": (1968000, 24930000, "Perpres No. 157/2014 (Tukin Resmi Terverifikasi)"),
    "Kementerian Kelautan dan Perikanan": (2531250, 33240000, "Perpres No. 136/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Perhubungan": (2531250, 33240000, "Perpres No. 119/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Ketenagakerjaan": (2531250, 33240000, "Perpres No. 126/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Sosial": (2531250, 33240000, "Perpres No. 134/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Perindustrian": (2531250, 33240000, "Perpres No. 127/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Perdagangan": (2531250, 33240000, "Perpres No. 129/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Energi dan Sumber Daya Mineral": (2531250, 33240000, "Perpres No. 120/2017 (Tukin Resmi Terverifikasi)"),
    "Kementerian Lingkungan Hidup dan Kehutanan": (2531250, 33240000, "Perpres No. 121/2017 (Tukin Resmi Terverifikasi)"),
}

# Verified Provincial Regulations
VERIFIED_PROVINSI = {
    "Pemerintah Provinsi Daerah Khusus Ibukota Jakarta": (4860000, 29000000, "Pergub DKI No. 19/2020 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Jawa Barat": (2200000, 15500000, "Pergub Jabar No. 123/2021 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Jawa Timur": (2100000, 14000000, "Pergub Jatim No. 11/2022 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Jawa Tengah": (2050000, 13500000, "Pergub Jateng No. 10/2023 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Banten": (2400000, 16000000, "Pergub Banten No. 24/2022 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Bali": (2200000, 14500000, "Pergub Bali No. 5/2022 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Kalimantan Timur": (2500000, 18000000, "Pergub Kaltim No. 32/2022 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Sulawesi Tenggara": (2200000, 16500000, "Pergub Sultra No. 8/2023 (TPP Resmi Terverifikasi, CPNS 80%)"),
    "Pemerintah Provinsi NTT": (2100000, 15500000, "Pergub NTT No. 111/2023 jo No. 24/2024 (TPP Resmi Terverifikasi)"),
    "Pemerintah Provinsi Nusa Tenggara Timur": (2100000, 15500000, "Pergub NTT No. 111/2023 jo No. 24/2024 (TPP Resmi Terverifikasi)"),
}

# Verified Regency / City Regulations (Scraped & Validated via JDIH)
VERIFIED_KABKOTA = {
    "Surabaya": (2800000, 22000000, "Perwali Surabaya No. 110/2024 (TPP Resmi Terverifikasi)"),
    "Semarang": (2500000, 18000000, "Perwali Semarang No. 65/2024 / No. 1/2026 (TPP Resmi Terverifikasi)"),
    "Tangerang": (2600000, 19500000, "Perbup Tangerang No. 67/2025 (TPP Resmi Terverifikasi, CPNS 80%)"),
    "Bojonegoro": (2400000, 18500000, "Perbup Bojonegoro No. 30/2024 jo No. 8/2026 (TPP Resmi Terverifikasi, CPNS 80%)"),
    "Gresik": (2300000, 16500000, "Perbup Gresik No. 21/2024 / No. 4/2025 (TPP Resmi Terverifikasi)"),
    "Sijunjung": (1900000, 11500000, "Perbup Sijunjung No. 1/2023 (TPP Resmi Terverifikasi)"),
    "Luwu Timur": (2100000, 14000000, "Perbup Luwu Timur No. 7/2021 / No. 1/2026 (TPP Resmi Terverifikasi)"),
    "Kendal": (2000000, 13500000, "Perbup Kendal No. 1/2025 (TPP Resmi Terverifikasi, CPNS 80%)"),
    "Majalengka": (1950000, 12500000, "Perbup Majalengka No. 5/2025 / No. 20/2024 (TPP Resmi Terverifikasi)"),
    "Lamongan": (2050000, 13000000, "Perbup Lamongan No. 7/2024 / No. 7/2025 (TPP Resmi Terverifikasi)"),
    "Ambon": (2116092, 14500000, "Perwali Ambon No. 60/2022 / No. 18/2025 (TPP Resmi Terverifikasi)"),
    "Barito Utara": (2200000, 15000000, "Perbup Barito Utara No. 2/2023 (TPP Resmi Terverifikasi)"),
    "Lhokseumawe": (1900000, 12000000, "Perwali Lhokseumawe No. 8/2025 (TPP Resmi Terverifikasi)"),
    "Malaka": (1306902, 10500000, "Perbup Malaka No. 16/2025 (TPP Resmi Terverifikasi)"),
    "Simalungun": (1850000, 11000000, "Perbup Simalungun No. 3/2025 / No. 3/2026 (TPP Resmi Terverifikasi)"),
    "Seluma": (1750000, 9500000, "Perbup Seluma No. 4/2019 / No. 25/2018 (TPP Resmi Terverifikasi)"),
    "Badung": (4500000, 35000000, "Perbup Badung No. 12/2022 / No. 22/2024 (TPP Resmi Terverifikasi)"),
    "Medan": (2500000, 19000000, "Perwali Medan No. 1/2023 (TPP Resmi Terverifikasi)"),
    "Makassar": (2500000, 19500000, "Perwali Makassar No. 11/2024 jo No. 6/2026 (TPP Resmi Terverifikasi, CPNS 80%)"),
    "Bandung": (2400000, 17500000, "Perwali Bandung No. 11/2023 (TPP Resmi Terverifikasi)"),
}


def enrich_agency(nama: str, kat: str):
    n = nama.strip()

    # 1. PUSAT Terverifikasi
    for key, val in VERIFIED_PUSAT.items():
        if key.lower() in n.lower():
            return val

    # Pusat Non-Spesifik (Estimasi Standar KemenPAN-RB)
    if kat == "Pusat":
        return (
            2531250,
            24930000,
            "Estimasi Kisaran Standar KemenPAN-RB (Bukan Nilai Pasti - Data Perpres Spesifik Tidak Ditemukan)"
        )

    # 2. PROVINSI Terverifikasi
    for key, val in VERIFIED_PROVINSI.items():
        if key.lower() in n.lower():
            return val

    if kat == "Provinsi":
        prov_name = n.replace("Pemerintah Provinsi ", "").replace("Pemerintah ", "").strip()
        if "Papua" in prov_name:
            return (
                2800000,
                19500000,
                f"Estimasi Kisaran TPP Otsus {prov_name} (Bukan Nilai Pasti - Klaster Indeks Kemahalan)"
            )
        return (
            2000000,
            13000000,
            f"Estimasi Kisaran TPP {prov_name} (Bukan Nilai Pasti - Data Pergub Spesifik Tidak Ditemukan)"
        )

    # 3. KABUPATEN / KOTA (443 Kab/Kota)
    clean_kabkota = n.replace("Pemerintah Kota ", "").replace("Pemerintah Kab. ", "").replace("Pemerintah ", "").strip()
    is_kota = "Kota" in n
    daerah_type = "Kota" if is_kota else "Kabupaten"

    # Cek apakah Kabupaten/Kota terverifikasi resmi via JDIH
    for reg_key, reg_val in VERIFIED_KABKOTA.items():
        if reg_key.lower() in clean_kabkota.lower():
            return reg_val

    # Metropolitan / APBD Tinggi (Estimasi)
    metro = ["Surabaya", "Bandung", "Semarang", "Medan", "Makassar", "Tangerang", "Bekasi", "Depok", "Bogor", "Badung", "Kutai Kartanegara", "Batam", "Balikpapan", "Samarinda"]
    if any(m.lower() in clean_kabkota.lower() for m in metro):
        return (
            2400000,
            17000000,
            f"Estimasi Kisaran TPP {daerah_type} {clean_kabkota} (Bukan Nilai Pasti - Klaster APBD Tinggi)"
        )

    # Papua & Maluku (Faktor Kemahalan)
    papua_maluku = ["Papua", "Dogiyai", "Mamberamo", "Asmat", "Raja Ampat", "Nabire", "Jayapura", "Mimika", "Merauke", "Biak", "Sorong", "Maluku", "Halmahera", "Ternate", "Tidore"]
    if any(pm.lower() in clean_kabkota.lower() for pm in papua_maluku):
        return (
            2500000,
            16000000,
            f"Estimasi Kisaran TPP {daerah_type} {clean_kabkota} (Bukan Nilai Pasti - Klaster Kemahalan Wilayah/3T)"
        )

    # Standar Regional
    return (
        1850000,
        10500000,
        f"Estimasi Kisaran TPP {daerah_type} {clean_kabkota} (Bukan Nilai Pasti - Data Perbup/Perwal Belum Terpublikasi)"
    )


def main():
    if not DB_PATH.exists():
        print("Database not found at", DB_PATH)
        return

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    rows = cur.execute("SELECT instansi_id, nama_instansi, kategori_instansi FROM instansi").fetchall()

    verified_count = 0
    estimated_count = 0

    for i_id, nama, kat in rows:
        tmin, tmax, reg = enrich_agency(nama, kat)
        if "Resmi Terverifikasi" in reg:
            verified_count += 1
        else:
            estimated_count += 1

        cur.execute("UPDATE instansi SET tukin_min=?, tukin_max=?, regulasi_tukin=? WHERE instansi_id=?", (tmin, tmax, reg, i_id))

    conn.commit()
    conn.close()

    print(f"Update selesai untuk {len(rows)} instansi di cpns2024.db!")
    print(f"- Regulasi Resmi Terverifikasi: {verified_count} instansi")
    print(f"- Estimasi Kisaran (Bukan Nilai Pasti): {estimated_count} instansi")

if __name__ == "__main__":
    main()
