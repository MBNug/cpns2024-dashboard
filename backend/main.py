"""
SSCASN CPNS 2024 - FastAPI Backend
Provides REST API endpoints for stats, filters, paginated formation queries,
analytics, CSV export, and serves the dashboard frontend.
"""

import io
import os
import csv
import math
import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = (
    (BASE_DIR / "data")
    if (BASE_DIR / "data" / "cpns2024.db").exists() or (BASE_DIR / "data" / "cpns2024.db.gz").exists()
    else Path(r"D:\CPNS\Dashboard\data")
)
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
# Compress HTML and JSON responses (>500B) by ~85% over the network (especially on Render)
app.add_middleware(GZipMiddleware, minimum_size=500)


_db_lock = threading.Lock()
_indexes_ensured = False

_cache_lock = threading.Lock()
_stats_cache: Optional[Dict[str, Any]] = None
_filters_cache: Optional[Dict[str, Any]] = None
_summary_cache: "OrderedDict[Tuple[Any, ...], Dict[str, Any]]" = OrderedDict()
_formasi_cache: "OrderedDict[Tuple[Any, ...], Dict[str, Any]]" = OrderedDict()
_MAX_SUMMARY_CACHE = 512
_MAX_FORMASI_CACHE = 256

COMPOSITE_INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_formasi_kuota_gaji ON formasi(jumlah_formasi DESC, gaji_max DESC)",
    "CREATE INDEX IF NOT EXISTS idx_formasi_gaji_max ON formasi(gaji_max DESC, jumlah_formasi DESC)",
    "CREATE INDEX IF NOT EXISTS idx_formasi_jabatan ON formasi(jabatan_nm ASC)",
    "CREATE INDEX IF NOT EXISTS idx_formasi_rasio_kuota ON formasi(rasio_kompetisi ASC, jumlah_formasi DESC)",
    "CREATE INDEX IF NOT EXISTS idx_formasi_pelamar_kuota ON formasi(jumlah_pelamar ASC, jumlah_formasi DESC)",
)


def clear_caches() -> None:
    """Clear in-memory caches for /api/stats, /api/filters, and /api/formasi."""
    global _stats_cache, _filters_cache
    with _cache_lock:
        _stats_cache = None
        _filters_cache = None
        _summary_cache.clear()
        _formasi_cache.clear()


def _ensure_composite_indexes() -> None:
    """Configure WAL mode once and create composite indexes on formasi if the database is writable."""
    global _indexes_ensured
    if _indexes_ensured:
        return
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=15.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        for stmt in COMPOSITE_INDEX_STATEMENTS:
            conn.execute(stmt)
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        if conn is not None:
            conn.close()
    _indexes_ensured = True


