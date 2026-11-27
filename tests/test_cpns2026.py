"""Tests for CPNS 2026 dataset integrity, API endpoints, and CPNS 2024 non-regression."""

import csv
import io
import sqlite3
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import app  # noqa: E402
from backend.cpns2026 import DB_PATH, DB_GZ_PATH, RAW_CSV_PATH, ensure_2026_database_ready  # noqa: E402


class Cpns2026DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_2026_database_ready()
        cls.client = TestClient(app)

    def test_database_and_artifacts_exist(self) -> None:
        self.assertTrue(DB_PATH.exists(), "cpns2026.db must exist")
        self.assertTrue(DB_GZ_PATH.exists(), "cpns2026.db.gz must exist for Render deploy")
        self.assertTrue(RAW_CSV_PATH.exists(), "raw_cpns_2026.csv must exist")

    def test_sqlite_integrity_and_no_hallucination_nulls(self) -> None:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cur = conn.cursor()
        try:
            row_count, kuota_sum = cur.execute(
                "SELECT COUNT(*), SUM(jumlah_formasi) FROM formasi"
            ).fetchone()
            self.assertEqual(row_count, 1169)
            self.assertEqual(kuota_sum, 6546)

            inst_counts = dict(
                cur.execute(
                    "SELECT instansi_id, COALESCE(SUM(jumlah_formasi), 0) FROM formasi GROUP BY instansi_id"
                ).fetchall()
            )
            self.assertEqual(
                inst_counts,
                {
                    "BPKP": 2007,
                    "KEMENKEU": 1915,
                    "KEMENKUM": 1297,
                    "BPK": 952,
                    "BSSN": 200,
                    "KEJAGUNG": 175,
                    "KEMENKES": 0,
                },
            )

            # Verify Kemenkeu 1..374 and BPKP 1..554 remain intact without duplicates
            kemenkeu_nos = [
                r[0]
                for r in cur.execute(
                    "SELECT no_urut FROM formasi WHERE instansi_id = 'KEMENKEU' ORDER BY no_urut"
                ).fetchall()
            ]
            self.assertEqual(kemenkeu_nos, list(range(1, 375)))
            bpkp_nos = [
                r[0]
                for r in cur.execute(
                    "SELECT no_urut FROM formasi WHERE instansi_id = 'BPKP' ORDER BY no_urut"
                ).fetchall()
            ]
            self.assertEqual(bpkp_nos, list(range(1, 555)))

            # Verify unpublished fields are NULL and Kemenkes keeps NULL quota (no fake 0)
            non_nulls = cur.execute(
                """
                SELECT
                    COUNT(jenis_formasi),
                    COUNT(jumlah_pelamar),
                    COUNT(rasio_kompetisi),
                    COUNT(peluang_lolos_pct),
                    COUNT(status_keketatan),
                    COUNT(gaji_min),
                    COUNT(gaji_max),
                    SUM(CASE WHEN jumlah_formasi IS NULL THEN 1 ELSE 0 END)
                FROM formasi
                """
            ).fetchone()
            self.assertEqual(non_nulls, (652, 0, 0, 0, 0, 605, 605, 49))

            # Ensure jurusan catalog merges case-variants (e.g. S-1 Informatika + S-1 INFORMATIKA)
            dup_jurusan = cur.execute(
                """
                SELECT UPPER(TRIM(jurusan_nm))
                FROM jurusan
                GROUP BY UPPER(TRIM(jurusan_nm))
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            self.assertEqual(dup_jurusan, [])
        finally:
            conn.close()

    def test_stats_2026_endpoint(self) -> None:
        r = self.client.get("/api/2026/stats")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["total_formasi_rows"], 1169)
        self.assertEqual(d["total_kuota"], 6546)
        self.assertEqual(d["pusat_rows"], 1169)
        self.assertEqual(d["daerah_rows"], 0)
        self.assertEqual(d["distinct_instansi"], 7)
        self.assertIsNone(d["total_pelamar"])
        self.assertIsNone(d["total_formasi_kosong"])
        self.assertIsNone(d["avg_rasio"])
        self.assertEqual(d["median_gaji_min"], 8300000)
        self.assertEqual(d["median_gaji_max"], 10000000)
        self.assertFalse(d["has_applicant_data"])
        self.assertTrue(d["has_salary_data"])
        self.assertTrue(d["has_jenis_formasi"])

    def test_filters_and_search_2026(self) -> None:
        rf = self.client.get("/api/2026/filters")
        self.assertEqual(rf.status_code, 200)
        fd = rf.json()
        self.assertEqual(len(fd["instansi"]), 7)
        self.assertEqual(len(fd["unit_eselon1"]), 69)
        self.assertEqual(len(fd["jabatan"]), 86)
        self.assertEqual(
            sorted(fd["jenis_formasi"]),
            [
                "ORANG ASLI PAPUA",
                "PENYANDANG DISABILITAS",
                "PUTRA/PUTRI LULUSAN TERBAIK",
                "PUTRA/PUTRI PAPUA",
                "UMUM",
            ],
        )
        self.assertEqual(fd["status_keketatan"], [])
        k24_map = {x["status"]: x for x in fd["status_keketatan_2024"]}
        self.assertEqual(k24_map["Sangat Ketat"]["formasi_count"], 243)
        self.assertEqual(k24_map["Moderat"]["formasi_count"], 130)
        self.assertEqual(k24_map["Tanpa Pelamar"]["formasi_count"], 1)
        self.assertEqual(fd["unmatched_2024_count"], 795)

        r_k24_tight = self.client.get("/api/2026/formasi", params={"keketatan_2024": "Sangat Ketat"})
        self.assertEqual(r_k24_tight.status_code, 200)
        self.assertEqual(r_k24_tight.json()["total"], 243)
        self.assertEqual(r_k24_tight.json()["total_kuota_filtered"], 2111)
        self.assertTrue(all(x["status_keketatan_2024"] == "Sangat Ketat" for x in r_k24_tight.json()["items"]))

        r_k24_mod = self.client.get("/api/2026/formasi", params={"keketatan_2024": "Moderat"})
        self.assertEqual(r_k24_mod.status_code, 200)
        self.assertEqual(r_k24_mod.json()["total"], 130)
        self.assertEqual(r_k24_mod.json()["total_kuota_filtered"], 384)

        r_k24_zero = self.client.get("/api/2026/formasi", params={"keketatan_2024": "Tanpa Pelamar"})
        self.assertEqual(r_k24_zero.status_code, 200)
        self.assertEqual(r_k24_zero.json()["total"], 1)
        self.assertEqual(r_k24_zero.json()["total_kuota_filtered"], 0)

        r_k24_none = self.client.get("/api/2026/formasi", params={"keketatan_2024": "__NONE__"})
        self.assertEqual(r_k24_none.status_code, 200)
        self.assertEqual(r_k24_none.json()["total"], 795)
        self.assertEqual(r_k24_none.json()["total_kuota_filtered"], 4051)
        self.assertTrue(all(x["status_keketatan_2024"] is None for x in r_k24_none.json()["items"]))

        r_k24_sorted = self.client.get(
            "/api/2026/formasi",
            params={
                "instansi": "Badan Pengawasan Keuangan dan Pembangunan",
                "keketatan_2024": "Sangat Ketat",
                "sort_by": "rasio_2024_desc",
                "limit": 5,
            },
        )
        self.assertEqual(r_k24_sorted.status_code, 200)
        ratios = [x["rasio_2024"] for x in r_k24_sorted.json()["items"] if x["rasio_2024"] is not None]
        self.assertEqual(ratios, sorted(ratios, reverse=True))

        r_jf = self.client.get("/api/2026/formasi", params={"jenis_formasi": "PENYANDANG DISABILITAS"})
        self.assertEqual(r_jf.status_code, 200)
        self.assertEqual(r_jf.json()["total"], 44)
        self.assertEqual(r_jf.json()["total_kuota_filtered"], 91)

        r_terbaik = self.client.get("/api/2026/formasi", params={"jenis_formasi": "PUTRA/PUTRI LULUSAN TERBAIK"})
        self.assertEqual(r_terbaik.status_code, 200)
        self.assertEqual(r_terbaik.json()["total"], 13)
        self.assertEqual(r_terbaik.json()["total_kuota_filtered"], 26)

        r_oap = self.client.get("/api/2026/formasi", params={"jenis_formasi": "ORANG ASLI PAPUA"})
        self.assertEqual(r_oap.status_code, 200)
        self.assertEqual(r_oap.json()["total"], 8)
        self.assertEqual(r_oap.json()["total_kuota_filtered"], 26)

        r_papua = self.client.get("/api/2026/formasi", params={"jenis_formasi": "PUTRA/PUTRI PAPUA"})
        self.assertEqual(r_papua.status_code, 200)
        self.assertEqual(r_papua.json()["total"], 2)
        self.assertEqual(r_papua.json()["total_kuota_filtered"], 12)

        r_jur = self.client.get("/api/2026/filters/jurusan", params={"q": "SMA/SEDERAJAT"})
        self.assertEqual(r_jur.status_code, 200)
        self.assertTrue(any(item["jurusan_nm"] == "SMA/SEDERAJAT" for item in r_jur.json()))

        r_inf = self.client.get("/api/2026/filters/jurusan", params={"q": "S-1 Informatika"})
        self.assertEqual(r_inf.status_code, 200)
        inf_exact = [x for x in r_inf.json() if x["jurusan_nm"].upper() == "S-1 INFORMATIKA"]
        self.assertEqual(len(inf_exact), 1)
        self.assertEqual(inf_exact[0]["jurusan_nm"], "S-1 Informatika")
        self.assertEqual(inf_exact[0]["formasi_count"], 50)
        self.assertEqual(inf_exact[0]["total_kuota"], 426)

        # Check Instansi filtering for BPKP, BPK (SSCASN live), BSSN, Kejaksaan Agung, and Kemenkes
        r_bpkp = self.client.get("/api/2026/formasi", params={"instansi": "Badan Pengawasan Keuangan dan Pembangunan"})
        self.assertEqual(r_bpkp.status_code, 200)
        self.assertEqual(r_bpkp.json()["total"], 554)
        self.assertEqual(r_bpkp.json()["total_kuota_filtered"], 2007)
        self.assertEqual(r_bpkp.json()["items"][0]["gaji_min"], 9600000)
        self.assertEqual(r_bpkp.json()["items"][0]["gaji_max"], 11500000)
        self.assertIsNone(r_bpkp.json()["items"][0]["jumlah_pelamar"])

        r_bpk = self.client.get("/api/2026/formasi", params={"instansi": "Badan Pemeriksa Keuangan"})
        self.assertEqual(r_bpk.status_code, 200)
        self.assertEqual(r_bpk.json()["total"], 51)
        self.assertEqual(r_bpk.json()["total_kuota_filtered"], 952)
        self.assertGreater(r_bpk.json()["items"][0]["gaji_min"], 0)
        self.assertIsNone(r_bpk.json()["items"][0]["jumlah_pelamar"])

        r_bssn = self.client.get("/api/2026/formasi", params={"instansi": "Badan Siber dan Sandi Negara"})
        self.assertEqual(r_bssn.status_code, 200)
        self.assertEqual(r_bssn.json()["total"], 2)
        self.assertEqual(r_bssn.json()["total_kuota_filtered"], 200)

        r_kej = self.client.get("/api/2026/formasi", params={"instansi": "Kejaksaan Agung"})
        self.assertEqual(r_kej.status_code, 200)
        self.assertEqual(r_kej.json()["total"], 94)
        self.assertEqual(r_kej.json()["total_kuota_filtered"], 175)

        r_kemenkes = self.client.get("/api/2026/formasi", params={"instansi": "Kementerian Kesehatan"})
        self.assertEqual(r_kemenkes.status_code, 200)
        self.assertEqual(r_kemenkes.json()["total"], 49)
        self.assertEqual(r_kemenkes.json()["total_kuota_filtered"], 0)
        self.assertIsNone(r_kemenkes.json()["items"][0]["jumlah_formasi"])
        self.assertIsNone(r_kemenkes.json()["items"][0]["gaji_min"])

        r_kemenkum = self.client.get("/api/2026/formasi", params={"instansi": "Kementerian Hukum"})
        self.assertEqual(r_kemenkum.status_code, 200)
        self.assertEqual(r_kemenkum.json()["total"], 45)
        self.assertEqual(r_kemenkum.json()["total_kuota_filtered"], 1297)
        self.assertIsNone(r_kemenkum.json()["items"][0]["gaji_min"])
        self.assertIsNone(r_kemenkum.json()["items"][0]["jumlah_pelamar"])

        # Check Jabatan breakdown matches verified decree counts
        r_jab = self.client.get("/api/2026/formasi", params={"jabatan": "PENELAAH TEKNIS KEBIJAKAN"})
        self.assertEqual(r_jab.status_code, 200)
        jd = r_jab.json()
        self.assertEqual(jd["total"], 152)
        self.assertEqual(jd["total_kuota_filtered"], 1151)

        # Ensure absent fields stay null in Kemenkeu items
        item = jd["items"][0]
        self.assertIsNone(item["jumlah_pelamar"])
        self.assertIsNone(item["jenis_formasi"])
        self.assertIsNone(item["gaji_min"])
        self.assertIsNone(item["status_keketatan"])

    def test_detail_batch_analytics_and_exports_2026(self) -> None:
        r_det = self.client.get("/api/2026/formasi/2026-KEMENKEU-001")
        self.assertEqual(r_det.status_code, 200)
        det = r_det.json()
        self.assertEqual(det["no_urut"], 1)
        self.assertEqual(det["jumlah_formasi"], 43)
        self.assertEqual(det["golongan_kode"], "II/a")

        # Verify Profesi tier resolves to III/b on Kejagung Apoteker and includes 2024 comparison
        r_kej_det = self.client.get("/api/2026/formasi/2026-KEJAGUNG-B-001")
        self.assertEqual(r_kej_det.status_code, 200)
        self.assertEqual(r_kej_det.json()["golongan_kode"], "III/b")
        self.assertEqual(r_kej_det.json()["kursi_2024"], 39)
        self.assertEqual(r_kej_det.json()["pelamar_2024"], 214)

        # Verify unmatched 2026 row returns explicit no-comparison message
        r_bssn_det = self.client.get("/api/2026/formasi/2026-BSSN-001-UMUM")
        self.assertEqual(r_bssn_det.status_code, 200)
        self.assertIsNone(r_bssn_det.json()["kursi_2024"])
        self.assertEqual(r_bssn_det.json()["match_label_2024"], "Tidak ada pembanding di 2024")

        # Verify BPK Regional Jawa matches 2024 Regional Jawa (101 kursi, 12412 pelamar)
        r_bpk = self.client.get("/api/2026/formasi", params={"instansi": "Badan Pemeriksa Keuangan", "jabatan": "PEMERIKSA AHLI PERTAMA"})
        self.assertEqual(r_bpk.status_code, 200)
        jawa_row = next(x for x in r_bpk.json()["items"] if x["lokasi_nm"] == "Regional Jawa")
        self.assertEqual(jawa_row["kursi_2024"], 101)
        self.assertEqual(jawa_row["pelamar_2024"], 12412)
        self.assertEqual(jawa_row["status_keketatan_2024"], "Sangat Ketat")

        r_bpkp_aud = self.client.get("/api/2026/formasi/2026-BPKP-001")
        self.assertEqual(r_bpkp_aud.status_code, 200)
        self.assertEqual(r_bpkp_aud.json()["kursi_2024"], 100)
        self.assertEqual(r_bpkp_aud.json()["pelamar_2024"], 14756)
        self.assertEqual(r_bpkp_aud.json()["status_keketatan_2024"], "Sangat Ketat")

        self.assertEqual(self.client.get("/api/2026/formasi/INVALID-ID").status_code, 404)

        r_batch = self.client.get(
            "/api/2026/formasi-batch",
            params={"ids": "2026-KEMENKEU-001,2026-BSSN-001-UMUM"},
        )
        self.assertEqual(r_batch.status_code, 200)
        self.assertEqual([x["formasi_id"] for x in r_batch.json()], ["2026-KEMENKEU-001", "2026-BSSN-001-UMUM"])

        r_ana = self.client.get("/api/2026/analytics/top")
        self.assertEqual(r_ana.status_code, 200)
        ana = r_ana.json()
        self.assertEqual(ana["total_rows"], 1169)
        self.assertEqual(ana["total_kuota"], 6546)
        self.assertEqual(len(ana["instansi_dist"]), 7)
        self.assertEqual(ana["keketatan_dist"], [])
        self.assertEqual(sum(x["formasi_count"] for x in ana["keketatan_2024_dist"]), 1169)
        self.assertFalse(ana["has_applicant_data"])

        r_ana_k24 = self.client.get("/api/2026/analytics/top", params={"keketatan_2024": "Sangat Ketat"})
        self.assertEqual(r_ana_k24.status_code, 200)
        self.assertEqual(r_ana_k24.json()["total_rows"], 243)
        self.assertEqual(r_ana_k24.json()["total_kuota"], 2111)

        r_csv = self.client.get("/api/2026/export")
        self.assertEqual(r_csv.status_code, 200)
        reader = list(csv.reader(io.StringIO(r_csv.content.decode("utf-8-sig"))))
        self.assertEqual(len(reader), 1170)  # 1 header + 1169 rows
        # Empty columns for Pelamar & Gaji Min/Max on Kemenkeu row 1
        self.assertEqual(reader[1][10], "")  # Jenis Formasi
        self.assertEqual(reader[1][11], "")  # Jumlah Pelamar
        self.assertEqual(reader[1][14], "")  # Gaji Min

        r_csv_mod = self.client.get("/api/2026/export", params={"keketatan_2024": "Moderat"})
        self.assertEqual(r_csv_mod.status_code, 200)
        reader_mod = list(csv.reader(io.StringIO(r_csv_mod.content.decode("utf-8-sig"))))
        self.assertEqual(len(reader_mod), 131)  # 1 header + 130 rows

    def test_html_pages_and_2024_non_regression(self) -> None:
        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("CPNS 2026 Explorer", r_root.text)
        self.assertIn("/cpns-2024", r_root.text)
        self.assertIn("/static/favicon.png", r_root.text)
        self.assertIn("https://x.com/wiraaaaa27/status/2126201372244914343", r_root.text)
        self.assertIn("filter-keketatan-2024", r_root.text)

        r_fav = self.client.get("/favicon.ico")
        self.assertEqual(r_fav.status_code, 200)
        self.assertIn("image/png", r_fav.headers.get("content-type", ""))

        r_2024 = self.client.get("/cpns-2024")
        self.assertEqual(r_2024.status_code, 200)
        self.assertIn("Portal Data Formasi CPNS 2024", r_2024.text)
        self.assertIn('href="/"', r_2024.text)
        self.assertIn("/static/favicon.png", r_2024.text)

        r_2026 = self.client.get("/cpns-2026")
        self.assertEqual(r_2026.status_code, 200)
        self.assertIn("CPNS 2026 Explorer", r_2026.text)

        r_sumber = self.client.get("/sumber-data")
        self.assertEqual(r_sumber.status_code, 200)
        self.assertIn("/cpns-2024", r_sumber.text)
        self.assertIn("/static/favicon.png", r_sumber.text)

        r_raw = self.client.get("/api/2026/download/raw-csv")
        self.assertEqual(r_raw.status_code, 200)
        self.assertIn("Pengumuman BPKP No. KP.00.01/PENG-2/SU/02/2026", r_raw.text)
        self.assertIn("Pengumuman Kemenkum No. SEK.2-KP.02.01-326", r_raw.text)
        self.assertIn("KepmenPANRB No. 675 Tahun 2026", r_raw.text)
        self.assertIn("KepmenPANRB No. 676 Tahun 2026", r_raw.text)
        self.assertIn("KepmenPANRB No. 638 Tahun 2026", r_raw.text)
        self.assertIn("SSCASN BKN Resmi TA 2026", r_raw.text)
        self.assertIn("SE Dirjen SDMK Kemenkes No. HK.02.02/F/4023/2026", r_raw.text)

        r_db = self.client.get("/api/2026/download/sqlite-db")
        self.assertEqual(r_db.status_code, 200)
        self.assertGreater(len(r_db.content), 100000)

        r_stats_2024 = self.client.get("/api/stats")
        self.assertEqual(r_stats_2024.status_code, 200)
        self.assertEqual(r_stats_2024.json()["total_formasi"], 111921)

    def test_2024_exam_scores_integration(self) -> None:
        # HTML modals must contain the 2024 score containers
        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("detail-compare-2024-scores-grid", r_root.text)

        r_2024 = self.client.get("/cpns-2024")
        self.assertEqual(r_2024.status_code, 200)
        self.assertIn("modal-nilai-2024-panel", r_2024.text)

        # Unmatched BSSN 2026 row must keep null 2024 score stats
        r_bssn = self.client.get("/api/2026/formasi/2026-BSSN-001-UMUM").json()
        self.assertIsNone(r_bssn["nilai_akhir_2024_median"])
        self.assertIsNone(r_bssn["skd_2024_lulus_median"])

        # Matched 2026 rows across BPKP, Kejagung, BPK, Kemenkeu, Kemenkes must satisfy valid score bounds
        matched_ids = (
            "2026-BPKP-001",
            "04e087a2-d153-4b01-8653-41a599cf29a4",  # BPK Pemerintah / Regional Jawa
            "2026-KEJAGUNG-B-001",
            "2026-KEMENKES-01-KEAH-TIDAK",
            "2026-KEMENKEU-001",
        )
        for fid in matched_ids:
            resp = self.client.get(f"/api/2026/formasi/{fid}")
            self.assertEqual(resp.status_code, 200, f"Expected 200 for {fid}")
            d = resp.json()
            self.assertGreater(d["n_lulus_2024"], 0)
            self.assertGreater(d["n_peserta_skb_2024"], 0)
            self.assertGreater(d["nilai_akhir_2024_min"], 0)
            self.assertLessEqual(d["nilai_akhir_2024_min"], d["nilai_akhir_2024_median"])
            self.assertLessEqual(d["nilai_akhir_2024_median"], d["nilai_akhir_2024_max"])
            self.assertLessEqual(d["nilai_akhir_2024_max"], 100.0)
            self.assertLessEqual(d["skd_2024_skb_min"], d["skd_2024_lulus_min"])
            self.assertLessEqual(d["skd_2024_lulus_min"], d["skd_2024_lulus_median"])
            self.assertLessEqual(d["skd_2024_lulus_median"], d["skd_2024_lulus_max"])
            self.assertLessEqual(d["skd_2024_lulus_max"], 550)
            self.assertTrue(d["sumber_nilai_2024"])

        # Global SQLite mathematical invariants across all 373 scored rows
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            bad = conn.execute(
                """
                SELECT COUNT(*) FROM banding_2024
                WHERE nilai_akhir_2024_median IS NOT NULL
                  AND (
                    nilai_akhir_2024_min > nilai_akhir_2024_median
                    OR nilai_akhir_2024_median > nilai_akhir_2024_max
                    OR nilai_akhir_2024_max > 100.0
                    OR skd_2024_skb_min > skd_2024_lulus_min
                    OR skd_2024_lulus_min > skd_2024_lulus_median
                    OR skd_2024_lulus_median > skd_2024_lulus_max
                    OR skd_2024_lulus_max > 550
                  )
                """
            ).fetchone()[0]
            self.assertEqual(bad, 0)
        finally:
            conn.close()

        # /api/formasi/{id} (CPNS 2024) must serve exact score stats for all 6 covered agencies
        covered_2024 = {
            "BSSN": "8a03849f914ed85101914f9b2e106dff",
            "KEJAGUNG": "8a03849f914ed85101914f1de6416ac5",
            "BPKP": "8a0282659168528c01916aa6aadd1b6a",
            "KEMENKEU": "8a0384979144c5430191458c39bd2691",
            "KEMENKES": "c55ac87b-4526-4d07-8052-badd95bd2f03",
            "BPK": "8a028490914aa6ad01914ab033a10435",
        }
        for kode, fid24 in covered_2024.items():
            res = self.client.get(f"/api/formasi/{fid24}")
            self.assertEqual(res.status_code, 200)
            n24 = res.json().get("nilai_2024")
            self.assertIsNotNone(n24, f"Missing nilai_2024 for {kode} ({fid24})")
            self.assertEqual(n24["instansi_kode"], kode)
            na = n24["nilai_akhir_lulus"]
            skd = n24["skd_lulus"]
            self.assertLessEqual(na["min"], na["median"])
            self.assertLessEqual(na["median"], na["max"])
            self.assertLessEqual(n24["skd_peserta_skb"]["min"], skd["min"])
            self.assertLessEqual(skd["min"], skd["median"])
            self.assertLessEqual(skd["median"], skd["max"])

        # Non-covered 2024 agency row must stay None (zero hallucination)
        r_pemda = self.client.get("/api/formasi", params={"limit": 1, "kategori_instansi": "Kabupaten/Kota"}).json()
        other_fid = r_pemda["items"][0]["formasi_id"]
        self.assertIsNone(self.client.get(f"/api/formasi/{other_fid}").json().get("nilai_2024"))


if __name__ == "__main__":
    unittest.main()
