"""FastAPI router and read-only SQLite layer for CPNS 2026 verified decrees.

Sources currently ingested:
- Kementerian Keuangan (KepmenPANRB No. 675/2026)
- Badan Siber dan Sandi Negara (Pengumuman No. PENG.102/2026 / KepmenPANRB No. 676/2026)
- Kejaksaan Agung (KepmenPANRB No. 638/2026 — verified partial attachment pages)

Strictly enforces the no-hallucination rule: fields absent from published 2026 decrees
(jumlah_pelamar, rasio_kompetisi, peluang_lolos_pct, status_keketatan, gaji_min, gaji_max,
and jenis_formasi on decrees without pathway breakdown) remain null/empty until official
SSCASN 2026 data is available.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import math
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = (
    (BASE_DIR / "data")
    if (BASE_DIR / "data" / "cpns2026.db").exists() or (BASE_DIR / "data" / "cpns2026.db.gz").exists()
    else Path(r"D:\CPNS\Dashboard\data")
)
DB_PATH = DATA_DIR / "cpns2026.db"
DB_GZ_PATH = DATA_DIR / "cpns2026.db.gz"
RAW_CSV_PATH = DATA_DIR / "raw_cpns_2026.csv"
AUDIT_JSON_PATH = DATA_DIR / "drive_audit_2026.json"

# PP No. 5 Tahun 2024 MKG 0 Gaji Pokok (100%) mapped from education tier strictly for reference THP simulation
GOLONGAN_STATUTORY: list[tuple[str, str, int, str]] = [
    ("SPESIALIS", "III/c", 3026400, "Dokter Subspesialis / S-3 (PP No. 5/2024 Gol. III/c MKG 0)"),
    ("PROFESI", "III/b", 2903600, "Profesi (PP No. 5/2024 Gol. III/b MKG 0)"),
    ("S-2", "III/b", 2903600, "S-2 / Magister (PP No. 5/2024 Gol. III/b MKG 0)"),
    ("D-IV/S-1", "III/a", 2785700, "S-1 / D-IV (PP No. 5/2024 Gol. III/a MKG 0)"),
    ("D-III", "II/c", 2485900, "D-III (PP No. 5/2024 Gol. II/c MKG 0)"),
    ("SMA/SMK", "II/a", 2184000, "SMA / SMK / Sederajat (PP No. 5/2024 Gol. II/a MKG 0)"),
]

router = APIRouter(prefix="/api/2026", tags=["cpns2026"])


def ensure_2026_database_ready() -> None:
    """Decompress data/cpns2026.db.gz if cpns2026.db is not yet extracted (e.g. Render deploy)."""
    if DB_PATH.exists():
        return
    if DB_GZ_PATH.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = DB_PATH.with_suffix(".db.tmp")
        with gzip.open(DB_GZ_PATH, "rb") as f_in, open(tmp_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        tmp_path.replace(DB_PATH)


def _get_conn() -> sqlite3.Connection:
    ensure_2026_database_ready()
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Database CPNS 2026 belum tersedia (cpns2026.db / cpns2026.db.gz tidak ditemukan).",
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _sanitize_csv_cell(val: Any) -> str:
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def _resolve_golongan(jenjang: str) -> dict[str, Any]:
    up = (jenjang or "").upper()
    for key, gol, gapok_100, label in GOLONGAN_STATUTORY:
        if key in up or ("S-1" in up and gol == "III/a"):
            return {
                "golongan_kode": gol,
                "gapok_pp5_100": gapok_100,
                "gapok_cpns_80": int(round(gapok_100 * 0.8)),
                "golongan_label": label,
            }
    return {
        "golongan_kode": "III/a",
        "gapok_pp5_100": 2785700,
        "gapok_cpns_80": int(round(2785700 * 0.8)),
        "golongan_label": "Acuan Regulasi PP No. 5/2024",
    }


def _build_filter_clause(
    q: str = "",
    instansi: str = "",
    eselon1: str = "",
    kategori: str = "",
    jenjang: str = "",
    jurusan: str = "",
    jabatan: str = "",
    lokasi: str = "",
    jenis_formasi: str = "",
    keketatan: str = "",
    min_kuota: Optional[int] = None,
    only_zero_pelamar: bool = False,
) -> tuple[str, list[Any]]:
    clauses: list[str] = ["1=1"]
    params: list[Any] = []

    q_clean = (q or "").strip()
    if q_clean:
        like = f"%{q_clean}%"
        clauses.append(
            "(f.jabatan_nm LIKE ? OR f.lokasi_nm LIKE ? OR f.pendidikan_nm LIKE ? "
            "OR f.unit_eselon1 LIKE ? OR i.instansi_nm LIKE ?)"
        )
        params.extend([like, like, like, like, like])

    if (instansi or "").strip():
        clauses.append("i.instansi_nm LIKE ?")
        params.append(f"%{instansi.strip()}%")

    if (eselon1 or "").strip():
        clauses.append("f.unit_eselon1 = ?")
        params.append(eselon1.strip())

    if (kategori or "").strip():
        clauses.append("i.kategori_instansi = ?")
        params.append(kategori.strip())

    if (jenjang or "").strip():
        clauses.append("f.jenjang = ?")
        params.append(jenjang.strip())

    if (jabatan or "").strip():
        clauses.append("f.jabatan_nm = ?")
        params.append(jabatan.strip())

    if (lokasi or "").strip():
        clauses.append("f.lokasi_nm LIKE ?")
        params.append(f"%{lokasi.strip()}%")

    if (jenis_formasi or "").strip():
        clauses.append("f.jenis_formasi = ?")
        params.append(jenis_formasi.strip())

    if (keketatan or "").strip():
        clauses.append("f.status_keketatan = ?")
        params.append(keketatan.strip())

    if min_kuota is not None and min_kuota > 0:
        clauses.append("f.jumlah_formasi >= ?")
        params.append(min_kuota)

    if only_zero_pelamar:
        clauses.append("f.jumlah_pelamar = 0")

    if (jurusan or "").strip():
        j_list = [x.strip() for x in jurusan.split(",") if x.strip()]
        if len(j_list) == 1:
            clauses.append(
                "EXISTS (SELECT 1 FROM formasi_jurusan fj "
                "JOIN jurusan j ON j.jurusan_id = fj.jurusan_id "
                "WHERE fj.formasi_id = f.formasi_id AND UPPER(j.jurusan_nm) LIKE ?)"
            )
            params.append(f"%{j_list[0].upper()}%")
        elif j_list:
            sub_conds = " OR ".join(["UPPER(j.jurusan_nm) LIKE ?" for _ in j_list])
            clauses.append(
                f"EXISTS (SELECT 1 FROM formasi_jurusan fj "
                f"JOIN jurusan j ON j.jurusan_id = fj.jurusan_id "
                f"WHERE fj.formasi_id = f.formasi_id AND ({sub_conds}))"
            )
            params.extend([f"%{item.upper()}%" for item in j_list])

    return " AND ".join(clauses), params


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["jurusan_list"] = [m.strip() for m in (d.get("pendidikan_nm") or "").split(" | ") if m.strip()]
    d.update(_resolve_golongan(d.get("jenjang", "")))
    return d


@router.get("/stats")
def get_stats_2026() -> dict[str, Any]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        row = cur.execute(
            """
            SELECT
                COUNT(*) AS total_formasi_rows,
                COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                SUM(CASE WHEN f.jumlah_pelamar IS NOT NULL THEN f.jumlah_pelamar ELSE 0 END) AS sum_pelamar,
                COUNT(f.jumlah_pelamar) AS has_pelamar_cnt,
                COUNT(CASE WHEN f.jumlah_pelamar = 0 THEN 1 END) AS zero_pelamar_cnt,
                AVG(CASE WHEN f.jumlah_pelamar IS NOT NULL THEN f.rasio_kompetisi END) AS avg_rasio,
                COUNT(CASE WHEN f.gaji_min > 0 THEN 1 END) AS has_salary_cnt,
                COUNT(CASE WHEN f.jenis_formasi IS NOT NULL AND f.jenis_formasi != '' THEN 1 END) AS has_jenis_cnt,
                SUM(CASE WHEN i.kategori_instansi = 'Pusat' THEN 1 ELSE 0 END) AS pusat_rows,
                SUM(CASE WHEN i.kategori_instansi = 'Daerah' THEN 1 ELSE 0 END) AS daerah_rows,
                COUNT(DISTINCT f.jabatan_nm) AS distinct_jabatan,
                COUNT(DISTINCT f.unit_eselon1) AS distinct_eselon1,
                COUNT(DISTINCT f.instansi_id) AS distinct_instansi
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            """
        ).fetchone()

        has_applicants = (row["has_pelamar_cnt"] or 0) > 0
        has_salary = (row["has_salary_cnt"] or 0) > 0
        has_jenis = (row["has_jenis_cnt"] or 0) > 0

        med_min = None
        med_max = None
        if has_salary:
            vals = [
                (r[0], r[1])
                for r in cur.execute(
                    "SELECT gaji_min, gaji_max FROM formasi WHERE gaji_min > 0 ORDER BY gaji_min"
                ).fetchall()
            ]
            if vals:
                mid = vals[len(vals) // 2]
                med_min, med_max = mid[0], mid[1]

        instansi_summary = [
            dict(r)
            for r in cur.execute(
                """
                SELECT
                    i.instansi_id,
                    i.instansi_nm,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM instansi i
                JOIN formasi f ON f.instansi_id = i.instansi_id
                GROUP BY i.instansi_id, i.instansi_nm
                ORDER BY total_kuota DESC, i.instansi_nm ASC
                """
            ).fetchall()
        ]
        drive_audit = (
            json.loads(AUDIT_JSON_PATH.read_text(encoding="utf-8"))
            if AUDIT_JSON_PATH.exists()
            else []
        )

        return {
            "total_formasi_rows": row["total_formasi_rows"],
            "total_kuota": row["total_kuota"],
            "total_pelamar": row["sum_pelamar"] if has_applicants else None,
            "total_formasi_kosong": row["zero_pelamar_cnt"] if has_applicants else None,
            "avg_rasio": round(row["avg_rasio"], 2) if has_applicants and row["avg_rasio"] is not None else None,
            "median_gaji_min": med_min,
            "median_gaji_max": med_max,
            "pusat_rows": row["pusat_rows"] or 0,
            "daerah_rows": row["daerah_rows"] or 0,
            "distinct_jabatan": row["distinct_jabatan"] or 0,
            "distinct_eselon1": row["distinct_eselon1"] or 0,
            "distinct_instansi": row["distinct_instansi"] or 0,
            "has_applicant_data": has_applicants,
            "has_salary_data": has_salary,
            "has_jenis_formasi": has_jenis,
            "instansi_summary": instansi_summary,
            "drive_audit": drive_audit,
            "sumber_dokumen": "SSCASN Live (BPK) • KepmenPANRB 675 (Kemenkeu), 676 (BSSN), 638 Parsial (Kejagung) • SE Kemenkes HK.02.02 (Syarat STR)",
        }
    finally:
        conn.close()


@router.get("/filters")
def get_filters_2026() -> dict[str, Any]:
    conn = _get_conn()
    try:
        cur = conn.cursor()
        kategori = [
            r[0]
            for r in cur.execute("SELECT DISTINCT kategori_instansi FROM instansi ORDER BY kategori_instansi").fetchall()
        ]
        instansi_summary = [
            dict(r)
            for r in cur.execute(
                """
                SELECT
                    i.instansi_id,
                    i.instansi_nm,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                    COUNT(f.jumlah_formasi) AS known_kuota_cnt
                FROM instansi i
                JOIN formasi f ON f.instansi_id = i.instansi_id
                GROUP BY i.instansi_id, i.instansi_nm
                ORDER BY total_kuota DESC, formasi_count DESC, i.instansi_nm ASC
                """
            ).fetchall()
        ]
        instansi = [x["instansi_nm"] for x in instansi_summary]
        unit_eselon1 = [
            {
                "unit_eselon1": r[0],
                "formasi_count": r[1],
                "total_kuota": r[2],
                "instansi_nm": r[3],
                "known_kuota_cnt": r[4],
            }
            for r in cur.execute(
                """
                SELECT f.unit_eselon1, COUNT(*) AS cnt, COALESCE(SUM(f.jumlah_formasi), 0) AS kuota, i.instansi_nm, COUNT(f.jumlah_formasi) AS known_kuota_cnt
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                GROUP BY f.unit_eselon1, i.instansi_nm
                ORDER BY kuota DESC, cnt DESC, f.unit_eselon1 ASC
                """
            ).fetchall()
        ]
        jenjang = [
            r[0]
            for r in cur.execute("SELECT DISTINCT jenjang FROM formasi ORDER BY jenjang").fetchall()
        ]
        jabatan = [
            {"jabatan_nm": r[0], "formasi_count": r[1], "total_kuota": r[2], "known_kuota_cnt": r[3]}
            for r in cur.execute(
                """
                SELECT jabatan_nm, COUNT(*) AS cnt, COALESCE(SUM(jumlah_formasi), 0) AS kuota, COUNT(jumlah_formasi) AS known_kuota_cnt
                FROM formasi
                GROUP BY jabatan_nm
                ORDER BY kuota DESC, cnt DESC, jabatan_nm ASC
                """
            ).fetchall()
        ]
        jenis_formasi = [
            r[0]
            for r in cur.execute(
                "SELECT DISTINCT jenis_formasi FROM formasi WHERE jenis_formasi IS NOT NULL AND jenis_formasi != '' ORDER BY jenis_formasi"
            ).fetchall()
        ]
        status_keketatan = [
            r[0]
            for r in cur.execute(
                "SELECT DISTINCT status_keketatan FROM formasi WHERE status_keketatan IS NOT NULL ORDER BY status_keketatan"
            ).fetchall()
        ]
        flags = cur.execute(
            """
            SELECT
                COUNT(jumlah_pelamar) AS has_p,
                COUNT(CASE WHEN gaji_min > 0 THEN 1 END) AS has_g,
                COUNT(CASE WHEN jenis_formasi IS NOT NULL AND jenis_formasi != '' THEN 1 END) AS has_j
            FROM formasi
            """
        ).fetchone()

        return {
            "kategori": kategori,
            "instansi": instansi,
            "instansi_summary": instansi_summary,
            "unit_eselon1": unit_eselon1,
            "jenjang": jenjang,
            "jabatan": jabatan,
            "jenis_formasi": jenis_formasi,
            "status_keketatan": status_keketatan,
            "has_applicant_data": (flags["has_p"] or 0) > 0,
            "has_salary_data": (flags["has_g"] or 0) > 0,
            "has_jenis_formasi": (flags["has_j"] or 0) > 0,
        }
    finally:
        conn.close()


@router.get("/filters/jurusan")
def search_jurusan_2026(
    q: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        q_clean = (q or "").strip()
        like = f"%{q_clean}%"
        rows = conn.execute(
            """
            SELECT j.jurusan_nm, COUNT(DISTINCT fj.formasi_id) AS formasi_count, COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
            FROM jurusan j
            JOIN formasi_jurusan fj ON fj.jurusan_id = j.jurusan_id
            JOIN formasi f ON f.formasi_id = fj.formasi_id
            WHERE j.jurusan_nm LIKE ?
            GROUP BY j.jurusan_id, j.jurusan_nm
            ORDER BY total_kuota DESC, j.jurusan_nm ASC
            LIMIT ?
            """,
            (like, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/filters/instansi")
def search_instansi_2026(
    q: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    conn = _get_conn()
    try:
        q_clean = (q or "").strip()
        like = f"%{q_clean}%"
        rows = conn.execute(
            """
            SELECT i.instansi_nm, i.kategori_instansi, COUNT(*) AS formasi_count, COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
            FROM instansi i
            JOIN formasi f ON f.instansi_id = i.instansi_id
            WHERE i.instansi_nm LIKE ?
            GROUP BY i.instansi_id, i.instansi_nm, i.kategori_instansi
            ORDER BY total_kuota DESC, i.instansi_nm ASC
            LIMIT ?
            """,
            (like, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/formasi")
def list_formasi_2026(
    q: str = Query(default=""),
    instansi: str = Query(default=""),
    eselon1: str = Query(default=""),
    kategori: str = Query(default=""),
    jenjang: str = Query(default=""),
    jurusan: str = Query(default=""),
    jabatan: str = Query(default=""),
    lokasi: str = Query(default=""),
    jenis_formasi: str = Query(default=""),
    keketatan: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
    sort_by: str = Query(default="no_urut"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    default_order = "CASE f.instansi_id WHEN 'KEMENKEU' THEN 1 WHEN 'BPK' THEN 2 WHEN 'BSSN' THEN 3 WHEN 'KEJAGUNG' THEN 4 WHEN 'KEMENKES' THEN 5 ELSE 9 END ASC, f.no_urut ASC, f.formasi_id ASC"
    sort_map = {
        "no_urut": default_order,
        "kuota_desc": "f.jumlah_formasi DESC, " + default_order,
        "kuota_asc": "f.jumlah_formasi ASC, " + default_order,
        "jabatan_asc": "f.jabatan_nm ASC, f.jumlah_formasi DESC, " + default_order,
        "eselon1_asc": "f.unit_eselon1 ASC, f.jumlah_formasi DESC, " + default_order,
        "rasio_asc": "CASE WHEN f.rasio_kompetisi IS NULL THEN 1 ELSE 0 END ASC, f.rasio_kompetisi ASC, f.jumlah_formasi DESC",
        "peluang_desc": "CASE WHEN f.peluang_lolos_pct IS NULL THEN 1 ELSE 0 END ASC, f.peluang_lolos_pct DESC, f.jumlah_formasi DESC",
        "gaji_desc": "CASE WHEN f.gaji_max IS NULL THEN 1 ELSE 0 END ASC, f.gaji_max DESC, f.jumlah_formasi DESC",
    }
    order_sql = sort_map.get(sort_by, sort_map["no_urut"])

    where_sql, params = _build_filter_clause(
        q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
        jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
        keketatan=keketatan, min_kuota=min_kuota, only_zero_pelamar=only_zero_pelamar,
    )

    conn = _get_conn()
    try:
        agg = conn.execute(
            f"""
            SELECT COUNT(*) AS cnt, COALESCE(SUM(f.jumlah_formasi), 0) AS kuota_sum
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE {where_sql}
            """,
            params,
        ).fetchone()
        total = agg["cnt"] or 0
        total_kuota_filtered = agg["kuota_sum"] or 0
        total_pages = max(1, math.ceil(total / limit))
        offset = (page - 1) * limit

        rows = conn.execute(
            f"""
            SELECT
                f.*,
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

        return {
            "total": total,
            "total_kuota_filtered": total_kuota_filtered,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "items": [_row_to_dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/formasi-batch")
def get_formasi_batch_2026(ids: str = Query(default="")) -> list[dict[str, Any]]:
    id_list = [x.strip() for x in ids.split(",") if x.strip()][:8]
    if not id_list:
        return []
    placeholders = ",".join("?" for _ in id_list)
    conn = _get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT
                f.*,
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE f.formasi_id IN ({placeholders})
            ORDER BY CASE f.instansi_id WHEN 'KEMENKEU' THEN 1 WHEN 'BPK' THEN 2 WHEN 'BSSN' THEN 3 WHEN 'KEJAGUNG' THEN 4 WHEN 'KEMENKES' THEN 5 ELSE 9 END ASC, f.no_urut ASC, f.formasi_id ASC
            """,
            id_list,
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/formasi/{formasi_id}")
def get_formasi_detail_2026(formasi_id: str) -> dict[str, Any]:
    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT
                f.*,
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE f.formasi_id = ?
            """,
            (formasi_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Formasi {formasi_id} tidak ditemukan.")
        return _row_to_dict(row)
    finally:
        conn.close()


@router.get("/analytics/top")
def get_top_analytics_2026(
    q: str = Query(default=""),
    instansi: str = Query(default=""),
    eselon1: str = Query(default=""),
    kategori: str = Query(default=""),
    jenjang: str = Query(default=""),
    jurusan: str = Query(default=""),
    jabatan: str = Query(default=""),
    lokasi: str = Query(default=""),
    jenis_formasi: str = Query(default=""),
    keketatan: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
) -> dict[str, Any]:
    where_sql, params = _build_filter_clause(
        q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
        jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
        keketatan=keketatan, min_kuota=min_kuota, only_zero_pelamar=only_zero_pelamar,
    )
    conn = _get_conn()
    try:
        cur = conn.cursor()
        agg = cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                COUNT(f.jumlah_pelamar) AS has_p
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE {where_sql}
            """,
            params,
        ).fetchone()
        has_applicants = (agg["has_p"] or 0) > 0

        top_jurusan = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    j.jurusan_nm,
                    COUNT(DISTINCT f.formasi_id) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                    CASE WHEN COUNT(f.jumlah_pelamar) > 0 THEN SUM(f.jumlah_pelamar) ELSE NULL END AS total_pelamar
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                JOIN formasi_jurusan fj ON fj.formasi_id = f.formasi_id
                JOIN jurusan j ON j.jurusan_id = fj.jurusan_id
                WHERE {where_sql}
                GROUP BY j.jurusan_id, j.jurusan_nm
                ORDER BY total_kuota DESC, formasi_count DESC, j.jurusan_nm ASC
                LIMIT 10
                """,
                params,
            ).fetchall()
        ]

        top_jabatan = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    f.jabatan_nm,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                WHERE {where_sql}
                GROUP BY f.jabatan_nm
                ORDER BY total_kuota DESC, formasi_count DESC
                LIMIT 10
                """,
                params,
            ).fetchall()
        ]

        top_eselon1 = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    f.unit_eselon1,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                WHERE {where_sql}
                GROUP BY f.unit_eselon1
                ORDER BY total_kuota DESC, formasi_count DESC
                LIMIT 13
                """,
                params,
            ).fetchall()
        ]

        jenjang_dist = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    f.jenjang,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                WHERE {where_sql}
                GROUP BY f.jenjang
                ORDER BY total_kuota DESC
                """,
                params,
            ).fetchall()
        ]

        keketatan_dist: list[dict[str, Any]] = []
        if has_applicants:
            keketatan_dist = [
                dict(r)
                for r in cur.execute(
                    f"""
                    SELECT
                        f.status_keketatan,
                        COUNT(*) AS formasi_count,
                        COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                    FROM formasi f
                    JOIN instansi i ON i.instansi_id = f.instansi_id
                    WHERE {where_sql} AND f.status_keketatan IS NOT NULL
                    GROUP BY f.status_keketatan
                    ORDER BY total_kuota DESC
                    """,
                    params,
                ).fetchall()
            ]

        kategori_dist = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    i.kategori_instansi,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                WHERE {where_sql}
                GROUP BY i.kategori_instansi
                ORDER BY total_kuota DESC
                """,
                params,
            ).fetchall()
        ]

        instansi_dist = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    i.instansi_nm,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                WHERE {where_sql}
                GROUP BY i.instansi_id, i.instansi_nm
                ORDER BY total_kuota DESC, i.instansi_nm ASC
                """,
                params,
            ).fetchall()
        ]

        return {
            "total_rows": agg["total_rows"] or 0,
            "total_kuota": agg["total_kuota"] or 0,
            "has_applicant_data": has_applicants,
            "top_jurusan": top_jurusan,
            "top_jabatan": top_jabatan,
            "top_eselon1": top_eselon1,
            "jenjang_dist": jenjang_dist,
            "keketatan_dist": keketatan_dist,
            "kategori_dist": kategori_dist,
            "instansi_dist": instansi_dist,
        }
    finally:
        conn.close()


@router.get("/export")
def export_csv_2026(
    q: str = Query(default=""),
    instansi: str = Query(default=""),
    eselon1: str = Query(default=""),
    kategori: str = Query(default=""),
    jenjang: str = Query(default=""),
    jurusan: str = Query(default=""),
    jabatan: str = Query(default=""),
    lokasi: str = Query(default=""),
    jenis_formasi: str = Query(default=""),
    keketatan: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
):
    where_sql, params = _build_filter_clause(
        q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
        jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
        keketatan=keketatan, min_kuota=min_kuota, only_zero_pelamar=only_zero_pelamar,
    )
    conn = _get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT
                f.no_urut,
                f.formasi_id,
                i.instansi_nm,
                i.kategori_instansi,
                f.unit_eselon1,
                f.jabatan_nm,
                f.lokasi_nm,
                f.pendidikan_nm,
                f.jenjang,
                f.jumlah_formasi,
                f.jenis_formasi,
                f.jumlah_pelamar,
                f.rasio_kompetisi,
                f.status_keketatan,
                f.gaji_min,
                f.gaji_max,
                f.sumber_dokumen
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            WHERE {where_sql}
            ORDER BY CASE f.instansi_id WHEN 'KEMENKEU' THEN 1 WHEN 'BPK' THEN 2 WHEN 'BSSN' THEN 3 WHEN 'KEJAGUNG' THEN 4 WHEN 'KEMENKES' THEN 5 ELSE 9 END ASC, f.no_urut ASC, f.formasi_id ASC
            """,
            params,
        ).fetchall()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "No", "Formasi ID", "Instansi", "Kategori", "Unit Eselon I",
            "Jabatan", "Unit Penempatan", "Kualifikasi Pendidikan", "Jenjang",
            "Alokasi CPNS", "Jenis Formasi", "Jumlah Pelamar", "Rasio Kompetisi",
            "Status Keketatan", "Gaji Min", "Gaji Max", "Sumber Dokumen",
        ])
        for r in rows:
            writer.writerow([_sanitize_csv_cell(r[k]) for k in r.keys()])

        csv_bytes = ("\ufeff" + buf.getvalue()).encode("utf-8")
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="cpns2026_filtered.csv"'},
        )
    finally:
        conn.close()


@router.get("/download/raw-csv")
def download_raw_csv_2026():
    if RAW_CSV_PATH.exists():
        return FileResponse(str(RAW_CSV_PATH), media_type="text/csv", filename="raw_cpns_2026.csv")
    raise HTTPException(status_code=404, detail="File raw_cpns_2026.csv tidak ditemukan")


@router.get("/download/sqlite-db")
def download_sqlite_db_2026():
    ensure_2026_database_ready()
    if DB_PATH.exists():
        return FileResponse(str(DB_PATH), media_type="application/vnd.sqlite3", filename="cpns2026.db")
    raise HTTPException(status_code=404, detail="Database cpns2026.db tidak ditemukan")
