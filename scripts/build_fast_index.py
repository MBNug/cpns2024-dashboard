"""
Builds compact integer-rowid acceleration tables, WITHOUT ROWID inverted major index,
contentless FTS5 full-text index, and O(1) precomputed summary tables inside cpns2024.db,
then recompresses cpns2024.db.gz (level 9) for zero-CPU cold-start on Render.
"""

import gzip
import os
import shutil
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cpns2024.db"
GZ_PATH = BASE_DIR / "data" / "cpns2024.db.gz"

KAT_TO_ID = {"Pusat": 0, "Provinsi": 1, "Kabupaten/Kota": 2}
KEK_TO_ID = {"Tanpa Pelamar": 0, "Sangat Longgar": 1, "Moderat": 2, "Sangat Ketat": 3}
JENJANG_BITS = {
    "S-1": 1,
    "D-III": 2,
    "D-IV": 4,
    "S-2": 8,
    "SMA/SMK": 16,
    "S-3/Spesialis": 32,
    "Profesi": 64,
}


def build_acceleration_structures(db_path: Path = DB_PATH, recompress_gz: bool = True) -> None:
    t0 = time.perf_counter()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode = DELETE;")
    conn.execute("PRAGMA synchronous = OFF;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA cache_size = -128000;")

    cur = conn.cursor()
    print("[1/5] Dropping redundant/stale auxiliary structures...")
    cur.executescript("""
        DROP TABLE IF EXISTS f_idx;
        DROP TABLE IF EXISTS fj_fast;
        DROP TABLE IF EXISTS f_fts;
        DROP TABLE IF EXISTS agg_top_jurusan;
        DROP TABLE IF EXISTS agg_top_instansi;
        DROP TABLE IF EXISTS agg_jenjang_summary;
        DROP INDEX IF EXISTS idx_fj_jurusan;
    """)

    print("[2/5] Loading lookup maps and computing per-formation jenjang bitmasks...")
    ins_map = {
        r[0]: (r[1], KAT_TO_ID.get(r[2], 2))
        for r in cur.execute("SELECT instansi_id, nama_instansi, kategori_instansi FROM instansi")
    }
    jur_tier = {
        r[0]: JENJANG_BITS.get(r[1], 0)
        for r in cur.execute("SELECT jurusan_id, jenjang FROM jurusan")
    }

    # Pre-order rid 1..N by default sort (jumlah_formasi DESC, gaji_max DESC)
    raw_formasi = cur.execute("""
        SELECT
            formasi_id, instansi_id, jabatan_nm, lokasi_nm,
            COALESCE(jenis_formasi, 'UMUM'),
            COALESCE(jumlah_formasi, 0),
            COALESCE(jumlah_pelamar, 0),
            COALESCE(rasio_kompetisi, 0.0),
            COALESCE(status_keketatan, 'Tanpa Pelamar'),
            COALESCE(gaji_min, 0),
            COALESCE(gaji_max, 0),
            COALESCE(golongan_awal, '-')
        FROM formasi
        ORDER BY jumlah_formasi DESC, gaji_max DESC
    """).fetchall()

    fid_to_rid = {}
    for rid, r in enumerate(raw_formasi, start=1):
        fid_to_rid[r[0]] = rid

    masks = [0] * (len(raw_formasi) + 1)
    fj_pairs = []
    from collections import defaultdict
    j_cnt = defaultdict(int)
    j_kuota = defaultdict(int)
    j_pelamar = defaultdict(int)
    j_rasio_sum = defaultdict(float)
    j_kosong = defaultdict(int)
    j_gmax_sum = defaultdict(int)

    # Fast tuple lookup by rid
    kuota_by_rid = [0] * (len(raw_formasi) + 1)
    pelamar_by_rid = [0] * (len(raw_formasi) + 1)
    rasio_by_rid = [0.0] * (len(raw_formasi) + 1)
    gmax_by_rid = [0] * (len(raw_formasi) + 1)
    for rid, r in enumerate(raw_formasi, start=1):
        kuota_by_rid[rid] = r[5]
        pelamar_by_rid[rid] = r[6]
        rasio_by_rid[rid] = r[7]
        gmax_by_rid[rid] = r[10]

    for fid, jid in cur.execute("SELECT formasi_id, jurusan_id FROM formasi_jurusan"):
        rid = fid_to_rid.get(fid)
        if rid is not None:
            masks[rid] |= jur_tier.get(jid, 0)
            fj_pairs.append((jid, rid))
            j_cnt[jid] += 1
            j_kuota[jid] += kuota_by_rid[rid]
            p = pelamar_by_rid[rid]
            j_pelamar[jid] += p
            j_rasio_sum[jid] += rasio_by_rid[rid]
            if p == 0:
                j_kosong[jid] += 1
            j_gmax_sum[jid] += gmax_by_rid[rid]

    print("[3/5] Writing f_idx, fj_fast (WITHOUT ROWID), and contentless FTS5 index...")
    cur.execute("""
        CREATE TABLE f_idx (
            rid INTEGER PRIMARY KEY,
            fid TEXT NOT NULL UNIQUE,
            ins_id INTEGER NOT NULL,
            kat_id INTEGER NOT NULL,
            kuota INTEGER NOT NULL,
            pelamar INTEGER NOT NULL,
            rasio REAL NOT NULL,
            kek_id INTEGER NOT NULL,
            gmin INTEGER NOT NULL,
            gmax INTEGER NOT NULL,
            gol TEXT NOT NULL,
            jenjang_mask INTEGER NOT NULL
        )
    """)

    f_idx_rows = []
    fts_rows = []
    for rid, r in enumerate(raw_formasi, start=1):
        fid = r[0]
        ins_id = r[1]
        ins_nm, kat_id = ins_map.get(ins_id, ("", 2))
        kek_id = KEK_TO_ID.get(r[8], 2)
        f_idx_rows.append((
            rid, fid, ins_id, kat_id,
            r[5], r[6], r[7], kek_id,
            r[9], r[10], r[11], masks[rid]
        ))
        fts_rows.append((rid, fid, r[2], r[3], ins_nm))

    cur.executemany("INSERT INTO f_idx VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", f_idx_rows)
    cur.execute("CREATE INDEX idx_fidx_ins ON f_idx(ins_id, rid)")
    cur.execute("CREATE INDEX idx_fidx_kat ON f_idx(kat_id, rid)")
    cur.execute("CREATE INDEX idx_fidx_kek ON f_idx(kek_id, rid)")
    cur.execute("CREATE INDEX idx_fidx_gmax ON f_idx(gmax DESC, kuota DESC)")
    cur.execute("CREATE INDEX idx_fidx_gmin ON f_idx(gmin DESC, gmax DESC)")
    cur.execute("CREATE INDEX idx_fidx_rasio ON f_idx(rasio ASC, kuota DESC)")
    cur.execute("CREATE INDEX idx_fidx_pelamar ON f_idx(pelamar ASC, kuota DESC)")

    fj_pairs.sort()
    cur.execute("""
        CREATE TABLE fj_fast (
            jid INTEGER NOT NULL,
            rid INTEGER NOT NULL,
            PRIMARY KEY (jid, rid)
        ) WITHOUT ROWID
    """)
    cur.executemany("INSERT INTO fj_fast VALUES (?, ?)", fj_pairs)
    cur.execute("CREATE INDEX idx_fjfast_rid ON fj_fast(rid, jid)")

    cur.execute("""
        CREATE VIRTUAL TABLE f_fts USING fts5(
            fid, jabatan, lokasi, ins_nama,
            content='',
            tokenize='unicode61 remove_diacritics 2'
        )
    """)
    cur.executemany(
        "INSERT INTO f_fts(rowid, fid, jabatan, lokasi, ins_nama) VALUES (?,?,?,?,?)",
        fts_rows,
    )

    print("[4/5] Writing O(1) summary tables (agg_top_jurusan, agg_top_instansi, agg_jenjang_summary)...")
    cur.execute("""
        CREATE TABLE agg_top_jurusan (
            jurusan_id INTEGER PRIMARY KEY,
            nama_jurusan TEXT NOT NULL,
            jenjang TEXT NOT NULL,
            total_formasi INTEGER NOT NULL,
            total_kuota INTEGER NOT NULL,
            total_pelamar INTEGER NOT NULL,
            avg_gaji_max INTEGER NOT NULL,
            avg_rasio REAL NOT NULL,
            total_kosong INTEGER NOT NULL
        )
    """)
    j_rows = []
    for jid, nama, jenjang in cur.execute("SELECT jurusan_id, nama_jurusan, jenjang FROM jurusan"):
        cnt = j_cnt.get(jid, 0)
        if cnt > 0:
            j_rows.append((
                jid,
                nama,
                jenjang,
                cnt,
                j_kuota[jid],
                j_pelamar[jid],
                int(round(j_gmax_sum[jid] / cnt)),
                round(j_rasio_sum[jid] / cnt, 2),
                j_kosong[jid],
            ))
    cur.executemany("INSERT INTO agg_top_jurusan VALUES (?,?,?,?,?,?,?,?,?)", j_rows)
    cur.execute("CREATE INDEX idx_agg_jurusan_kuota ON agg_top_jurusan(total_kuota DESC, total_formasi DESC)")
    cur.execute("CREATE INDEX idx_agg_jurusan_jenjang ON agg_top_jurusan(jenjang, total_kuota DESC)")

    cur.execute("""
        CREATE TABLE agg_top_instansi AS
        SELECT
            i.instansi_id AS instansi_id,
            i.nama_instansi AS nama_instansi,
            i.kategori_instansi AS kategori_instansi,
            COUNT(fi.rid) AS total_formasi,
            COALESCE(SUM(fi.kuota), 0) AS total_kuota,
            COALESCE(SUM(fi.pelamar), 0) AS total_pelamar,
            CAST(ROUND(COALESCE(AVG(fi.gmax), 0)) AS INTEGER) AS avg_gaji_max,
            ROUND(COALESCE(AVG(fi.rasio), 0), 2) AS avg_rasio,
            SUM(CASE WHEN fi.pelamar = 0 THEN 1 ELSE 0 END) AS total_kosong
        FROM instansi i
        INNER JOIN f_idx fi ON fi.ins_id = i.instansi_id
        GROUP BY i.instansi_id
    """)
    cur.execute("CREATE UNIQUE INDEX idx_agg_instansi_pk ON agg_top_instansi(instansi_id)")
    cur.execute("CREATE INDEX idx_agg_instansi_kuota ON agg_top_instansi(total_kuota DESC, total_formasi DESC)")
    cur.execute("CREATE INDEX idx_agg_instansi_kat ON agg_top_instansi(kategori_instansi, total_kuota DESC)")

    cur.execute("""
        CREATE TABLE agg_jenjang_summary (
            jenjang TEXT PRIMARY KEY,
            bit INTEGER NOT NULL,
            total_formasi INTEGER NOT NULL,
            total_kuota INTEGER NOT NULL,
            total_pelamar INTEGER NOT NULL,
            avg_rasio REAL NOT NULL,
            total_kosong INTEGER NOT NULL
        )
    """)
    for j_name, bit in JENJANG_BITS.items():
        row = cur.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(SUM(kuota), 0),
                COALESCE(SUM(pelamar), 0),
                ROUND(COALESCE(AVG(rasio), 0), 2),
                SUM(CASE WHEN pelamar = 0 THEN 1 ELSE 0 END)
            FROM f_idx
            WHERE (jenjang_mask & ?) != 0
            """,
            (bit,),
        ).fetchone()
        cur.execute(
            "INSERT INTO agg_jenjang_summary VALUES (?,?,?,?,?,?,?)",
            (j_name, bit, row[0] or 0, row[1] or 0, row[2] or 0, float(row[3] or 0.0), row[4] or 0),
        )

    conn.commit()
    print("[5/5] Running ANALYZE + VACUUM for compact page layout...")
    cur.execute("ANALYZE;")
    conn.commit()
    cur.execute("VACUUM;")
    conn.close()

    db_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"SQLite DB optimized in {(time.perf_counter() - t0):.1f}s | Uncompressed size: {db_mb:.1f} MB")

    if recompress_gz:
        t_gz = time.perf_counter()
        tmp_gz = gz_path_tmp = db_path.parent / "cpns2024.db.gz.tmp"
        with open(db_path, "rb") as f_in:
            with gzip.open(tmp_gz, "wb", compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
        os.replace(tmp_gz, GZ_PATH)
        gz_mb = GZ_PATH.stat().st_size / (1024 * 1024)
        print(f"Compressed {GZ_PATH.name} in {(time.perf_counter() - t_gz):.1f}s | GZip size: {gz_mb:.2f} MB")


if __name__ == "__main__":
    build_acceleration_structures()