def ensure_database_ready():
    """Ensure cpns2024.db is extracted completely and ready for queries without race conditions."""
    if _indexes_ensured and DB_PATH.exists() and DB_PATH.stat().st_size > 10_000_000:
        return

    with _db_lock:
        if not (DB_PATH.exists() and DB_PATH.stat().st_size > 10_000_000):
            gz_path = DATA_DIR / "cpns2024.db.gz"
            raw_csv_path = DATA_DIR / "raw_cpns_2024.csv"
            schema_path = BASE_DIR / "scripts" / "schema.sql"

            if gz_path.exists():
                import gzip, shutil
                tmp_path = DATA_DIR / "cpns2024.db.tmp"
                print(f"[STARTUP] Extracting {gz_path} to {tmp_path} ...")
                with gzip.open(str(gz_path), "rb") as f_in:
                    with open(str(tmp_path), "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                # Atomic swap so no concurrent request can read half-written file
                if tmp_path.exists():
                    os.replace(str(tmp_path), str(DB_PATH))
                print(f"[STARTUP] Database extracted successfully ({DB_PATH.stat().st_size / (1024*1024):.1f} MB).")
            elif raw_csv_path.exists() and schema_path.exists():
                print("[INFO] Building cpns2024.db from raw_cpns_2024.csv via ETL...")
                from scripts.etl_normalize import run_etl
                run_etl(raw_csv_path, DB_PATH, schema_path)
            elif not DB_PATH.exists():
                raise HTTPException(
                    status_code=503,
                    detail="Database cpns2024.db not found. Please ensure data/cpns2024.db.gz exists."
                )

        if DB_PATH.exists():
            _ensure_composite_indexes()


def _prewarm_common_queries() -> None:
    """Background pre-warming of common filter combinations so Render responds in <1ms."""
    try:
        # Pre-warm strategic presets
        get_formasi(jenjang="S-1", zero_applicant_only=True, status_keketatan="Tanpa Pelamar", sort_by="kuota_desc", page=1, limit=10)
        get_formasi(gaji_min=10000000, status_keketatan="Sangat Longgar", sort_by="gaji_max_desc", page=1, limit=10)
        get_formasi(kategori_instansi="Pusat", status_keketatan="Sangat Longgar", sort_by="rasio_asc", page=1, limit=10)
        get_formasi(zero_applicant_only=True, status_keketatan="Tanpa Pelamar", sort_by="kuota_desc", page=1, limit=10)
        # Pre-warm kategori_instansi & status_keketatan
        for kat in ("Pusat", "Provinsi", "Kabupaten/Kota"):
            get_formasi(kategori_instansi=kat, sort_by="kuota_desc", page=1, limit=10)
        for st in ("Tanpa Pelamar", "Sangat Longgar", "Moderat", "Sangat Ketat"):
            get_formasi(status_keketatan=st, sort_by="kuota_desc", page=1, limit=10)
        # Pre-warm jenjang tiers
        for j in ("S-1", "D-III", "D-IV", "SMA/SMK", "S-2", "Profesi", "S-3/Spesialis"):
            get_formasi(jenjang=j, sort_by="kuota_desc", page=1, limit=10)
    except Exception:
        pass


@app.on_event("startup")
def startup_event():
    """Unpack database and pre-warm in-memory caches immediately on startup before requests arrive."""
    ensure_database_ready()
    try:
        _get_stats_data()
        _get_filters_data()
        get_formasi(page=1, limit=10, sort_by="kuota_desc")
        threading.Thread(target=_prewarm_common_queries, daemon=True).start()
    except Exception as exc:
        print(f"[STARTUP] Cache warm warning: {exc}")


def get_db_connection() -> sqlite3.Connection:
    """Create a SQLite connection configured with memory-mapped I/O, RAM page cache, and dict row factory."""
    ensure_database_ready()
    conn = None
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -32000;")
        conn.execute("PRAGMA mmap_size = 268435456;")
        return conn
    except sqlite3.OperationalError:
        if conn is not None:
            conn.close()
        db_uri = DB_PATH.resolve().as_posix()
        conn = sqlite3.connect(f"file:{db_uri}?immutable=1", uri=True, timeout=15.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -32000;")
        conn.execute("PRAGMA mmap_size = 268435456;")
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
    conn = None
    try:
        conn = get_db_connection()
        count = conn.execute("SELECT COUNT(*) FROM formasi").fetchone()[0]
        return {"status": "ok", "database": "connected", "total_formasi": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if conn is not None:
            conn.close()


def _get_stats_data() -> Dict[str, Any]:
    """Compute or return cached summary statistics."""
    global _stats_cache
    if _stats_cache is not None:
        return _stats_cache

    with _cache_lock:
        if _stats_cache is not None:
            return _stats_cache

        conn = None
        try:
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

            result = {
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
            _stats_cache = result
            return result
        finally:
            if conn is not None:
                conn.close()


@app.get("/api/stats")
def get_stats(response: Response):
    """Summary statistics for KPI cards including competition metrics."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    return _get_stats_data()


def _get_filters_data() -> Dict[str, Any]:
    """Compute or return cached dropdown and filter options."""
    global _filters_cache
    if _filters_cache is not None:
        return _filters_cache

    with _cache_lock:
        if _filters_cache is not None:
            return _filters_cache

        conn = None
        try:
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

            result = {
                "jenjang": jenjang_list,
                "kategori_instansi": kategori_instansi,
                "status_keketatan": status_keketatan,
                "jenis_formasi": jenis_formasi,
                "instansi": instansi_list
            }
            _filters_cache = result
            return result
        finally:
            if conn is not None:
                conn.close()


@app.get("/api/filters")
def get_filter_options(response: Response):
    """Options for dropdowns and filter panels."""
    response.headers["Cache-Control"] = "public, max-age=3600"
    return _get_filters_data()


@app.get("/api/filters/jurusan")
def autocomplete_jurusan(
    q: str = Query("", description="Keyword search for major name"),
    jenjang: Optional[str] = Query(None, description="Optional tier filter"),
    limit: int = Query(25, ge=1, le=100)
):
    """Searchable autocomplete endpoint for majors (jurusan)."""
    conn = None
    try:
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
        return [
            {"jurusan_id": r["jurusan_id"], "nama_jurusan": r["nama_jurusan"], "jenjang": r["jenjang"]}
            for r in cur.fetchall()
        ]
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/filters/instansi")
def autocomplete_instansi(
    q: str = Query("", description="Keyword search for agency name"),
    kategori: Optional[str] = Query(None, description="Optional category filter"),
    limit: int = Query(25, ge=1, le=100)
):
    """Searchable autocomplete endpoint for agencies (instansi)."""
    conn = None
    try:
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
        return [
            {
                "instansi_id": r["instansi_id"],
                "kode_instansi": r["kode_instansi"],
                "nama_instansi": r["nama_instansi"],
                "kategori_instansi": r["kategori_instansi"]
            }
            for r in cur.fetchall()
        ]
    finally:
        if conn is not None:
            conn.close()


def _clean_str(val: Any) -> Optional[str]:
    if isinstance(val, str):
        s = val.strip()
        return s if s else None
    return None


def _clean_int(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.strip().isdigit():
        return int(val.strip())
    return None


def _clean_float(val: Any) -> Optional[float]:
    if isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.strip())
        except ValueError:
            return None
    return None


def _clean_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes")
    return False


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
    max_rasio_flt = _clean_float(max_rasio)
    zero_only_bool = _clean_bool(zero_applicant_only)
    keketatan_str = _clean_str(status_keketatan)

    conditions = []
    params = []
    needs_jurusan_join = False

    if q_str:
        for token in q_str.split():
            search_term = f"%{token}%"
            conditions.append("(f.formasi_id LIKE ? OR f.jabatan_nm LIKE ? OR f.lokasi_nm LIKE ? OR i.nama_instansi LIKE ?)")
            params.extend([search_term, search_term, search_term, search_term])

    if jurusan_id_int and (not jenjang_str or jenjang_str == "ALL"):
        needs_jurusan_join = True
        conditions.append("f.formasi_id IN (SELECT fj.formasi_id FROM formasi_jurusan fj WHERE fj.jurusan_id = ?)")
        params.append(jurusan_id_int)
    elif jurusan_id_int or jurusan_str or (jenjang_str and jenjang_str != "ALL"):
        needs_jurusan_join = True
        j_conds = []
        if jurusan_id_int:
            j_conds.append("fj.jurusan_id = ?")
            params.append(jurusan_id_int)
        elif jurusan_str:
            j_conds.append("j.nama_jurusan LIKE ?")
            params.append(f"%{jurusan_str.upper()}%")
        if jenjang_str and jenjang_str != "ALL":
            j_conds.append("j.jenjang = ?")
            params.append(jenjang_str)
        conditions.append(
            f"f.formasi_id IN (SELECT fj.formasi_id FROM formasi_jurusan fj INNER JOIN jurusan j ON fj.jurusan_id = j.jurusan_id WHERE {' AND '.join(j_conds)})"
        )

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

    if zero_only_bool:
        conditions.append("f.jumlah_pelamar = 0")
    elif keketatan_str and keketatan_str != "ALL":
        conditions.append("f.status_keketatan = ?")
        params.append(keketatan_str)

    if max_rasio_flt is not None and max_rasio_flt > 0:
        conditions.append("f.rasio_kompetisi <= ?")
        params.append(max_rasio_flt)

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
    Paginated formations list with dynamic filters, summary aggregates, and server-side LIMIT/OFFSET.
    """
    sort_by = _clean_str(sort_by) or "kuota_desc"
    page = _clean_int(page) or 1
    limit = _clean_int(limit) or 10

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

    params_tuple = tuple(params)
    formasi_cache_key = (where_clause, params_tuple, sort_by, page, limit)
    with _cache_lock:
        cached_resp = _formasi_cache.get(formasi_cache_key)
        if cached_resp is not None:
            _formasi_cache.move_to_end(formasi_cache_key)
            return cached_resp

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Summary Metrics & Total Matching Records (with in-memory LRU cache)
        summary_cache_key = (where_clause, params_tuple)
        summary = None
        if not where_clause:
            stats_data = _get_stats_data()
            summary = {
                "total_formasi": int(stats_data["total_formasi"]),
                "total_kuota": int(stats_data["total_kuota"]),
                "total_pelamar": int(stats_data["total_pelamar"]),
                "avg_rasio_kompetisi": float(stats_data["avg_rasio_kompetisi"]),
                "total_formasi_kosong": int(stats_data["total_formasi_kosong"]),
            }
        else:
            with _cache_lock:
                cached_sum = _summary_cache.get(summary_cache_key)
                if cached_sum is not None:
                    _summary_cache.move_to_end(summary_cache_key)
                    summary = cached_sum

            if summary is None:
                instansi_join_sql = (
                    "INNER JOIN instansi i ON f.instansi_id = i.instansi_id"
                    if "i." in where_clause
                    else ""
                )
                summary_sql = f"""
                    SELECT
                        COUNT(*),
                        COALESCE(SUM(f.jumlah_formasi), 0),
                        COALESCE(SUM(f.jumlah_pelamar), 0),
                        ROUND(COALESCE(AVG(f.rasio_kompetisi), 0), 2),
                        COUNT(CASE WHEN f.jumlah_pelamar = 0 THEN 1 END)
                    FROM formasi f
                    {instansi_join_sql}
                    {where_clause}
                """
                cur.execute(summary_sql, params)
                s_formasi, s_kuota, s_pelamar, s_rasio, s_kosong = cur.fetchone()
                summary = {
                    "total_formasi": int(s_formasi or 0),
                    "total_kuota": int(s_kuota or 0),
                    "total_pelamar": int(s_pelamar or 0),
                    "avg_rasio_kompetisi": float(s_rasio or 0.0),
                    "total_formasi_kosong": int(s_kosong or 0),
                }
                with _cache_lock:
                    _summary_cache[summary_cache_key] = summary
                    if len(_summary_cache) > _MAX_SUMMARY_CACHE:
                        _summary_cache.popitem(last=False)

        total_records = summary["total_formasi"]

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

        # 3. Query Paginated IDs (only join instansi when needed by WHERE or ORDER BY)
        offset = (page - 1) * limit
        paged_instansi_join = (
            "INNER JOIN instansi i ON f.instansi_id = i.instansi_id"
            if ("i." in where_clause or "i." in order_clause)
            else ""
        )
        paged_sql = f"""
            SELECT f.formasi_id
            FROM formasi f
            {paged_instansi_join}
            {where_clause}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """

        cur.execute(paged_sql, params + [limit, offset])
        matched_ids = [r[0] for r in cur.fetchall()]

        total_pages = math.ceil(total_records / limit) if limit else 1
        if not matched_ids:
            empty_result = {
                "items": [],
                "total": total_records,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "summary": summary
            }
            with _cache_lock:
                _formasi_cache[formasi_cache_key] = empty_result
                if len(_formasi_cache) > _MAX_FORMASI_CACHE:
                    _formasi_cache.popitem(last=False)
            return empty_result

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

        result = {
            "items": items,
            "total": total_records,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "summary": summary
        }
        with _cache_lock:
            _formasi_cache[formasi_cache_key] = result
            if len(_formasi_cache) > _MAX_FORMASI_CACHE:
                _formasi_cache.popitem(last=False)
        return result
    finally:
        if conn is not None:
            conn.close()


@app.get("/api/formasi-batch")
def get_formasi_batch(
    ids: str = Query(..., description="Comma-separated formasi_id list, max 20")
):
    """
    Batch lookup for up to 20 formations (used for bookmarks and side-by-side comparison).
    """
    id_list = list(dict.fromkeys(x.strip() for x in ids.split(",") if x.strip()))[:20]
    if not id_list:
        return {"items": []}

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        placeholders = ",".join(["?"] * len(id_list))
        query = f"""
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
                f.pendidikan_raw,
                GROUP_CONCAT(j.nama_jurusan, ' || ') as jurusan_concat
            FROM formasi f
            INNER JOIN instansi i ON f.instansi_id = i.instansi_id
            LEFT JOIN formasi_jurusan fj ON f.formasi_id = fj.formasi_id
            LEFT JOIN jurusan j ON fj.jurusan_id = j.jurusan_id
            WHERE f.formasi_id IN ({placeholders})
            GROUP BY f.formasi_id
        """
        cur.execute(query, id_list)
        rows_by_id = {r["formasi_id"]: r for r in cur.fetchall()}
    finally:
        if conn is not None:
            conn.close()

    items = []
    for fid in id_list:
        r = rows_by_id.get(fid)
        if not r:
            continue
        concat = r["jurusan_concat"] or ""
        jurusan_list = [j.strip() for j in concat.split(" || ") if j.strip()]
        cpns_80 = r["gaji_pokok_cpns_80"] or 0
        full_100 = int(round(cpns_80 / 0.8)) if cpns_80 else 0
        items.append({
            "formasi_id": r["formasi_id"],
            "instansi_id": r["instansi_id"],
            "nama_instansi": r["nama_instansi"],
            "kategori_instansi": r["kategori_instansi"],
            "kode_instansi": r["kode_instansi"],
            "tukin_min": r["tukin_min"],
            "tukin_max": r["tukin_max"],
            "regulasi_tukin": r["regulasi_tukin"],
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
            "gaji_pokok_cpns_80": cpns_80,
            "gaji_pokok_100": full_100,
            "pendidikan_raw": r["pendidikan_raw"],
            "jurusan_list": jurusan_list
        })

    return {"items": items}


@app.get("/api/formasi/{formasi_id}")
def get_formasi_detail(formasi_id: str):
    """
    Get comprehensive details for a single formation including agency data and eligible majors.
    """
    conn = None
    try:
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
                i.link_regulasi,
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
            "link_regulasi": row["link_regulasi"],
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
    finally:
        if conn is not None:
            conn.close()


def _iter_export_csv(
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
    """Build synchronous CSV generator with UTF-8 BOM and guaranteed DB cleanup."""
    sort_by = _clean_str(sort_by) or "kuota_desc"

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

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params)
    except Exception:
        conn.close()
        raise

    def iter_csv():
        try:
            output = io.StringIO()
            output.write("\ufeff")
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
        finally:
            conn.close()

    return iter_csv()


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
    Stream filtered query results directly as downloadable CSV with competition metrics and UTF-8 BOM.
    """
    return StreamingResponse(
        _iter_export_csv(
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
            zero_applicant_only=zero_applicant_only,
            sort_by=sort_by,
        ),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=cpns2024_filtered_export.csv"
        }
    )


# Serve Static Frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.api_route("/", methods=["GET", "HEAD"])
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Frontend not yet built. Please check frontend/index.html"}


@app.get("/favicon.ico")
def serve_favicon():
    svg_path = FRONTEND_DIR / "tako_logo.svg"
    if svg_path.exists():
        return FileResponse(str(svg_path), media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
