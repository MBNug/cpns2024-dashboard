"""FastAPI router and read-only SQLite layer for CPNS 2026 verified decrees & live SSCASN data.

Sources currently ingested (14 agencies):
- SSCASN BKN Live (12 agencies): Kemenhut, MA RI, KKP, BPKP, Kejaksaan Agung, BGN, Kemenkum, Kemenham, Kemenkop, BPK, Polri, BSSN
- Official PDF (1 agency): Kementerian Keuangan (KepmenPANRB 675/2026)
- Official SE STR (1 agency): Kementerian Kesehatan (SE HK.02.02/F/4023/2026, quota NULL)

Strictly enforces the no-hallucination rule: fields absent from published 2026 decrees
(jumlah_pelamar, rasio_kompetisi, peluang_lolos_pct, status_keketatan, gaji_min, gaji_max,
and jenis_formasi on decrees without pathway breakdown) remain null/empty until official
SSCASN 2026 data is available.
"""

from __future__ import annotations

from collections import OrderedDict
import csv
import gzip
import io
import json
import math
import os
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Response
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
_db_2026_lock = threading.Lock()
_cache_2026_lock = threading.Lock()
_cache_2026_sig: Optional[tuple[Optional[tuple[int, int]], Optional[tuple[int, int]]]] = None
_stats_cache_2026: Optional[dict[str, Any]] = None
_filters_cache_2026: Optional[dict[str, Any]] = None
_list_cache_2026: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
_jurusan_cache_2026: "OrderedDict[tuple[Any, ...], list[dict[str, Any]]]" = OrderedDict()
_instansi_cache_2026: "OrderedDict[tuple[Any, ...], list[dict[str, Any]]]" = OrderedDict()
_batch_cache_2026: "OrderedDict[tuple[str, ...], list[dict[str, Any]]]" = OrderedDict()
_detail_cache_2026: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_analytics_cache_2026: "OrderedDict[tuple[Any, ...], dict[str, Any]]" = OrderedDict()
_MAX_LIST_CACHE_2026 = 128
_MAX_JURUSAN_CACHE_2026 = 128
_MAX_INSTANSI_CACHE_2026 = 64
_MAX_BATCH_CACHE_2026 = 64
_MAX_DETAIL_CACHE_2026 = 256
_MAX_ANALYTICS_CACHE_2026 = 64
_CDN_CACHE_HEADER = "public, max-age=120, s-maxage=3600, stale-while-revalidate=86400"

_FORMASI_LIST_COLS = (
    "f.formasi_id, f.no_urut, f.instansi_id, f.unit_eselon1, f.jabatan_nm, f.lokasi_nm, "
    "f.jenis_formasi, f.jumlah_formasi, f.jumlah_pelamar, f.rasio_kompetisi, "
    "f.peluang_lolos_pct, f.status_keketatan, f.gaji_min, f.gaji_max, "
    "f.usia_min, f.usia_max, f.pendidikan_nm, f.jenjang, f.sumber_dokumen"
)


def _file_sig(path: Path) -> Optional[tuple[int, int]]:
    try:
        st = path.stat()
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def _sync_2026_cache_version() -> None:
    """Clear read-only 2026 caches automatically whenever cpns2026.db or drive_audit changes on disk."""
    global _cache_2026_sig, _stats_cache_2026, _filters_cache_2026
    sig = (_file_sig(DB_PATH), _file_sig(AUDIT_JSON_PATH))
    if sig == _cache_2026_sig:
        return
    with _cache_2026_lock:
        if sig == _cache_2026_sig:
            return
        _cache_2026_sig = sig
        _stats_cache_2026 = None
        _filters_cache_2026 = None
        _list_cache_2026.clear()
        _jurusan_cache_2026.clear()
        _instansi_cache_2026.clear()
        _batch_cache_2026.clear()
        _detail_cache_2026.clear()
        _analytics_cache_2026.clear()


def _lru_get(cache: OrderedDict, key: Any) -> Any:
    with _cache_2026_lock:
        val = cache.get(key)
        if val is not None:
            cache.move_to_end(key)
        return val


def _lru_set(cache: OrderedDict, key: Any, value: Any, max_size: int) -> None:
    with _cache_2026_lock:
        cache[key] = value
        cache.move_to_end(key)
        while len(cache) > max_size:
            cache.popitem(last=False)


