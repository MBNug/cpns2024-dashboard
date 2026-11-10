"""
SSCASN CPNS 2024 ETL & 3NF Normalization Pipeline
Reads /data/raw_cpns_2024.csv, normalizes many-to-many major qualifications,
classifies agency categories, assigns civil servant rank (golongan) & PP 5/2024 CPNS 80% base salary,
and populates /data/cpns2024.db.
"""

import os
import re
import csv
import sys
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("etl_normalize")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

RAW_CSV_PATH = DATA_DIR / "raw_cpns_2024.csv"
DB_PATH = DATA_DIR / "cpns2024.db"
SCHEMA_PATH = SCRIPTS_DIR / "schema.sql"

# PP No. 5 Tahun 2024 Mapping
GOLONGAN_MAPPING = {
    "SMA/SMK": {"gol": "II/a", "full": 2184000, "cpns_80": 1747200, "rank": 1},
    "D-III": {"gol": "II/c", "full": 2485900, "cpns_80": 1988720, "rank": 2},
    "D-IV": {"gol": "III/a", "full": 2785700, "cpns_80": 2228560, "rank": 3},
    "S-1": {"gol": "III/a", "full": 2785700, "cpns_80": 2228560, "rank": 3},
    "S-2": {"gol": "III/b", "full": 2903600, "cpns_80": 2322880, "rank": 4},
    "Profesi": {"gol": "III/b", "full": 2903600, "cpns_80": 2322880, "rank": 4},
    "S-3/Spesialis": {"gol": "III/c", "full": 3026400, "cpns_80": 2421120, "rank": 5},
}


def classify_instansi(nama_instansi: str) -> str:
    """Classify agency category into 'Provinsi', 'Kabupaten/Kota', or 'Pusat'."""
    nama = nama_instansi.strip()
    if nama.startswith("Pemerintah Provinsi"):
        return "Provinsi"
    elif nama.startswith("Pemerintah Kab.") or nama.startswith("Pemerintah Kota"):
        return "Kabupaten/Kota"
    return "Pusat"


def get_tukin_info(nama_instansi: str, kategori: str) -> Tuple[int, int, str]:
    """Provide authentic regulatory and baseline tukin/TPP data using verified rules or estimated regional ranges."""
    from scripts.enrich_tukin import enrich_agency
    return enrich_agency(nama_instansi, kategori)


def extract_jenjang(nama_jurusan: str) -> str:
    """Extract education tier (jenjang) using regex rule hierarchy."""
    s = nama_jurusan.strip().upper()

    # Priority 1: Exact prefix matches per specification
    if re.match(r"^(SLTA|SMA|SMK|PERSAMAAN SLTA)", s):
        return "SMA/SMK"
    if re.match(r"^D-?III\b", s):
        return "D-III"
    if re.match(r"^D-?IV\b", s):
        return "D-IV"
    if re.match(r"^S-?1\b", s):
        return "S-1"
    if re.match(r"^S-?2\b", s):
        return "S-2"
    if re.match(r"^(PROFESI|DOKTER UMUM|DOKTER GIGI|DOKTER\b|APOTEKER|NERS)", s):
        return "Profesi"
    if re.match(r"^(S-?3\b|SPESIALIS|SUBSPESIALIS)", s):
        return "S-3/Spesialis"

    # Priority 2: Keyword search within major name
    if "SPESIALIS" in s or "SUBSPESIALIS" in s or "S-3" in s:
        return "S-3/Spesialis"
    if "PROFESI" in s or "DOKTER" in s or "APOTEKER" in s or "NERS" in s:
        return "Profesi"
    if "S-2" in s or "MAGISTER" in s:
        return "S-2"
    if "D-IV" in s or "DIV" in s or "SARJANA TERAPAN" in s:
        return "D-IV"
    if "D-III" in s or "DIII" in s or "AHLI MADYA" in s:
        return "D-III"
    if "SLTA" in s or "SMA" in s or "SMK" in s:
        return "SMA/SMK"
    if "S-1" in s or "S1" in s or "SARJANA" in s:
        return "S-1"

    # Default fallback
    return "S-1"


