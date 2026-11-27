import sqlite3
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from backend.main import DB_PATH, app
import parse_2024_all as p24


class Scores2024Phase2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_parser_unit_invariants(self) -> None:
        # Arithmetic validator accepts exact scores and rejects fabricated totals/weighted mismatch
        self.assertTrue(p24._valid_scores(100, 140, 195, 435, 31.636, 75.0, 45.0, 76.636))
        self.assertFalse(p24._valid_scores(100, 140, 195, 436, 31.636, 75.0, 45.0, 76.636))
        self.assertFalse(p24._valid_scores(100, 140, 195, 435, 35.0, 75.0, 45.0, 80.0))

        # Column-reordered REKAP table ("1 2 3 4 5 6 7 10") extracts lulus_akhir cleanly
        rekap_txt = (
            "REKAP HASIL INTEGRASI SKD DAN SKB\nPENGADAAN CPNS 2024\n"
            "1 2 3 4 5 6 7 10\n15 5 1 15 0 10 0 5\nPeserta\n"
        )
        cnts = p24.parse_rekap_counts_v2(rekap_txt)
        self.assertIsNotNone(cnts)
        self.assertEqual(cnts["peserta_skb"], 15)
        self.assertEqual(cnts["jumlah_formasi"], 5)
        self.assertEqual(cnts["lulus_akhir"], 5)

        # Wrapped Lokasi Formasi + BNPT Instansi-before-Jabatan + comma-decimal Ringkas parsing
        hdr = p24.parse_rekap_header_v2(
            "PANITIA SELEKSI NASIONAL PENGADAAN CASN 2024\n"
            "REKAP HASIL INTEGRASI SKD DAN SKB\n"
            "Instansi : 4060 - Badan Nasional Penanggulangan Terorisme 194\n"
            "Jabatan Formasi : JF0000334 - ANALIS HUKUM AHLI PERTAMA 2\n"
            "Lokasi Formasi : 40600023 - Badan Nasional Penanggulangan Terorisme | Biro Umum 2\n"
            "Jenis Formasi : 1 - UMUM 2\n"
            "Pendidikan S-1 HUKUM 2\n"
        )
        self.assertEqual(hdr["jab_kode"], "JF0000334")
        self.assertEqual(hdr["jabatan_nm"], "ANALIS HUKUM AHLI PERTAMA")
        self.assertEqual(hdr["lokasi_nm"], "Badan Nasional Penanggulangan Terorisme | Biro Umum")
        self.assertEqual(hdr["jenis_formasi"], "UMUM")

    def test_sqlite_scores_2024_coverage_and_math_integrity(self) -> None:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            tables = {
                r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
            self.assertIn("formasi_scores_2024", tables)
            self.assertIn("scores_2024_sources", tables)

            tot_rows, ag_count = conn.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT f.instansi_id)
                FROM formasi_scores_2024 fs
                JOIN formasi f ON f.formasi_id = fs.formasi_id
                """
            ).fetchone()
            self.assertGreaterEqual(ag_count, 175)
            self.assertGreaterEqual(tot_rows, 50000)

            bad = conn.execute(
                """
                SELECT COUNT(*) FROM formasi_scores_2024
                WHERE (na_n > 0 AND (na_min > na_median OR na_median > na_max OR na_max > 100.05))
                   OR (skd_n > 0 AND (skd_min > skd_median OR skd_median > skd_max OR skd_max > 550))
                   OR (skb_n > 0 AND (skb_min > skb_median OR skb_median > skb_max OR skb_max > 100.05))
                   OR (skd_skb_n > 0 AND skd_n > 0 AND skd_skb_min > skd_min)
                   OR n_lulus > peserta_skb
                """
            ).fetchone()[0]
            self.assertEqual(bad, 0)
        finally:
            conn.close()

    def test_api_scores_2024_all_agency_tiers(self) -> None:
        stats = self.client.get("/api/stats").json()
        self.assertGreaterEqual(stats["scores_2024_agencies"], 175)
        self.assertGreaterEqual(stats["scores_2024_formasi"], 50000)

        # Verify Pusat (BRIN, BKN, ATR/BPN), Provinsi (DKI Jakarta, Riau), and Kab/Kota (Tangerang, Merangin)
        sample_agencies = (
            "Badan Riset dan Inovasi Nasional",
            "Badan Kepegawaian Negara",
            "Badan Nasional Penanggulangan Terorisme",
            "Pemerintah Provinsi Daerah Khusus Ibukota Jakarta",
            "Pemerintah Provinsi Riau",
            "Pemerintah Kab. Tangerang",
            "Pemerintah Kab. Merangin",
            "Pemerintah Kota Padang",
        )
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        try:
            for agency_nm in sample_agencies:
                row = conn.execute(
                    """
                    SELECT fs.formasi_id
                    FROM formasi_scores_2024 fs
                    JOIN formasi f ON f.formasi_id = fs.formasi_id
                    JOIN instansi i ON i.instansi_id = f.instansi_id
                    WHERE i.nama_instansi = ? AND fs.na_n > 0
                    LIMIT 1
                    """,
                    (agency_nm,),
                ).fetchone()
                self.assertIsNotNone(row, f"No scored formation found in DB for {agency_nm}")
                res = self.client.get(f"/api/formasi/{row[0]}")
                self.assertEqual(res.status_code, 200)
                n24 = res.json().get("nilai_2024")
                self.assertIsNotNone(n24, f"Missing nilai_2024 in API for {agency_nm}")
                na = n24["nilai_akhir_lulus"]
                skd = n24["skd_lulus"]
                self.assertGreater(n24["n_lulus"], 0)
                self.assertLessEqual(na["min"], na["median"])
                self.assertLessEqual(na["median"], na["max"])
                self.assertLessEqual(n24["skd_peserta_skb"]["min"], skd["min"])
                self.assertLessEqual(skd["min"], skd["median"])
                self.assertLessEqual(skd["median"], skd["max"])
                self.assertTrue(n24["sumber"])
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