def _needs_2026_extract() -> bool:
    if not DB_GZ_PATH.exists():
        return False
    if not DB_PATH.exists():
        return True
    try:
        db_st = DB_PATH.stat()
        gz_st = DB_GZ_PATH.stat()
        if db_st.st_size == 0:
            return True
        if gz_st.st_mtime > db_st.st_mtime + 1.0:
            return True
    except OSError:
        return True
    return False


def ensure_2026_database_ready() -> None:
    """Thread-safe decompression of data/cpns2026.db.gz when missing, empty, or newer than cpns2026.db."""
    if not _needs_2026_extract():
        return
    with _db_2026_lock:
        if not _needs_2026_extract():
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path = DATA_DIR / f"{DB_PATH.name}.{os.getpid()}.{threading.get_ident()}.tmp"
        try:
            with gzip.open(DB_GZ_PATH, "rb") as f_in, open(tmp_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            tmp_path.replace(DB_PATH)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
    _sync_2026_cache_version()


def _get_conn() -> sqlite3.Connection:
    ensure_2026_database_ready()
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Database CPNS 2026 belum tersedia (cpns2026.db / cpns2026.db.gz tidak ditemukan).",
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -4000;")
    return conn


def warm_2026_caches() -> None:
    """Pre-warm lightweight CPNS 2026 default caches at startup to avoid Render cold-boot stampedes."""
    ensure_2026_database_ready()
    if DB_PATH.exists():
        get_stats_2026(Response())
        get_filters_2026(Response())
        search_jurusan_2026(Response(), q="", limit=25)
        list_formasi_2026(
            Response(), q="", instansi="", eselon1="", kategori="", jenjang="",
            jurusan="", jabatan="", lokasi="", jenis_formasi="", keketatan="",
            keketatan_2024="", min_kuota=None, only_zero_pelamar=False,
            sort_by="no_urut", page=1, limit=20,
        )
        get_top_analytics_2026(
            Response(), q="", instansi="", eselon1="", kategori="", jenjang="",
            jurusan="", jabatan="", lokasi="", jenis_formasi="", keketatan="",
            keketatan_2024="", min_kuota=None, only_zero_pelamar=False,
        )


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
    keketatan_2024: str = "",
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
        clauses.append(
            "f.instansi_id IN (SELECT instansi_id FROM instansi WHERE instansi_nm LIKE ?)"
        )
        params.append(f"%{instansi.strip()}%")

    if (eselon1 or "").strip():
        clauses.append("f.unit_eselon1 = ?")
        params.append(eselon1.strip())

    if (kategori or "").strip():
        clauses.append("i.kategori_instansi = ?")
        params.append(kategori.strip())

    if (jenjang or "").strip():
        clauses.append("(' / ' || f.jenjang || ' / ') LIKE ?")
        params.append(f"% / {jenjang.strip()} / %")

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

    if (keketatan_2024 or "").strip():
        k24 = keketatan_2024.strip()
        if k24 == "__NONE__":
            clauses.append("b.status_keketatan_2024 IS NULL")
        else:
            clauses.append("b.status_keketatan_2024 = ?")
            params.append(k24)

    if min_kuota is not None and min_kuota > 0:
        clauses.append("f.jumlah_formasi >= ?")
        params.append(min_kuota)

    if only_zero_pelamar:
        clauses.append("f.jumlah_pelamar = 0")

    if (jurusan or "").strip():
        j_list = [x.strip() for x in jurusan.split(",") if x.strip()]
        if len(j_list) == 1:
            clauses.append(
                "f.formasi_id IN (SELECT fj.formasi_id FROM jurusan j "
                "CROSS JOIN formasi_jurusan fj ON fj.jurusan_id = j.jurusan_id "
                "WHERE UPPER(j.jurusan_nm) LIKE ?)"
            )
            params.append(f"%{j_list[0].upper()}%")
        elif j_list:
            sub_conds = " OR ".join(["UPPER(j.jurusan_nm) LIKE ?" for _ in j_list])
            clauses.append(
                f"f.formasi_id IN (SELECT fj.formasi_id FROM jurusan j "
                f"CROSS JOIN formasi_jurusan fj ON fj.jurusan_id = j.jurusan_id "
                f"WHERE {sub_conds})"
            )
            params.extend([f"%{item.upper()}%" for item in j_list])

    return " AND ".join(clauses), params


_BANDING_2024_SQL = """
                b.match_level_2024,
                COALESCE(b.match_label_2024, 'Tidak ada pembanding di 2024') AS match_label_2024,
                b.kursi_2024,
                b.pelamar_2024,
                b.rasio_2024,
                b.peluang_2024_pct,
                b.status_keketatan_2024,
                COALESCE(b.row_count_2024, 0) AS row_count_2024,
                b.n_peserta_skb_2024,
                b.n_lulus_2024,
                b.nilai_akhir_2024_min,
                b.nilai_akhir_2024_median,
                b.nilai_akhir_2024_max,
                b.skd_2024_lulus_min,
                b.skd_2024_lulus_median,
                b.skd_2024_lulus_max,
                b.skd_2024_skb_min,
                b.skb_2024_lulus_min,
                b.skb_2024_lulus_median,
                b.skb_2024_lulus_max,
                b.sumber_nilai_2024
"""


def _build_persyaratan_daftar(row_dict: dict[str, Any]) -> dict[str, Any]:
    raw_inst = row_dict.pop("pers_ringkasan_json", None)
    inst_data: dict[str, Any] = {}
    if raw_inst:
        try:
            inst_data = json.loads(raw_inst)
        except Exception:
            inst_data = {}

    raw_formasi_pers = row_dict.pop("persyaratan_json", None)
    berkas_sscasn: list[dict[str, Any]] = []
    if raw_formasi_pers:
        try:
            parsed = json.loads(raw_formasi_pers)
            if isinstance(parsed, list):
                berkas_sscasn = parsed
        except Exception:
            berkas_sscasn = []

    jf_raw = (row_dict.get("jenis_formasi") or "").strip().upper()
    khusus_map = inst_data.get("berkas_khusus_jalur") or {}
    berkas_jalur: list[str] = []
    if jf_raw and isinstance(khusus_map, dict):
        if jf_raw in khusus_map:
            berkas_jalur = list(khusus_map[jf_raw] or [])
        else:
            for k, v in khusus_map.items():
                ku = str(k).upper()
                if ("DISABILITAS" in jf_raw and "DISABILITAS" in ku) or (
                    "PAPUA" in jf_raw and "PAPUA" in ku
                ) or (
                    ("TERBAIK" in jf_raw or "CUMLAUDE" in jf_raw or "CUM LAUDE" in jf_raw)
                    and ("TERBAIK" in ku or "CUMLAUDE" in ku)
                ):
                    berkas_jalur = list(v or [])
                    break

    usia_min = row_dict.get("usia_min")
    usia_max = row_dict.get("usia_max")
    usia_formasi = f"{usia_min} – {usia_max} tahun" if (usia_min and usia_max) else None

    berkas_wajib_instansi = list(inst_data.get("berkas_wajib") or [])
    if (
        row_dict.get("instansi_id") == "KEMENKES"
        and str(row_dict.get("formasi_id") or "").endswith("-TIDAK")
    ):
        berkas_wajib_instansi = [
            b for b in berkas_wajib_instansi if "STR" not in b.upper()
        ]

    return {
        "status_pengumuman": inst_data.get("status_pengumuman") or "menunggu_pengumuman",
        "nomor_pengumuman": inst_data.get("nomor_pengumuman"),
        "portal_resmi": inst_data.get("portal_resmi"),
        "portal_sscasn": "https://sscasn.bkn.go.id",
        "jadwal_pendaftaran": inst_data.get("jadwal_pendaftaran"),
        "jadwal_ringkas": inst_data.get("jadwal_ringkas") or [],
        "usia_min": usia_min,
        "usia_max": usia_max,
        "usia_formasi": usia_formasi,
        "usia_ringkas": inst_data.get("usia_ringkas"),
        "ipk_minimal": inst_data.get("ipk_minimal"),
        "akreditasi": inst_data.get("akreditasi"),
        "syarat_bahasa": inst_data.get("syarat_bahasa"),
        "syarat_fisik_khusus": inst_data.get("syarat_fisik_khusus"),
        "ikatan_dinas": inst_data.get("ikatan_dinas"),
        "tahapan_skb": inst_data.get("tahapan_skb"),
        "catatan_penting": inst_data.get("catatan_penting"),
        "jobdesc": row_dict.get("jobdesc"),
        "berkas_formasi_sscasn": berkas_sscasn,
        "berkas_wajib_instansi": berkas_wajib_instansi,
        "berkas_khusus_jalur": berkas_jalur,
        "jalur_aktif": row_dict.get("jenis_formasi"),
    }


def _row_to_dict(row: sqlite3.Row, *, include_detail: bool = False) -> dict[str, Any]:
    d = dict(row)
    seen_majors: set[str] = set()
    uniq_majors: list[str] = []
    for m in (d.get("pendidikan_nm") or "").split(" | "):
        cm = m.strip()
        if cm and cm.upper() not in seen_majors:
            seen_majors.add(cm.upper())
            uniq_majors.append(cm)
    d["jurusan_list"] = uniq_majors
    d.update(_resolve_golongan(d.get("jenjang", "")))
    if include_detail:
        d["persyaratan_daftar"] = _build_persyaratan_daftar(d)
    else:
        d.pop("persyaratan_json", None)
        d.pop("jobdesc", None)
        d.pop("pers_ringkasan_json", None)
    return d


@router.get("/stats")
def get_stats_2026(response: Response) -> dict[str, Any]:
    global _stats_cache_2026
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    if _stats_cache_2026 is not None:
        return _stats_cache_2026
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

        payload = {
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
            "sumber_dokumen": "SSCASN Live (Kemenhut, MA RI, KKP, BPKP, Kejaksaan Agung, BGN, Kemenkum, Kemenham, Kemenkop, BPK, Polri, BSSN) • KepmenPANRB 675 (Kemenkeu), 674 (Passing Grade) • SE Kemenkes HK.02.02",
        }
        with _cache_2026_lock:
            _stats_cache_2026 = payload
        return payload
    finally:
        conn.close()


@router.get("/filters")
def get_filters_2026(response: Response) -> dict[str, Any]:
    global _filters_cache_2026
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    if _filters_cache_2026 is not None:
        return _filters_cache_2026
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
                SELECT
                    f.unit_eselon1,
                    COUNT(*) AS cnt,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS kuota,
                    CASE WHEN COUNT(DISTINCT i.instansi_nm) = 1 THEN MIN(i.instansi_nm) ELSE 'Lintas Instansi' END AS instansi_nm,
                    COUNT(f.jumlah_formasi) AS known_kuota_cnt
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                GROUP BY f.unit_eselon1
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
        raw_k24 = cur.execute(
            """
            SELECT
                b.status_keketatan_2024,
                COUNT(*) AS formasi_count,
                COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
            FROM formasi f
            LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
            GROUP BY b.status_keketatan_2024
            """
        ).fetchall()
        order_k24 = {
            "Tanpa Pelamar": 1,
            "Sangat Longgar": 2,
            "Longgar": 3,
            "Moderat": 4,
            "Ketat": 5,
            "Sangat Ketat": 6,
        }
        status_keketatan_2024 = []
        unmatched_2024_count = 0
        unmatched_2024_kuota = 0
        for r in raw_k24:
            st24 = r["status_keketatan_2024"]
            if st24:
                status_keketatan_2024.append(
                    {
                        "status": st24,
                        "formasi_count": r["formasi_count"],
                        "total_kuota": r["total_kuota"],
                    }
                )
            else:
                unmatched_2024_count = r["formasi_count"]
                unmatched_2024_kuota = r["total_kuota"]
        status_keketatan_2024.sort(key=lambda x: (order_k24.get(x["status"], 99), x["status"]))

        flags = cur.execute(
            """
            SELECT
                COUNT(jumlah_pelamar) AS has_p,
                COUNT(CASE WHEN gaji_min > 0 THEN 1 END) AS has_g,
                COUNT(CASE WHEN jenis_formasi IS NOT NULL AND jenis_formasi != '' THEN 1 END) AS has_j
            FROM formasi
            """
        ).fetchone()

        payload = {
            "kategori": kategori,
            "instansi": instansi,
            "instansi_summary": instansi_summary,
            "unit_eselon1": unit_eselon1,
            "jenjang": jenjang,
            "jabatan": jabatan,
            "jenis_formasi": jenis_formasi,
            "status_keketatan": status_keketatan,
            "status_keketatan_2024": status_keketatan_2024,
            "unmatched_2024_count": unmatched_2024_count,
            "unmatched_2024_kuota": unmatched_2024_kuota,
            "has_applicant_data": (flags["has_p"] or 0) > 0,
            "has_salary_data": (flags["has_g"] or 0) > 0,
            "has_jenis_formasi": (flags["has_j"] or 0) > 0,
        }
        with _cache_2026_lock:
            _filters_cache_2026 = payload
        return payload
    finally:
        conn.close()


@router.get("/filters/jurusan")
def search_jurusan_2026(
    response: Response,
    q: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    q_clean = (q or "").strip()
    cache_key = (q_clean.upper(), limit)
    cached = _lru_get(_jurusan_cache_2026, cache_key)
    if cached is not None:
        return cached
    conn = _get_conn()
    try:
        like = f"%{q_clean}%"
        try:
            rows = conn.execute(
                """
                SELECT jurusan_nm, formasi_count, total_kuota
                FROM jurusan
                WHERE UPPER(jurusan_nm) LIKE UPPER(?)
                ORDER BY total_kuota DESC, formasi_count DESC, jurusan_nm ASC
                LIMIT ?
                """,
                (like, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = conn.execute(
                """
                SELECT j.jurusan_nm, COUNT(*) AS formasi_count, COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota
                FROM jurusan j
                CROSS JOIN formasi_jurusan fj ON fj.jurusan_id = j.jurusan_id
                JOIN formasi f ON f.formasi_id = fj.formasi_id
                WHERE UPPER(j.jurusan_nm) LIKE UPPER(?)
                GROUP BY j.jurusan_id, j.jurusan_nm
                ORDER BY total_kuota DESC, j.jurusan_nm ASC
                LIMIT ?
                """,
                (like, limit),
            ).fetchall()
        payload = [dict(r) for r in rows]
        _lru_set(_jurusan_cache_2026, cache_key, payload, _MAX_JURUSAN_CACHE_2026)
        return payload
    finally:
        conn.close()


@router.get("/filters/instansi")
def search_instansi_2026(
    response: Response,
    q: str = Query(default=""),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[dict[str, Any]]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    q_clean = (q or "").strip()
    cache_key = (q_clean.upper(), limit)
    cached = _lru_get(_instansi_cache_2026, cache_key)
    if cached is not None:
        return cached
    conn = _get_conn()
    try:
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
        payload = [dict(r) for r in rows]
        _lru_set(_instansi_cache_2026, cache_key, payload, _MAX_INSTANSI_CACHE_2026)
        return payload
    finally:
        conn.close()


_DEFAULT_ORDER_SQL = (
    "CASE f.instansi_id "
    "WHEN 'KEMENKEU' THEN 1 "
    "WHEN 'BPK' THEN 2 "
    "WHEN 'BSSN' THEN 3 "
    "WHEN 'KEJAGUNG' THEN 4 "
    "WHEN 'KEMENKES' THEN 5 "
    "WHEN 'BPKP' THEN 6 "
    "WHEN 'KEMENKUM' THEN 7 "
    "WHEN 'KEMENKOP' THEN 8 "
    "WHEN 'MA' THEN 9 "
    "WHEN 'KEMENHAM' THEN 10 "
    "WHEN 'POLRI' THEN 11 "
    "WHEN 'KEMENHUT' THEN 12 "
    "WHEN 'KKP' THEN 13 "
    "WHEN 'BGN' THEN 14 "
    "ELSE 99 END ASC, f.instansi_id ASC, f.no_urut ASC, f.formasi_id ASC"
)

_SORT_MAP_2026 = {
    "no_urut": _DEFAULT_ORDER_SQL,
    "kuota_desc": "CASE WHEN f.jumlah_formasi IS NULL THEN 1 ELSE 0 END ASC, f.jumlah_formasi DESC, " + _DEFAULT_ORDER_SQL,
    "kuota_asc": "CASE WHEN f.jumlah_formasi IS NULL THEN 1 ELSE 0 END ASC, f.jumlah_formasi ASC, " + _DEFAULT_ORDER_SQL,
    "jabatan_asc": "f.jabatan_nm ASC, f.jumlah_formasi DESC, " + _DEFAULT_ORDER_SQL,
    "eselon1_asc": "f.unit_eselon1 ASC, f.jumlah_formasi DESC, " + _DEFAULT_ORDER_SQL,
    "rasio_2024_asc": "CASE WHEN b.rasio_2024 IS NULL THEN 1 ELSE 0 END ASC, b.rasio_2024 ASC, f.jumlah_formasi DESC, " + _DEFAULT_ORDER_SQL,
    "rasio_2024_desc": "CASE WHEN b.rasio_2024 IS NULL THEN 1 ELSE 0 END ASC, b.rasio_2024 DESC, f.jumlah_formasi DESC, " + _DEFAULT_ORDER_SQL,
    "rasio_asc": "CASE WHEN f.rasio_kompetisi IS NULL THEN 1 ELSE 0 END ASC, f.rasio_kompetisi ASC, f.jumlah_formasi DESC",
    "peluang_desc": "CASE WHEN f.peluang_lolos_pct IS NULL THEN 1 ELSE 0 END ASC, f.peluang_lolos_pct DESC, f.jumlah_formasi DESC",
    "gaji_desc": "CASE WHEN f.gaji_max IS NULL THEN 1 ELSE 0 END ASC, f.gaji_max DESC, f.jumlah_formasi DESC",
}


@router.get("/formasi")
def list_formasi_2026(
    response: Response,
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
    keketatan_2024: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
    sort_by: str = Query(default="no_urut"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    cache_key = (
        q.strip(), instansi.strip(), eselon1.strip(), kategori.strip(),
        jenjang.strip(), jurusan.strip(), jabatan.strip(), lokasi.strip(),
        jenis_formasi.strip(), keketatan.strip(), keketatan_2024.strip(),
        min_kuota, bool(only_zero_pelamar), sort_by, page, limit,
    )
    cached = _lru_get(_list_cache_2026, cache_key)
    if cached is not None:
        return cached

    order_sql = _SORT_MAP_2026.get(sort_by, _SORT_MAP_2026["no_urut"])

    where_sql, params = _build_filter_clause(
        q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
        jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
        keketatan=keketatan, keketatan_2024=keketatan_2024, min_kuota=min_kuota,
        only_zero_pelamar=only_zero_pelamar,
    )

    conn = _get_conn()
    try:
        needs_b_join = bool((keketatan_2024 or "").strip())
        agg_b_join = "LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id" if needs_b_join else ""
        agg = conn.execute(
            f"""
            SELECT COUNT(*) AS cnt, COALESCE(SUM(f.jumlah_formasi), 0) AS kuota_sum
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            {agg_b_join}
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
                {_FORMASI_LIST_COLS},
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber,
                {_BANDING_2024_SQL.strip()}
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

        payload = {
            "total": total,
            "total_kuota_filtered": total_kuota_filtered,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "items": [_row_to_dict(r) for r in rows],
        }
        _lru_set(_list_cache_2026, cache_key, payload, _MAX_LIST_CACHE_2026)
        return payload
    finally:
        conn.close()


@router.get("/formasi-batch")
def get_formasi_batch_2026(response: Response, ids: str = Query(default="")) -> list[dict[str, Any]]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    id_list = [x.strip() for x in ids.split(",") if x.strip()][:8]
    if not id_list:
        return []
    cache_key = tuple(id_list)
    cached = _lru_get(_batch_cache_2026, cache_key)
    if cached is not None:
        return cached
    placeholders = ",".join("?" for _ in id_list)
    conn = _get_conn()
    try:
        rows = conn.execute(
            f"""
            SELECT
                {_FORMASI_LIST_COLS},
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber,
                {_BANDING_2024_SQL.strip()}
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
            WHERE f.formasi_id IN ({placeholders})
            """,
            id_list,
        ).fetchall()
        by_id = {r["formasi_id"]: _row_to_dict(r) for r in rows}
        payload = [by_id[fid] for fid in id_list if fid in by_id]
        _lru_set(_batch_cache_2026, cache_key, payload, _MAX_BATCH_CACHE_2026)
        return payload
    finally:
        conn.close()


@router.get("/formasi/{formasi_id}")
def get_formasi_detail_2026(formasi_id: str, response: Response) -> dict[str, Any]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    cached = _lru_get(_detail_cache_2026, formasi_id)
    if cached is not None:
        return cached
    conn = _get_conn()
    try:
        row = conn.execute(
            f"""
            SELECT
                f.*,
                i.instansi_nm,
                i.kategori_instansi,
                i.tukin_min,
                i.tukin_max,
                i.tukin_sumber,
                p.ringkasan_json AS pers_ringkasan_json,
                {_BANDING_2024_SQL.strip()}
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            LEFT JOIN persyaratan_instansi p ON p.instansi_id = f.instansi_id
            LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
            WHERE f.formasi_id = ?
            """,
            (formasi_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Formasi {formasi_id} tidak ditemukan.")
        payload = _row_to_dict(row, include_detail=True)
        _lru_set(_detail_cache_2026, formasi_id, payload, _MAX_DETAIL_CACHE_2026)
        return payload
    finally:
        conn.close()


@router.get("/analytics/top")
def get_top_analytics_2026(
    response: Response,
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
    keketatan_2024: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
) -> dict[str, Any]:
    ensure_2026_database_ready()
    _sync_2026_cache_version()
    response.headers["Cache-Control"] = _CDN_CACHE_HEADER
    cache_key = (
        q.strip(), instansi.strip(), eselon1.strip(), kategori.strip(),
        jenjang.strip(), jurusan.strip(), jabatan.strip(), lokasi.strip(),
        jenis_formasi.strip(), keketatan.strip(), keketatan_2024.strip(),
        min_kuota, bool(only_zero_pelamar),
    )
    cached = _lru_get(_analytics_cache_2026, cache_key)
    if cached is not None:
        return cached
    where_sql, params = _build_filter_clause(
        q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
        jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
        keketatan=keketatan, keketatan_2024=keketatan_2024, min_kuota=min_kuota,
        only_zero_pelamar=only_zero_pelamar,
    )
    conn = _get_conn()
    try:
        cur = conn.cursor()
        b_join_opt = (
            "LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id"
            if (keketatan_2024 or "").strip()
            else ""
        )
        agg = cur.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                COUNT(f.jumlah_pelamar) AS has_p
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            {b_join_opt}
            WHERE {where_sql}
            """,
            params,
        ).fetchone()
        has_applicants = (agg["has_p"] or 0) > 0

        top_jurusan = [
            dict(r)
            for r in cur.execute(
                f"""
                WITH filtered_f AS MATERIALIZED (
                    SELECT f.formasi_id, f.jumlah_formasi, f.jumlah_pelamar
                    FROM formasi f
                    JOIN instansi i ON i.instansi_id = f.instansi_id
                    {b_join_opt}
                    WHERE {where_sql}
                )
                SELECT
                    j.jurusan_nm,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(ff.jumlah_formasi), 0) AS total_kuota,
                    CASE WHEN COUNT(ff.jumlah_pelamar) > 0 THEN SUM(ff.jumlah_pelamar) ELSE NULL END AS total_pelamar
                FROM filtered_f ff
                CROSS JOIN formasi_jurusan fj ON fj.formasi_id = ff.formasi_id
                JOIN jurusan j ON j.jurusan_id = fj.jurusan_id
                GROUP BY fj.jurusan_id, j.jurusan_nm
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
                {b_join_opt}
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
                {b_join_opt}
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
                {b_join_opt}
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
                    LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
                    WHERE {where_sql} AND f.status_keketatan IS NOT NULL
                    GROUP BY f.status_keketatan
                    ORDER BY total_kuota DESC
                    """,
                    params,
                ).fetchall()
            ]

        keketatan_2024_dist = [
            dict(r)
            for r in cur.execute(
                f"""
                SELECT
                    COALESCE(b.status_keketatan_2024, 'Belum Ada Pembanding 2024') AS status_keketatan_2024,
                    CASE WHEN b.status_keketatan_2024 IS NULL THEN '__NONE__' ELSE b.status_keketatan_2024 END AS filter_value,
                    COUNT(*) AS formasi_count,
                    COALESCE(SUM(f.jumlah_formasi), 0) AS total_kuota,
                    ROUND(AVG(b.rasio_2024), 1) AS avg_rasio_2024
                FROM formasi f
                JOIN instansi i ON i.instansi_id = f.instansi_id
                LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
                WHERE {where_sql}
                GROUP BY b.status_keketatan_2024
                ORDER BY
                    CASE COALESCE(b.status_keketatan_2024, '__NONE__')
                        WHEN 'Tanpa Pelamar' THEN 1
                        WHEN 'Sangat Longgar' THEN 2
                        WHEN 'Longgar' THEN 3
                        WHEN 'Moderat' THEN 4
                        WHEN 'Ketat' THEN 5
                        WHEN 'Sangat Ketat' THEN 6
                        WHEN '__NONE__' THEN 9
                        ELSE 8
                    END ASC
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
                LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
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
                LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
                WHERE {where_sql}
                GROUP BY i.instansi_id, i.instansi_nm
                ORDER BY total_kuota DESC, i.instansi_nm ASC
                """,
                params,
            ).fetchall()
        ]

        payload = {
            "total_rows": agg["total_rows"] or 0,
            "total_kuota": agg["total_kuota"] or 0,
            "has_applicant_data": has_applicants,
            "top_jurusan": top_jurusan,
            "top_jabatan": top_jabatan,
            "top_eselon1": top_eselon1,
            "jenjang_dist": jenjang_dist,
            "keketatan_dist": keketatan_dist,
            "keketatan_2024_dist": keketatan_2024_dist,
            "kategori_dist": kategori_dist,
            "instansi_dist": instansi_dist,
        }
        _lru_set(_analytics_cache_2026, cache_key, payload, _MAX_ANALYTICS_CACHE_2026)
        return payload
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
    keketatan_2024: str = Query(default=""),
    min_kuota: Optional[int] = Query(default=None),
    only_zero_pelamar: bool = Query(default=False),
    sort_by: str = Query(default="no_urut"),
    ids: str = Query(default=""),
):
    id_list = [x.strip() for x in ids.split(",") if x.strip()][:50]
    order_sql = _SORT_MAP_2026.get(sort_by, _SORT_MAP_2026["no_urut"])
    if id_list:
        placeholders = ",".join("?" for _ in id_list)
        where_sql = f"f.formasi_id IN ({placeholders})"
        params: list[Any] = list(id_list)
    else:
        where_sql, params = _build_filter_clause(
            q=q, instansi=instansi, eselon1=eselon1, kategori=kategori, jenjang=jenjang,
            jurusan=jurusan, jabatan=jabatan, lokasi=lokasi, jenis_formasi=jenis_formasi,
            keketatan=keketatan, keketatan_2024=keketatan_2024, min_kuota=min_kuota,
            only_zero_pelamar=only_zero_pelamar,
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
                f.sumber_dokumen,
                b.kursi_2024,
                b.pelamar_2024,
                b.rasio_2024,
                b.status_keketatan_2024,
                COALESCE(b.match_label_2024, 'Tidak ada pembanding di 2024') AS match_label_2024
            FROM formasi f
            JOIN instansi i ON i.instansi_id = f.instansi_id
            LEFT JOIN banding_2024 b ON b.formasi_id = f.formasi_id
            WHERE {where_sql}
            ORDER BY {order_sql}
            """,
            params,
        ).fetchall()
        if id_list:
            by_id = {r["formasi_id"]: r for r in rows}
            rows = [by_id[fid] for fid in id_list if fid in by_id]

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "No", "Formasi ID", "Instansi", "Kategori", "Unit Eselon I",
            "Jabatan", "Unit Penempatan", "Kualifikasi Pendidikan", "Jenjang",
            "Alokasi CPNS", "Jenis Formasi", "Jumlah Pelamar", "Rasio Kompetisi",
            "Status Keketatan", "Gaji Min", "Gaji Max", "Sumber Dokumen",
            "Kursi 2024", "Pelamar 2024", "Rasio 2024", "Keketatan 2024", "Pembanding 2024",
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