def init_database(db_path: Path, schema_path: Path, reset: bool = False) -> sqlite3.Connection:
    """Initialize SQLite database with schema and WAL pragma."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if reset and db_path.exists():
        try:
            # Safely close any handles and remove old db file
            conn = sqlite3.connect(str(db_path))
            conn.close()
            db_path.unlink()
            for extra in [f"{db_path}-wal", f"{db_path}-shm"]:
                if os.path.exists(extra):
                    os.unlink(extra)
        except Exception as e:
            logger.warning(f"Could not unlink db file directly ({e}), dropping tables instead.")
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA foreign_keys = OFF;")
            for tbl in ["formasi_jurusan", "formasi", "jurusan", "instansi"]:
                conn.execute(f"DROP TABLE IF EXISTS {tbl}")
            conn.commit()
            conn.close()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA synchronous = NORMAL;")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    logger.info(f"Database schema initialized at {db_path} with WAL mode.")
    return conn


def run_etl(csv_path: Path, db_path: Path, schema_path: Path, reset: bool = True) -> None:
    """Run full ETL pipeline from raw CSV to normalized SQLite tables."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Source raw CSV not found at {csv_path}. Run scraper_sscasn.py first.")

    conn = init_database(db_path, schema_path, reset=reset)
    cur = conn.cursor()
    cur.execute("PRAGMA synchronous = OFF;")

    logger.info(f"Reading raw records from {csv_path}...")

    # Caches for deduplication
    instansi_cache: Dict[str, int] = {}  # nama_instansi -> instansi_id
    jurusan_cache: Dict[str, Tuple[int, str]] = {}  # nama_jurusan -> (jurusan_id, jenjang)

    # Pre-populate caches if database already has rows
    for row in cur.execute("SELECT instansi_id, nama_instansi FROM instansi"):
        instansi_cache[row[1]] = row[0]

    for row in cur.execute("SELECT jurusan_id, nama_jurusan, jenjang FROM jurusan"):
        jurusan_cache[row[1]] = (row[0], row[2])

    formasi_records = []
    formasi_jurusan_records: Set[Tuple[str, int]] = set()

    rows_read = 0
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_read += 1
            f_id = row["formasi_id"].strip()
            ins_nm = row["ins_nm"].strip()
            jabatan_nm = row["jabatan_nm"].strip()
            lokasi_nm = row["lokasi_nm"].strip()
            jenis_formasi = (row.get("formasi_nm") or "UMUM").strip()
            jumlah_formasi = max(1, int(float(row.get("jumlah_formasi") or 1)))
            gaji_min = int(float(row.get("gaji_min") or 0))
            gaji_max = int(float(row.get("gaji_max") or 0))
            pendidikan_raw = (row.get("pendidikan_nm") or "").strip()

            # 1. Resolve Instansi
            if ins_nm not in instansi_cache:
                kategori = classify_instansi(ins_nm)
                kode_ins = f"INS-{len(instansi_cache) + 1:04d}"
                tukin_min, tukin_max, regulasi = get_tukin_info(ins_nm, kategori)
                cur.execute(
                    "INSERT INTO instansi (kode_instansi, nama_instansi, kategori_instansi, tukin_min, tukin_max, regulasi_tukin) VALUES (?, ?, ?, ?, ?, ?)",
                    (kode_ins, ins_nm, kategori, tukin_min, tukin_max, regulasi)
                )
                instansi_cache[ins_nm] = cur.lastrowid

            instansi_id = instansi_cache[ins_nm]

            # 2. Parse and Unnest Pendidikan (Many-to-Many)
            raw_splits = [p.strip().upper() for p in pendidikan_raw.split("/") if p.strip()]
            if not raw_splits:
                raw_splits = ["SEMUA JURUSAN"]

            matched_tiers = []
            for j_nama in raw_splits:
                if j_nama not in jurusan_cache:
                    tier = extract_jenjang(j_nama)
                    cur.execute(
                        "INSERT OR IGNORE INTO jurusan (jenjang, nama_jurusan) VALUES (?, ?)",
                        (tier, j_nama)
                    )
                    # Retrieve ID if ignored or inserted
                    cur.execute("SELECT jurusan_id, jenjang FROM jurusan WHERE nama_jurusan = ?", (j_nama,))
                    j_id, j_tier = cur.fetchone()
                    jurusan_cache[j_nama] = (j_id, j_tier)

                j_id, j_tier = jurusan_cache[j_nama]
                matched_tiers.append(j_tier)
                formasi_jurusan_records.add((f_id, j_id))

            # 3. Determine Formation Golongan & Base Salary
            # Pick lowest rank among required majors to ensure minimum eligibility entry point
            min_tier = min(
                matched_tiers,
                key=lambda t: GOLONGAN_MAPPING.get(t, GOLONGAN_MAPPING["S-1"])["rank"]
            )
            tier_info = GOLONGAN_MAPPING.get(min_tier, GOLONGAN_MAPPING["S-1"])
            golongan_awal = tier_info["gol"]
            gaji_pokok_cpns_80 = tier_info["cpns_80"]

            # 4. Competition Metrics & Status
            jumlah_pelamar = int(float(row.get("jumlah_ms") or 0))
            kuota = max(1, jumlah_formasi)
            rasio_kompetisi = round(jumlah_pelamar / kuota, 2)
            peluang_lolos_pct = 100.0 if jumlah_pelamar == 0 else round(min((kuota / jumlah_pelamar) * 100.0, 100.0), 2)

            if jumlah_pelamar == 0:
                status_keketatan = "Tanpa Pelamar"
            elif rasio_kompetisi <= 1.0:
                status_keketatan = "Sangat Longgar"
            elif rasio_kompetisi <= 15.0:
                status_keketatan = "Moderat"
            else:
                status_keketatan = "Sangat Ketat"

            formasi_records.append((
                f_id,
                instansi_id,
                jabatan_nm,
                lokasi_nm,
                jenis_formasi,
                jumlah_formasi,
                jumlah_pelamar,
                rasio_kompetisi,
                peluang_lolos_pct,
                status_keketatan,
                gaji_min,
                gaji_max,
                golongan_awal,
                gaji_pokok_cpns_80,
                pendidikan_raw
            ))

            if len(formasi_records) >= 10000:
                cur.executemany(
                    """
                    INSERT OR REPLACE INTO formasi (
                        formasi_id, instansi_id, jabatan_nm, lokasi_nm, jenis_formasi,
                        jumlah_formasi, jumlah_pelamar, rasio_kompetisi, peluang_lolos_pct,
                        status_keketatan, gaji_min, gaji_max, golongan_awal,
                        gaji_pokok_cpns_80, pendidikan_raw
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    formasi_records
                )
                cur.executemany(
                    """
                    INSERT OR IGNORE INTO formasi_jurusan (formasi_id, jurusan_id)
                    VALUES (?, ?)
                    """,
                    list(formasi_jurusan_records)
                )
                conn.commit()
                logger.info(f"Processed & committed {rows_read:,} rows...")
                formasi_records.clear()
                formasi_jurusan_records.clear()

    # Flush remaining records
    if formasi_records:
        logger.info(f"Inserting remaining {len(formasi_records)} formasi records...")
        cur.executemany(
            """
            INSERT OR REPLACE INTO formasi (
                formasi_id, instansi_id, jabatan_nm, lokasi_nm, jenis_formasi,
                jumlah_formasi, jumlah_pelamar, rasio_kompetisi, peluang_lolos_pct,
                status_keketatan, gaji_min, gaji_max, golongan_awal,
                gaji_pokok_cpns_80, pendidikan_raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            formasi_records
        )
        cur.executemany(
            """
            INSERT OR IGNORE INTO formasi_jurusan (formasi_id, jurusan_id)
            VALUES (?, ?)
            """,
            list(formasi_jurusan_records)
        )
        conn.commit()
        formasi_records.clear()
        formasi_jurusan_records.clear()

    cur.execute("PRAGMA synchronous = NORMAL;")

    # Verification counts
    count_instansi = cur.execute("SELECT COUNT(*) FROM instansi").fetchone()[0]
    count_jurusan = cur.execute("SELECT COUNT(*) FROM jurusan").fetchone()[0]
    count_formasi = cur.execute("SELECT COUNT(*) FROM formasi").fetchone()[0]
    count_fj = cur.execute("SELECT COUNT(*) FROM formasi_jurusan").fetchone()[0]
    total_kuota = cur.execute("SELECT SUM(jumlah_formasi) FROM formasi").fetchone()[0]
    total_pelamar = cur.execute("SELECT SUM(jumlah_pelamar) FROM formasi").fetchone()[0]
    total_kosong = cur.execute("SELECT COUNT(*) FROM formasi WHERE jumlah_pelamar = 0").fetchone()[0]

    conn.close()

    logger.info("=== ETL NORMALIZATION COMPLETE ===")
    logger.info(f"Total Raw Rows Processed: {rows_read}")
    logger.info(f"Normalized Instansi:     {count_instansi}")
    logger.info(f"Distinct Jurusan:        {count_jurusan}")
    logger.info(f"Total Formasi:           {count_formasi}")
    logger.info(f"Total Kuota Formasi:     {total_kuota}")
    logger.info(f"Total Pelamar (MS):      {total_pelamar}")
    logger.info(f"Formasi 0 Pelamar:       {total_kosong}")
    logger.info(f"Formasi-Jurusan Links:   {count_fj}")


if __name__ == "__main__":
    run_etl(RAW_CSV_PATH, DB_PATH, SCHEMA_PATH)
