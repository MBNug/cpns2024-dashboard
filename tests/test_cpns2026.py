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
            self.assertEqual(row_count, 570)
            self.assertEqual(kuota_sum, 3242)

            inst_counts = dict(
                cur.execute(
                    "SELECT instansi_id, COALESCE(SUM(jumlah_formasi), 0) FROM formasi GROUP BY instansi_id"
                ).fetchall()
            )
            self.assertEqual(
                inst_counts,
                {"KEMENKEU": 1915, "BPK": 952, "BSSN": 200, "KEJAGUNG": 175, "KEMENKES": 0},
            )

            # Verify Kemenkeu 1..374 remains intact without duplicates
            kemenkeu_nos = [
                r[0]
                for r in cur.execute(
                    "SELECT no_urut FROM formasi WHERE instansi_id = 'KEMENKEU' ORDER BY no_urut"
                ).fetchall()
            ]
            self.assertEqual(kemenkeu_nos, list(range(1, 375)))

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
            self.assertEqual(non_nulls, (53, 0, 0, 0, 0, 51, 51, 49))
        finally:
            conn.close()

    def test_stats_2026_endpoint(self) -> None:
        r = self.client.get("/api/2026/stats")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertEqual(d["total_formasi_rows"], 570)
        self.assertEqual(d["total_kuota"], 3242)
        self.assertEqual(d["pusat_rows"], 570)
        self.assertEqual(d["daerah_rows"], 0)
        self.assertEqual(d["distinct_instansi"], 5)
        self.assertIsNone(d["total_pelamar"])
        self.assertIsNone(d["total_formasi_kosong"])
        self.assertIsNone(d["avg_rasio"])
        self.assertEqual(d["median_gaji_min"], 17000000)
        self.assertEqual(d["median_gaji_max"], 18000000)
        self.assertFalse(d["has_applicant_data"])
        self.assertTrue(d["has_salary_data"])
        self.assertTrue(d["has_jenis_formasi"])

    def test_filters_and_search_2026(self) -> None:
        rf = self.client.get("/api/2026/filters")
        self.assertEqual(rf.status_code, 200)
        fd = rf.json()
        self.assertEqual(len(fd["instansi"]), 5)
        self.assertEqual(len(fd["unit_eselon1"]), 57)
        self.assertEqual(len(fd["jabatan"]), 58)
        self.assertEqual(
            sorted(fd["jenis_formasi"]),
            ["PENYANDANG DISABILITAS", "PUTRA/PUTRI PAPUA", "UMUM"],
        )
        self.assertEqual(fd["status_keketatan"], [])

        r_jf = self.client.get("/api/2026/formasi", params={"jenis_formasi": "PENYANDANG DISABILITAS"})
        self.assertEqual(r_jf.status_code, 200)
        self.assertEqual(r_jf.json()["total"], 5)
        self.assertEqual(r_jf.json()["total_kuota_filtered"], 24)

        r_papua = self.client.get("/api/2026/formasi", params={"jenis_formasi": "PUTRA/PUTRI PAPUA"})
        self.assertEqual(r_papua.status_code, 200)
        self.assertEqual(r_papua.json()["total"], 2)
        self.assertEqual(r_papua.json()["total_kuota_filtered"], 12)

        r_jur = self.client.get("/api/2026/filters/jurusan", params={"q": "SMA/SEDERAJAT"})
        self.assertEqual(r_jur.status_code, 200)
        self.assertTrue(any(item["jurusan_nm"] == "SMA/SEDERAJAT" for item in r_jur.json()))

        # Check Instansi filtering for BPK (SSCASN live), BSSN, Kejaksaan Agung, and Kemenkes (null quota)
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

        # Check Jabatan breakdown matches verified decree counts
        r_jab = self.client.get("/api/2026/formasi", params={"jabatan": "PENELAAH TEKNIS KEBIJAKAN"})
        self.assertEqual(r_jab.status_code, 200)
        jd = r_jab.json()
        self.assertEqual(jd["total"], 150)
        self.assertEqual(jd["total_kuota_filtered"], 1068)

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

        # Verify Profesi tier resolves to III/b on Kejagung Apoteker
        r_kej_det = self.client.get("/api/2026/formasi/2026-KEJAGUNG-B-001")
        self.assertEqual(r_kej_det.status_code, 200)
        self.assertEqual(r_kej_det.json()["golongan_kode"], "III/b")

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
        self.assertEqual(ana["total_rows"], 570)
        self.assertEqual(ana["total_kuota"], 3242)
        self.assertEqual(len(ana["instansi_dist"]), 5)
        self.assertEqual(ana["keketatan_dist"], [])
        self.assertFalse(ana["has_applicant_data"])

        r_csv = self.client.get("/api/2026/export")
        self.assertEqual(r_csv.status_code, 200)
        reader = list(csv.reader(io.StringIO(r_csv.content.decode("utf-8-sig"))))
        self.assertEqual(len(reader), 571)  # 1 header + 570 rows
        # Empty columns for Pelamar & Gaji Min/Max on Kemenkeu row 1
        self.assertEqual(reader[1][10], "")  # Jenis Formasi
        self.assertEqual(reader[1][11], "")  # Jumlah Pelamar
        self.assertEqual(reader[1][14], "")  # Gaji Min

    def test_html_pages_and_2024_non_regression(self) -> None:
        r_2026 = self.client.get("/cpns-2026")
        self.assertEqual(r_2026.status_code, 200)
        self.assertIn("CPNS 2026 Explorer", r_2026.text)

        r_sumber = self.client.get("/sumber-data")
        self.assertEqual(r_sumber.status_code, 200)
        self.assertIn("/cpns-2026", r_sumber.text)

        r_raw = self.client.get("/api/2026/download/raw-csv")
        self.assertEqual(r_raw.status_code, 200)
        self.assertIn("KepmenPANRB No. 675 Tahun 2026", r_raw.text)
        self.assertIn("KepmenPANRB No. 676 Tahun 2026", r_raw.text)
        self.assertIn("KepmenPANRB No. 638 Tahun 2026", r_raw.text)
        self.assertIn("SSCASN BKN Resmi TA 2026", r_raw.text)
        self.assertIn("SE Dirjen SDMK Kemenkes No. HK.02.02/F/4023/2026", r_raw.text)

        r_db = self.client.get("/api/2026/download/sqlite-db")
        self.assertEqual(r_db.status_code, 200)
        self.assertGreater(len(r_db.content), 100000)

        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("/cpns-2026", r_root.text)

        r_stats_2024 = self.client.get("/api/stats")
        self.assertEqual(r_stats_2024.status_code, 200)
        self.assertEqual(r_stats_2024.json()["total_formasi"], 111921)


if __name__ == "__main__":
    unittest.main()
