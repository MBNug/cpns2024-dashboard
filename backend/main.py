"""
SSCASN CPNS 2024 - FastAPI Backend
Provides REST API endpoints for stats, filters, paginated formation queries,
analytics, CSV export, and serves the dashboard frontend.
"""

import io
import csv
import math
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "cpns2024.db"
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="SSCASN CPNS 2024 Formation API",
    description="Backend API querying normalized 3NF SQLite database of CPNS 2024 formations",
    version="1.0.0"
)

# Enable CORS for local development & cross-origin frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection configured with WAL and dict row factory."""
    if not DB_PATH.exists():
        gz_path = DATA_DIR / "cpns2024.db.gz"
        raw_csv_path = DATA_DIR / "raw_cpns_2024.csv"
        schema_path = BASE_DIR / "scripts" / "schema.sql"

        if gz_path.exists():
            import gzip, shutil
            print(f"[INFO] Extracting {gz_path} to {DB_PATH}...")
            with gzip.open(str(gz_path), "rb") as f_in:
                with open(str(DB_PATH), "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        elif raw_csv_path.exists() and schema_path.exists():
            print("[INFO] Building cpns2024.db from raw_cpns_2024.csv via ETL...")
            from scripts.etl_normalize import run_etl
            run_etl(raw_csv_path, DB_PATH, schema_path)
        else:
            raise HTTPException(
                status_code=503,
                detail="Database cpns2024.db not found. Please run scripts/etl_normalize.py first."
            )

    conn = sqlite3.connect(str(DB_PATH), timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def get_median_salary(cur: sqlite3.Cursor, column: str) -> int:
    """Calculate exact median for a salary column in formasi table."""
    cur.execute(f"SELECT {column} FROM formasi WHERE {column} > 0 ORDER BY {column}")
    rows = cur.fetchall()
    if not rows:
        return 0
    n = len(rows)
    mid = n // 2
    if n % 2 == 1:
        return int(rows[mid][0])
    return int((rows[mid - 1][0] + rows[mid][0]) / 2)


@app.get("/health")
def health_check():
    """Health check endpoint verifying database connectivity."""
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM formasi").fetchone()[0]
        conn.close()
        return {"status": "ok", "database": "connected", "total_formasi": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/stats")
def get_stats():
    """Summary statistics for KPI cards including competition metrics."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*),
            SUM(jumlah_formasi),
            SUM(jumlah_pelamar),
            ROUND(AVG(rasio_kompetisi), 2),
            COUNT(CASE WHEN jumlah_pelamar = 0 THEN 1 END)
        FROM formasi
    """)
    tot_formasi, tot_kuota, tot_pelamar, avg_rasio, tot_kosong = cur.fetchone()
    tot_formasi = tot_formasi or 0
    tot_kuota = tot_kuota or 0
    tot_pelamar = tot_pelamar or 0
    avg_rasio = float(avg_rasio or 0.0)
    tot_kosong = tot_kosong or 0

    cur.execute("SELECT COUNT(*) FROM instansi")
    tot_instansi = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM jurusan")
    tot_jurusan = cur.fetchone()[0] or 0

    # Agencies by Category
    cur.execute("""
        SELECT kategori_instansi, COUNT(*) as cnt
        FROM instansi
        GROUP BY kategori_instansi
    """)
    instansi_by_kategori = {r["kategori_instansi"]: r["cnt"] for r in cur.fetchall()}

    # Formations by Jenis Formasi
    cur.execute("""
        SELECT jenis_formasi, COUNT(*) as cnt, SUM(jumlah_formasi) as kuota
        FROM formasi
        GROUP BY jenis_formasi
    """)
    jenis_formasi_stats = [
        {"jenis": r["jenis_formasi"], "count": r["cnt"], "kuota": r["kuota"]}
        for r in cur.fetchall()
    ]

    # Formations by Status Keketatan
    cur.execute("""
        SELECT status_keketatan, COUNT(*) as cnt, SUM(jumlah_formasi) as kuota, SUM(jumlah_pelamar) as pelamar
        FROM formasi
        GROUP BY status_keketatan
    """)
    keketatan_stats = [
        {"status": r["status_keketatan"], "count": r["cnt"], "kuota": r["kuota"], "pelamar": r["pelamar"]}
        for r in cur.fetchall()
    ]

    # Salary aggregates
    cur.execute("SELECT AVG(gaji_min), AVG(gaji_max) FROM formasi WHERE gaji_min > 0")
    avg_min, avg_max = cur.fetchone()
    avg_min = int(avg_min or 0)
    avg_max = int(avg_max or 0)

    median_min = get_median_salary(cur, "gaji_min")
    median_max = get_median_salary(cur, "gaji_max")

    conn.close()

    return {
        "total_formasi": tot_formasi,
        "total_kuota": tot_kuota,
        "total_pelamar": tot_pelamar,
        "avg_rasio_kompetisi": avg_rasio,
        "total_formasi_kosong": tot_kosong,
        "total_instansi": tot_instansi,
        "total_jurusan": tot_jurusan,
        "instansi_by_kategori": instansi_by_kategori,
        "jenis_formasi_stats": jenis_formasi_stats,
        "keketatan_stats": keketatan_stats,
        "gaji_median_min": median_min,
        "gaji_median_max": median_max,
        "gaji_avg_min": avg_min,
        "gaji_avg_max": avg_max,
    }


@app.get("/api/filters")
def get_filter_options():
    """Options for dropdowns and filter panels."""
    conn = get_db_connection()
    cur = conn.cursor()

    # Jenjang order
    jenjang_order = ["SMA/SMK", "D-III", "D-IV", "S-1", "S-2", "Profesi", "S-3/Spesialis"]
    cur.execute("SELECT DISTINCT jenjang FROM jurusan")
    raw_jenjang = {r["jenjang"] for r in cur.fetchall()}
    jenjang_list = [j for j in jenjang_order if j in raw_jenjang]
    for j in sorted(raw_jenjang):
        if j not in jenjang_list:
            jenjang_list.append(j)

    kategori_instansi = ["Pusat", "Provinsi", "Kabupaten/Kota"]
    status_keketatan = ["Tanpa Pelamar", "Sangat Longgar", "Moderat", "Sangat Ketat"]

    cur.execute("SELECT DISTINCT jenis_formasi FROM formasi ORDER BY jenis_formasi")
    jenis_formasi = [r["jenis_formasi"] for r in cur.fetchall()]

    cur.execute("SELECT instansi_id, nama_instansi, kategori_instansi FROM instansi ORDER BY nama_instansi")
    instansi_list = [
        {
            "instansi_id": r["instansi_id"],
            "nama_instansi": r["nama_instansi"],
            "kategori_instansi": r["kategori_instansi"]
        }
        for r in cur.fetchall()
    ]

    conn.close()

    return {
        "jenjang": jenjang_list,
        "kategori_instansi": kategori_instansi,
        "status_keketatan": status_keketatan,
        "jenis_formasi": jenis_formasi,
        "instansi": instansi_list
    }


@app.get("/api/filters/jurusan")
def autocomplete_jurusan(
    q: str = Query("", description="Keyword search for major name"),
    jenjang: Optional[str] = Query(None, description="Optional tier filter"),
    limit: int = Query(25, ge=1, le=100)
):
    """Searchable autocomplete endpoint for majors (jurusan)."""
    conn = get_db_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    if q.strip():
        conditions.append("nama_jurusan LIKE ?")
        params.append(f"%{q.strip().upper()}%")

    if jenjang and jenjang != "ALL":
        conditions.append("jenjang = ?")
        params.append(jenjang)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT jurusan_id, nama_jurusan, jenjang
        FROM jurusan
        {where_clause}
        ORDER BY nama_jurusan ASC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(query, params)
    results = [
        {"jurusan_id": r["jurusan_id"], "nama_jurusan": r["nama_jurusan"], "jenjang": r["jenjang"]}
        for r in cur.fetchall()
    ]
    conn.close()

    return results


@app.get("/api/filters/instansi")
def autocomplete_instansi(
    q: str = Query("", description="Keyword search for agency name"),
    kategori: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(25, ge=1, le=100)
):
    """Searchable autocomplete endpoint for agencies (instansi)."""
    conn = get_db_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    if q.strip():
        conditions.append("nama_instansi LIKE ?")
        params.append(f"%{q.strip()}%")

    if kategori and kategori != "ALL":
        conditions.append("kategori_instansi = ?")
        params.append(kategori)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
        SELECT instansi_id, kode_instansi, nama_instansi, kategori_instansi
        FROM instansi
        {where_clause}
        ORDER BY nama_instansi ASC
        LIMIT ?
    """
    params.append(limit)

    cur.execute(query, params)
    results = [
        {
            "instansi_id": r["instansi_id"],
            "kode_instansi": r["kode_instansi"],
            "nama_instansi": r["nama_instansi"],
            "kategori_instansi": r["kategori_instansi"]
        }
        for r in cur.fetchall()
    ]
    conn.close()

    return results


def _clean_str(val: Any) -> Optional[str]:
    if isinstance(val, str):
        s = val.strip()
        return s if s else None
    return None


def _clean_int(val: Any) -> Optional[int]:
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.strip().isdigit():
        return int(val.strip())
    return None


def build_filter_clause(
    q: Optional[str] = None,
    jurusan: Optional[str] = None,
    jurusan_id: Optional[int] = None,
    jenjang: Optional[str] = None,
    kategori_instansi: Optional[str] = None,
    instansi_id: Optional[int] = None,
    jenis_formasi: Optional[str] = None,
    gaji_min: Optional[int] = None,
    gaji_max: Optional[int] = None,
    max_rasio: Optional[float] = None,
    status_keketatan: Optional[str] = None,
    zero_applicant_only: bool = False
) -> Tuple[str, List[Any], bool]:
    """
    Build parameterized WHERE clause and detect if formasi_jurusan / jurusan joins are required.
    """
    q_str = _clean_str(q)
    jurusan_str = _clean_str(jurusan)
    jurusan_id_int = _clean_int(jurusan_id)
    jenjang_str = _clean_str(jenjang)
    kategori_str = _clean_str(kategori_instansi)
    instansi_id_int = _clean_int(instansi_id)
    jenis_str = _clean_str(jenis_formasi)
    gaji_min_int = _clean_int(gaji_min)
    gaji_max_int = _clean_int(gaji_max)
    keketatan_str = _clean_str(status_keketatan)

    conditions = []
    params = []
    needs_jurusan_join = False

    if q_str:
        search_term = f"%{q_str}%"
        conditions.append("(f.formasi_id LIKE ? OR f.jabatan_nm LIKE ? OR f.lokasi_nm LIKE ? OR i.nama_instansi LIKE ?)")
        params.extend([search_term, search_term, search_term, search_term])

    if jurusan_id_int:
        needs_jurusan_join = True
        conditions.append("fj.jurusan_id = ?")
        params.append(jurusan_id_int)
    elif jurusan_str:
        needs_jurusan_join = True
        conditions.append("j.nama_jurusan LIKE ?")
        params.append(f"%{jurusan_str.upper()}%")

    if jenjang_str and jenjang_str != "ALL":
        needs_jurusan_join = True
        conditions.append("j.jenjang = ?")
        params.append(jenjang_str)

    if kategori_str and kategori_str != "ALL":
        conditions.append("i.kategori_instansi = ?")
        params.append(kategori_str)

    if instansi_id_int:
        conditions.append("f.instansi_id = ?")
        params.append(instansi_id_int)

    if jenis_str and jenis_str != "ALL":
        conditions.append("f.jenis_formasi = ?")
        params.append(jenis_str)

    if gaji_min_int and gaji_min_int > 0:
        conditions.append("f.gaji_max >= ?")
        params.append(gaji_min_int)

    if gaji_max_int and gaji_max_int > 0:
        conditions.append("f.gaji_min <= ?")
        params.append(gaji_max_int)

    if zero_applicant_only:
        conditions.append("f.jumlah_pelamar = 0")
    elif keketatan_str and keketatan_str != "ALL":
        conditions.append("f.status_keketatan = ?")
        params.append(keketatan_str)

    if max_rasio is not None and max_rasio > 0:
        conditions.append("f.rasio_kompetisi <= ?")
        params.append(max_rasio)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params, needs_jurusan_join


@app.get("/api/formasi")
def get_formasi(
    q: Optional[str] = Query(None, description="Search keyword for position/location/agency"),
    jurusan: Optional[str] = Query(None, description="Search keyword for major name"),
    jurusan_id: Optional[int] = Query(None, description="Exact major ID filter"),
    jenjang: Optional[str] = Query(None, description="Education tier"),
    kategori_instansi: Optional[str] = Query(None, description="Agency category (Pusat/Provinsi/Kabupaten/Kota)"),
    instansi_id: Optional[int] = Query(None, description="Agency ID filter"),
    jenis_formasi: Optional[str] = Query(None, description="Formation type (UMUM/CUMLAUDE/etc)"),
    gaji_min: Optional[int] = Query(None, description="Minimum salary threshold"),
    gaji_max: Optional[int] = Query(None, description="Maximum salary threshold"),
    max_rasio: Optional[float] = Query(None, description="Maximum competition ratio threshold"),
    status_keketatan: Optional[str] = Query(None, description="Competition tier: Tanpa Pelamar, Sangat Longgar, Moderat, Sangat Ketat"),
    zero_applicant_only: bool = Query(False, description="Filter for 0 applicants only"),
    sort_by: str = Query("kuota_desc", description="Sort option: kuota_desc, gaji_max_desc, gaji_min_desc, jabatan_asc, rasio_asc, rasio_desc, pelamar_asc, pelamar_desc"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    Paginated formations list with dynamic filters and server-side LIMIT/OFFSET.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    where_clause, params, needs_jurusan = build_filter_clause(
        q=q,
        jurusan=jurusan,
        jurusan_id=jurusan_id,
        jenjang=jenjang,
        kategori_instansi=kategori_instansi,
        instansi_id=instansi_id,
        jenis_formasi=jenis_formasi,
        gaji_min=gaji_min,
        gaji_max=gaji_max,
        max_rasio=max_rasio,
        status_keketatan=status_keketatan,
        zero_applicant_only=zero_applicant_only
    )

    # 1. Count Total Matching Records
    if needs_jurusan:
        count_sql = f"""
            SELECT COUNT(DISTINCT f.formasi_id)
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            INNER JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
            INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
            {where_clause}
        """
    else:
        count_sql = f"""
            SELECT COUNT(*)
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            {where_clause}
        """

    cur.execute(count_sql, params)
    total_records = cur.fetchone()[0]

    # 2. Sorting
    sort_mappings = {
        "kuota_desc": "f.jumlah_formasi DESC, f.gaji_max DESC",
        "kuota_asc": "f.jumlah_formasi ASC, f.gaji_min ASC",
        "gaji_max_desc": "f.gaji_max DESC, f.jumlah_formasi DESC",
        "gaji_min_desc": "f.gaji_min DESC, f.gaji_max DESC",
        "jabatan_asc": "f.jabatan_nm ASC, i.nama_instansi ASC",
        "rasio_asc": "f.rasio_kompetisi ASC, f.jumlah_formasi DESC",
        "rasio_desc": "f.rasio_kompetisi DESC, f.jumlah_pelamar DESC",
        "pelamar_asc": "f.jumlah_pelamar ASC, f.jumlah_formasi DESC",
        "pelamar_desc": "f.jumlah_pelamar DESC, f.jumlah_formasi DESC",
    }
    order_clause = sort_mappings.get(sort_by, "f.jumlah_formasi DESC, f.gaji_max DESC")

    # 3. Query Paginated IDs
    offset = (page - 1) * limit

    if needs_jurusan:
        paged_sql = f"""
            SELECT f.formasi_id
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            INNER JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
            INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
            {where_clause}
            GROUP BY f.formasi_id
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
    else:
        paged_sql = f"""
            SELECT f.formasi_id
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """

    cur.execute(paged_sql, params + [limit, offset])
    matched_ids = [r[0] for r in cur.fetchall()]

    if not matched_ids:
        conn.close()
        return {
            "items": [],
            "total": total_records,
            "page": page,
            "limit": limit,
            "total_pages": math.ceil(total_records / limit) if limit else 1
        }

    # 4. Fetch Full Formation Details + Majors for the Paged IDs
    placeholders = ",".join(["?"] * len(matched_ids))
    detail_sql = f"""
        SELECT
            f.formasi_id,
            f.instansi_id,
            i.nama_instansi,
            i.kategori_instansi,
            f.jabatan_nm,
            f.lokasi_nm,
            f.jenis_formasi,
            f.jumlah_formasi,
            f.jumlah_pelamar,
            f.rasio_kompetisi,
            f.peluang_lolos_pct,
            f.status_keketatan,
            f.gaji_min,
            f.gaji_max,
            f.golongan_awal,
            f.gaji_pokok_cpns_80,
            f.pendidikan_raw,
            GROUP_CONCAT(j.nama_jurusan, ' || ') as jurusan_concat
        FROM formasi f
        INNER JOIN instansi i ON f.instansi_id = i.instansi_id
        LEFT JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
        LEFT JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
        WHERE f.formasi_id IN ({placeholders})
        GROUP BY f.formasi_id
        ORDER BY {order_clause}
    """
    cur.execute(detail_sql, matched_ids)
    rows = cur.fetchall()

    items = []
    for r in rows:
        concat = r["jurusan_concat"] or ""
        jurusan_list = [j.strip() for j in concat.split(" || ") if j.strip()]
        items.append({
            "formasi_id": r["formasi_id"],
            "instansi_id": r["instansi_id"],
            "nama_instansi": r["nama_instansi"],
            "kategori_instansi": r["kategori_instansi"],
            "jabatan_nm": r["jabatan_nm"],
            "lokasi_nm": r["lokasi_nm"],
            "jenis_formasi": r["jenis_formasi"],
            "jumlah_formasi": r["jumlah_formasi"],
            "jumlah_pelamar": r["jumlah_pelamar"],
            "rasio_kompetisi": r["rasio_kompetisi"],
            "peluang_lolos_pct": r["peluang_lolos_pct"],
            "status_keketatan": r["status_keketatan"],
            "gaji_min": r["gaji_min"],
            "gaji_max": r["gaji_max"],
            "golongan_awal": r["golongan_awal"],
            "gaji_pokok_cpns_80": r["gaji_pokok_cpns_80"],
            "pendidikan_raw": r["pendidikan_raw"],
            "jurusan_list": jurusan_list
        })

    conn.close()

    total_pages = math.ceil(total_records / limit) if limit else 1
    return {
        "items": items,
        "total": total_records,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@app.get("/api/formasi/{formasi_id}")
def get_formasi_detail(formasi_id: str):
    """
    Get comprehensive details for a single formation including agency data and eligible majors.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    query = """
        SELECT
            f.formasi_id,
            f.instansi_id,
            i.nama_instansi,
            i.kategori_instansi,
            i.kode_instansi,
            i.tukin_min,
            i.tukin_max,
            i.regulasi_tukin,
            f.jabatan_nm,
            f.lokasi_nm,
            f.jenis_formasi,
            f.jumlah_formasi,
            f.jumlah_pelamar,
            f.rasio_kompetisi,
            f.peluang_lolos_pct,
            f.status_keketatan,
            f.gaji_min,
            f.gaji_max,
            f.golongan_awal,
            f.gaji_pokok_cpns_80,
            f.pendidikan_raw
        FROM formasi f
        INNER JOIN instansi i ON f.instansi_id = i.instansi_id
        WHERE f.formasi_id = ?
    """
    cur.execute(query, (formasi_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Formasi {formasi_id} not found")

    # Fetch eligible majors
    cur.execute("""
        SELECT j.jurusan_id, j.nama_jurusan, j.jenjang
        FROM formasi_jurusan fj
        INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
        WHERE fj.formasi_id = ?
        ORDER BY j.nama_jurusan ASC
    """, (formasi_id,))
    majors = [
        {"jurusan_id": r["jurusan_id"], "nama_jurusan": r["nama_jurusan"], "jenjang": r["jenjang"]}
        for r in cur.fetchall()
    ]
    conn.close()

    # Calculate 100% full base salary from cpns 80%
    cpns_80 = row["gaji_pokok_cpns_80"] or 0
    full_100 = int(round(cpns_80 / 0.8)) if cpns_80 else 0

    return {
        "formasi_id": row["formasi_id"],
        "instansi_id": row["instansi_id"],
        "nama_instansi": row["nama_instansi"],
        "kategori_instansi": row["kategori_instansi"],
        "kode_instansi": row["kode_instansi"],
        "tukin_min": row["tukin_min"],
        "tukin_max": row["tukin_max"],
        "regulasi_tukin": row["regulasi_tukin"],
        "jabatan_nm": row["jabatan_nm"],
        "lokasi_nm": row["lokasi_nm"],
        "jenis_formasi": row["jenis_formasi"],
        "jumlah_formasi": row["jumlah_formasi"],
        "jumlah_pelamar": row["jumlah_pelamar"],
        "rasio_kompetisi": row["rasio_kompetisi"],
        "peluang_lolos_pct": row["peluang_lolos_pct"],
        "status_keketatan": row["status_keketatan"],
        "gaji_min": row["gaji_min"],
        "gaji_max": row["gaji_max"],
        "golongan_awal": row["golongan_awal"],
        "gaji_pokok_cpns_80": cpns_80,
        "gaji_pokok_100": full_100,
        "pendidikan_raw": row["pendidikan_raw"],
        "majors": majors
    }


@app.get("/api/analytics/top-jurusan")
def get_top_jurusan(
    q: Optional[str] = None,
    jenjang: Optional[str] = None,
    kategori_instansi: Optional[str] = None,
    instansi_id: Optional[int] = None,
    gaji_min: Optional[int] = None,
    gaji_max: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """
    Top demanded majors by total quota seats based on active filters.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    where_clause, params, _ = build_filter_clause(
        q=q,
        jenjang=jenjang,
        kategori_instansi=kategori_instansi,
        instansi_id=instansi_id,
        gaji_min=gaji_min,
        gaji_max=gaji_max
    )

    query = f"""
        SELECT
            j.jurusan_id,
            j.nama_jurusan,
            j.jenjang,
            COUNT(DISTINCT f.formasi_id) as total_formasi,
            SUM(f.jumlah_formasi) as total_kuota,
            ROUND(AVG(f.gaji_max)) as avg_gaji_max
        FROM jurusan j
        INNER JOIN formasi_jurusan fj ON j.jurusan_id = fj.jurusan_id
        INNER JOIN formasi f ON fj.formasi_id = f.formasi_id
        INNER JOIN instansi i ON f.instansi_id = i.instansi_id
        {where_clause}
        GROUP BY j.jurusan_id
        ORDER BY total_kuota DESC, total_formasi DESC
        LIMIT ?
    """
    params.append(limit)
    cur.execute(query, params)

    results = [
        {
            "jurusan_id": r["jurusan_id"],
            "nama_jurusan": r["nama_jurusan"],
            "jenjang": r["jenjang"],
            "total_formasi": r["total_formasi"],
            "total_kuota": r["total_kuota"],
            "avg_gaji_max": int(r["avg_gaji_max"] or 0)
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return results


@app.get("/api/analytics/top-instansi")
def get_top_instansi(
    q: Optional[str] = None,
    jurusan: Optional[str] = None,
    jurusan_id: Optional[int] = None,
    kategori_instansi: Optional[str] = None,
    jenjang: Optional[str] = None,
    gaji_min: Optional[int] = None,
    gaji_max: Optional[int] = None,
    limit: int = Query(10, ge=1, le=100)
):
    """
    Top agencies by quota seats and average compensation based on active filters.
    Uses CTE/distinct subquery to prevent 1-to-many duplication from major relations.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    where_clause, params, needs_jurusan = build_filter_clause(
        q=q,
        jurusan=jurusan,
        jurusan_id=jurusan_id,
        kategori_instansi=kategori_instansi,
        jenjang=jenjang,
        gaji_min=gaji_min,
        gaji_max=gaji_max
    )

    if needs_jurusan:
        query = f"""
            WITH filtered_formasi AS (
                SELECT DISTINCT f.formasi_id, f.instansi_id, f.jumlah_formasi, f.gaji_min, f.gaji_max
                FROM formasi f
                INNER JOIN instansi i ON f.instansi_id = i.instansi_id
                INNER JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
                INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
                {where_clause}
            )
            SELECT
                i.instansi_id,
                i.nama_instansi,
                i.kategori_instansi,
                COUNT(ff.formasi_id) as total_formasi,
                SUM(ff.jumlah_formasi) as total_kuota,
                ROUND(AVG(ff.gaji_min)) as avg_gaji_min,
                ROUND(AVG(ff.gaji_max)) as avg_gaji_max
            FROM instansi i
            INNER JOIN filtered_formasi ff ON i.instansi_id = ff.instansi_id
            GROUP BY i.instansi_id
            ORDER BY total_kuota DESC, total_formasi DESC
            LIMIT ?
        """
    else:
        query = f"""
            SELECT
                i.instansi_id,
                i.nama_instansi,
                i.kategori_instansi,
                COUNT(f.formasi_id) as total_formasi,
                SUM(f.jumlah_formasi) as total_kuota,
                ROUND(AVG(f.gaji_min)) as avg_gaji_min,
                ROUND(AVG(f.gaji_max)) as avg_gaji_max
            FROM instansi i
            INNER JOIN formasi f ON i.instansi_id = f.instansi_id
            {where_clause}
            GROUP BY i.instansi_id
            ORDER BY total_kuota DESC, total_formasi DESC
            LIMIT ?
        """
    params.append(limit)
    cur.execute(query, params)

    results = [
        {
            "instansi_id": r["instansi_id"],
            "nama_instansi": r["nama_instansi"],
            "kategori_instansi": r["kategori_instansi"],
            "total_formasi": r["total_formasi"],
            "total_kuota": r["total_kuota"] or 0,
            "avg_gaji_min": int(r["avg_gaji_min"] or 0),
            "avg_gaji_max": int(r["avg_gaji_max"] or 0),
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return results


@app.get("/api/export")
def export_formasi_csv(
    q: Optional[str] = None,
    jurusan: Optional[str] = None,
    jurusan_id: Optional[int] = None,
    jenjang: Optional[str] = None,
    kategori_instansi: Optional[str] = None,
    instansi_id: Optional[int] = None,
    jenis_formasi: Optional[str] = None,
    gaji_min: Optional[int] = None,
    gaji_max: Optional[int] = None,
    max_rasio: Optional[float] = None,
    status_keketatan: Optional[str] = None,
    zero_applicant_only: bool = False,
    sort_by: str = "kuota_desc"
):
    """
    Stream filtered query results directly as downloadable CSV with competition metrics.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    where_clause, params, needs_jurusan = build_filter_clause(
        q=q,
        jurusan=jurusan,
        jurusan_id=jurusan_id,
        jenjang=jenjang,
        kategori_instansi=kategori_instansi,
        instansi_id=instansi_id,
        jenis_formasi=jenis_formasi,
        gaji_min=gaji_min,
        gaji_max=gaji_max,
        max_rasio=max_rasio,
        status_keketatan=status_keketatan,
        zero_applicant_only=zero_applicant_only
    )

    sort_mappings = {
        "kuota_desc": "f.jumlah_formasi DESC, f.gaji_max DESC",
        "kuota_asc": "f.jumlah_formasi ASC, f.gaji_min ASC",
        "gaji_max_desc": "f.gaji_max DESC, f.jumlah_formasi DESC",
        "gaji_min_desc": "f.gaji_min DESC, f.gaji_max DESC",
        "jabatan_asc": "f.jabatan_nm ASC, i.nama_instansi ASC",
        "rasio_asc": "f.rasio_kompetisi ASC, f.jumlah_formasi DESC",
        "rasio_desc": "f.rasio_kompetisi DESC, f.jumlah_pelamar DESC",
        "pelamar_asc": "f.jumlah_pelamar ASC, f.jumlah_formasi DESC",
        "pelamar_desc": "f.jumlah_pelamar DESC, f.jumlah_formasi DESC",
    }
    order_clause = sort_mappings.get(sort_by, "f.jumlah_formasi DESC, f.gaji_max DESC")

    if needs_jurusan:
        query = f"""
            SELECT
                f.formasi_id,
                i.nama_instansi,
                i.kategori_instansi,
                f.jabatan_nm,
                f.lokasi_nm,
                f.jenis_formasi,
                f.jumlah_formasi,
                f.jumlah_pelamar,
                f.rasio_kompetisi,
                f.peluang_lolos_pct,
                f.status_keketatan,
                f.golongan_awal,
                f.gaji_pokok_cpns_80,
                f.gaji_min,
                f.gaji_max,
                f.pendidikan_raw
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            INNER JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
            INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
            {where_clause}
            GROUP BY f.formasi_id
            ORDER BY {order_clause}
        """
    else:
        query = f"""
            SELECT
                f.formasi_id,
                i.nama_instansi,
                i.kategori_instansi,
                f.jabatan_nm,
                f.lokasi_nm,
                f.jenis_formasi,
                f.jumlah_formasi,
                f.jumlah_pelamar,
                f.rasio_kompetisi,
                f.peluang_lolos_pct,
                f.status_keketatan,
                f.golongan_awal,
                f.gaji_pokok_cpns_80,
                f.gaji_min,
                f.gaji_max,
                f.pendidikan_raw
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            {where_clause}
            ORDER BY {order_clause}
        """

    cur.execute(query, params)

    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "ID Formasi",
            "Instansi",
            "Kategori Instansi",
            "Nama Jabatan",
            "Unit Lokasi Penempatan",
            "Jenis Formasi",
            "Jumlah Formasi (Kuota)",
            "Jumlah Pelamar (MS)",
            "Rasio Kompetisi (1 : X)",
            "Peluang Lolos (%)",
            "Status Keketatan",
            "Golongan Awal",
            "Gaji Pokok CPNS 80% (PP 5/2024)",
            "Penghasilan Min (Rp)",
            "Penghasilan Max (Rp)",
            "Kualifikasi Pendidikan"
        ])
        output.seek(0)
        yield output.read()
        output.truncate(0)
        output.seek(0)

        for row in cur:
            writer.writerow([
                row["formasi_id"],
                row["nama_instansi"],
                row["kategori_instansi"],
                row["jabatan_nm"],
                row["lokasi_nm"],
                row["jenis_formasi"],
                row["jumlah_formasi"],
                row["jumlah_pelamar"],
                f"1 : {row['rasio_kompetisi']}",
                f"{row['peluang_lolos_pct']}%",
                row["status_keketatan"],
                row["golongan_awal"],
                row["gaji_pokok_cpns_80"],
                row["gaji_min"],
                row["gaji_max"],
                row["pendidikan_raw"],
            ])
            output.seek(0)
            yield output.read()
            output.truncate(0)
            output.seek(0)

        conn.close()

    return StreamingResponse(
        iter_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=cpns2024_filtered_export.csv"
        }
    )


# Serve Static Frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not yet built. Please check frontend/index.html"}


@app.get("/sumber-data")
def serve_sumber_data():
    page = FRONTEND_DIR / "sumber-data.html"
    if page.exists():
        return FileResponse(str(page))
    raise HTTPException(status_code=404, detail="Halaman sumber-data.html belum dibuat")


@app.get("/api/download/raw-csv")
def download_raw_csv():
    raw_path = DATA_DIR / "raw_cpns_2024.csv"
    if raw_path.exists():
        return FileResponse(
            str(raw_path),
            media_type="text/csv",
            filename="raw_cpns_2024.csv"
        )
    raise HTTPException(status_code=404, detail="File raw_cpns_2024.csv tidak ditemukan")


@app.get("/api/download/sqlite-db")
def download_sqlite_db():
    db_path = DATA_DIR / "cpns2024.db"
    if db_path.exists():
        return FileResponse(
            str(db_path),
            media_type="application/vnd.sqlite3",
            filename="cpns2024.db"
        )
    raise HTTPException(status_code=404, detail="Database cpns2024.db tidak ditemukan")


@app.get("/api/download/audit-report")
def download_audit_report():
    report_path = DATA_DIR / "laporan_tpp_lengkap.md"
    if report_path.exists():
        return FileResponse(
            str(report_path),
            media_type="text/markdown",
            filename="laporan_tpp_lengkap.md"
        )
    raise HTTPException(status_code=404, detail="Laporan audit belum dibuat")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
