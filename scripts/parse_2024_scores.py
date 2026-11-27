"""Parse official CPNS 2024 Hasil Integrasi SKD-SKB PDFs for the 6 active CPNS 2026 agencies.

Extracts verified per-formation exam score statistics (Nilai Akhir Lulus P/L,
Skor SKD Lulus & Batas Masuk SKB, Nilai SKB Lulus) from both BKN Ringkas tables
and BKN Rincian blocks, validates every section against BKN REKAP summary pages
and arithmetic checksums, and maps each section 1-to-1 to cpns2024.db formasi_ids.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import time
import unicodedata
from typing import Any

import pypdfium2 as pdfium


BASE_DIR = Path(__file__).resolve().parents[1]
SCORES_ROOT = Path(r"D:\AG Files\cpns2026-scraper\data\refs\scores_2024")
RAW_OUT_PATH = Path(r"D:\AG Files\cpns2026-scraper\data\parsed\scores_2024_6instansi_raw.json")
SUMMARY_OUT_PATH = BASE_DIR / "data" / "scores_2024_6instansi.json"
CPNS2024_DB_PATH = BASE_DIR / "data" / "cpns2024.db"

AGENCY_SPECS: list[dict[str, Any]] = [
    {
        "instansi_kode": "BSSN",
        "instansi_id_2024": 111,
        "instansi_nm": "Badan Siber dan Sandi Negara",
        "format": "ringkas",
        "pdf_candidates": [
            SCORES_ROOT / "bssn" / "4010_HASIL-RINGKAS-CPNS-BSSN-2024.pdf",
        ],
        "sumber": "PENG.3 & PENG.5/BSSN/SU/KP.02.01/01/2025 (Pasca Sanggah: 0 sanggahan diterima)",
    },
    {
        "instansi_kode": "KEJAGUNG",
        "instansi_id_2024": 2,
        "instansi_nm": "Kejaksaan Agung",
        "format": "ringkas",
        "pdf_candidates": [
            SCORES_ROOT / "kejagung" / "HASIL_INTEGRASI_SKD_SKB_LAMPIRAN_I_RINGKAS.pdf",
        ],
        "sumber": "Lampiran I Ringkas Hasil Integrasi SKD-SKB Kejaksaan Agung TA 2024",
    },
    {
        "instansi_kode": "BPKP",
        "instansi_id_2024": 4,
        "instansi_nm": "Badan Pengawasan Keuangan dan Pembangunan",
        "format": "ringkas",
        "pdf_candidates": [
            SCORES_ROOT / "bpkp" / "20250107220401_Lampiran_I.pdf",
        ],
        "sumber": "KP.00.01/PENG-1 & PENG-2/SU/02/2025 (Pasca Sanggah: 0 dari 128 sanggahan diterima)",
    },
    {
        "instansi_kode": "KEMENKEU",
        "instansi_id_2024": 10,
        "instansi_nm": "Kementerian Keuangan",
        "format": "ringkas",
        "pdf_candidates": [
            SCORES_ROOT / "kemenkeu" / "0e5a6b92-6bc9-4ad7-b865-0b67a5338ed0.pdf",
            SCORES_ROOT / "kemenkeu" / "af8f7edf-a394-4e42-96a4-6dad62b27843.pdf",
        ],
        "sumber": "PENG-08/PANREK/2025 (Pasca Pembatalan & Penggantian Kelulusan, 14 Mar 2025)",
    },
    {
        "instansi_kode": "KEMENKES",
        "instansi_id_2024": 11,
        "instansi_nm": "Kementerian Kesehatan",
        "format": "ringkas",
        "pdf_candidates": [
            SCORES_ROOT / "kemenkes" / "Lampiran_I_Ringkasan_hasil_Integrasi_SKD_dan_SKB.pdf",
        ],
        "sumber": "KP.01.02/A/78/2025 Lampiran I Ringkasan Hasil Integrasi SKD-SKB (Pra-Sanggah 9 Jan 2025)",
    },
    {
        "instansi_kode": "BPK",
        "instansi_id_2024": 102,
        "instansi_nm": "Badan Pemeriksa Keuangan",
        "format": "rincian",
        "pdf_candidates": [
            SCORES_ROOT / "bpk" / "Lampiran-Rekap-Hasil-Integrasi-SKD-dan-SKB-Rincian-_0.pdf",
            SCORES_ROOT / "bpk" / "2-SPeng-Lamp-1_Rekap-Hasil-Integrasi-SKD-dan-SKB-Rincian.pdf",
        ],
        "sumber": "2/S.Peng/X/01/2025 & 3/S.Peng/X/01/2025 (Pasca Sanggah: 0 sanggahan diterima)",
    },
]

STATUS_PATTERN = r"P/L(?:-[A-Z0-9]+)?|P|TL|TMS(?:-\d+)?|TH|APS"
RE_PESERTA_START = re.compile(r"^(\d{1,5})\s+(2\d{16})\b")
RE_RINGKAS_TAIL = re.compile(
    rf"(\d+(?:\.\d+)?|-)\s+(\d{{1,3}})\s+(\d{{1,3}})\s+(\d{{1,3}})\s+(\d{{1,3}})\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?|-)\s+(\d+(?:\.\d+)?|-)\s+(\d+(?:\.\d+)?)\s+({STATUS_PATTERN})\s*$"
)
RE_REKAP_DATA = re.compile(r"^(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$")
RE_RINCIAN_START = re.compile(r"(?:^|\n)(\d{1,5})\n(24\d{15})\b")
RE_RINCIAN_TIU = re.compile(r"2\.\s*Tes Intelegensi Umum \(TIU\)\s+(\d{1,3})\s+(\d+(?:\.\d+)?)")
RE_RINCIAN_TKP = re.compile(r"3\.\s*Tes Karakteristik Pribadi \(TKP\)\s+(\d{1,3})\s*\n\s*(\d+(?:\.\d+)?)\s*\n\s*(\d+(?:\.\d+)?)")
RE_RINCIAN_SKB = re.compile(
    rf"(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*\n\s*({STATUS_PATTERN})\s*\n\s*(\d{{1,3}})\s*\n\s*(\d{{1,3}})\b"
)


def _extract_pdf_chunk(args: tuple[str, int, int]) -> list[tuple[int, str]]:
    pdf_path, start_idx, end_idx = args
    doc = pdfium.PdfDocument(pdf_path)
    out: list[tuple[int, str]] = []
    for idx in range(start_idx, end_idx):
        out.append((idx, doc[idx].get_textpage().get_text_range().replace("\r\n", "\n")))
    return out


def iter_pdf_pages(pdf_path: Path) -> list[str]:
    doc = pdfium.PdfDocument(str(pdf_path))
    n_pages = len(doc)
    doc.close()

    if n_pages < 400:
        return [t for _, t in _extract_pdf_chunk((str(pdf_path), 0, n_pages))]

    workers = min(6, max(2, (os.cpu_count() or 4) - 1))
    chunk = max(100, (n_pages + workers - 1) // workers)
    tasks = [
        (str(pdf_path), i, min(n_pages, i + chunk))
        for i in range(0, n_pages, chunk)
    ]
    pages = [""] * n_pages
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for batch in pool.map(_extract_pdf_chunk, tasks):
            for idx, txt in batch:
                pages[idx] = txt
    return pages


def _norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _norm_key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"[^A-Za-z0-9]+", " ", s.upper()).strip()
    return s


def parse_rekap_header(page_txt: str) -> dict[str, Any]:
    """Extract normalized Jabatan, Lokasi, Jenis Formasi, Pendidikan from REKAP page."""
    head = page_txt.split("REKAP HASIL INTEGRASI")[0]
    lines = [_norm_ws(ln) for ln in head.splitlines() if _norm_ws(ln)]
    if lines and lines[0].startswith("PANITIA SELEKSI NASIONAL"):
        lines = lines[1:]

    joined = "\n".join(lines)

    # 1. Jabatan Formasi (may wrap before Kode Jumlah, including hyphen-split or ': -' moved to end)
    jab_kode, jab_nm, jab_qty = "", "", None
    m_jab = re.search(
        r"Jabatan Formasi\s*:?\s*([A-Z0-9]+(?:-\s*\n?\s*\d+)?)\s*(?::\s*-\s*|-\s+|\s+)(.+?)\s+(\d+)\s*(?:\nKode Jumlah|\nInstansi|$)",
        joined,
        re.S,
    )
    if m_jab:
        jab_kode = re.sub(r"\s+", "", m_jab.group(1))
        raw_jnm = re.sub(r"\s*:\s*-\s*$", "", _norm_ws(m_jab.group(2)))
        jab_nm = _norm_ws(raw_jnm)
        jab_qty = int(m_jab.group(3))

    # 2. Lokasi Formasi (either single-line or wrapped ABOVE 'Lokasi Formasi : <kode> -')
    lok_kode, lok_nm, lok_qty = "", "", None
    idx_ins = next((i for i, l in enumerate(lines) if l.startswith("Instansi :")), -1)
    idx_lok = next((i for i, l in enumerate(lines) if "Lokasi Formasi :" in l), -1)
    idx_jf = next((i for i, l in enumerate(lines) if l.startswith("Jenis Formasi :")), -1)
    idx_pend = next((i for i, l in enumerate(lines) if l.startswith("Pendidikan")), -1)

    if idx_lok >= 0:
        end_lok = idx_jf if idx_jf > idx_lok else len(lines)
        lok_line = lines[idx_lok]
        if lok_line.startswith("Lokasi Formasi :"):
            seg = " ".join(lines[idx_lok:end_lok])
            m_l = re.match(r"Lokasi Formasi\s*:\s*([A-Z0-9-]+)\s*-\s*(.+?)\s+(\d+)$", seg)
            if m_l:
                lok_kode = m_l.group(1).strip()
                lok_nm = _norm_ws(m_l.group(2))
                lok_qty = int(m_l.group(3))
        else:
            # Wrapped form: '<qty> <text...>\n<text...> Lokasi Formasi : <kode> -'
            m_code = re.search(r"Lokasi Formasi\s*:\s*([A-Z0-9-]+)\s*-\s*(.*)$", lok_line)
            if m_code:
                lok_kode = m_code.group(1).strip()
            pre_parts: list[str] = []
            if idx_ins >= 0:
                pre_parts.extend(lines[idx_ins + 1 : idx_lok])
            prefix_on_lok = lok_line.split("Lokasi Formasi :")[0].strip()
            if prefix_on_lok:
                pre_parts.append(prefix_on_lok)
            raw_pre = _norm_ws(" ".join(pre_parts))
            m_q = re.match(r"^(\d+)\s+(.+)$", raw_pre)
            if m_q:
                lok_qty = int(m_q.group(1))
                lok_nm = _norm_ws(m_q.group(2))
            else:
                lok_nm = raw_pre

    # 3. Jenis Formasi
    jf_kode, jf_nm, jf_qty = "", "", None
    if idx_jf >= 0:
        end_jf = idx_pend if idx_pend > idx_jf else len(lines)
        jf_seg = _norm_ws(" ".join(lines[idx_jf:end_jf]))
        m_jf = re.match(r"Jenis Formasi\s*:\s*([A-Z0-9-]+)\s*-\s*(.+?)\s+(\d+)$", jf_seg)
        if m_jf:
            jf_kode = m_jf.group(1).strip()
            jf_nm = _norm_ws(m_jf.group(2))
            jf_qty = int(m_jf.group(3))

    # 4. Pendidikan + section quota
    pend_raw, pend_qty = "", None
    if idx_pend >= 0:
        pend_seg = _norm_ws(" ".join(lines[idx_pend:]))
        m_p = re.match(r"Pendidikan\s+(.+?)\s+(\d+)$", pend_seg)
        if m_p:
            pend_raw = _norm_ws(m_p.group(1))
            pend_qty = int(m_p.group(2))

    return {
        "jab_kode": jab_kode,
        "jabatan_nm": jab_nm,
        "jabatan_qty": jab_qty,
        "lok_kode": lok_kode,
        "lokasi_nm": lok_nm,
        "lokasi_qty": lok_qty,
        "jf_kode": jf_kode,
        "jenis_formasi": jf_nm,
        "jf_qty": jf_qty,
        "pendidikan_raw": pend_raw,
        "jumlah_formasi_header": pend_qty,
    }


def parse_rekap_counts(page_txt: str) -> dict[str, int] | None:
    after = page_txt.split("REKAP HASIL INTEGRASI")[1]
    for ln in after.splitlines():
        s = ln.strip()
        if s == "1 2 3 4 5 6 7 10":
            continue
        m = RE_REKAP_DATA.match(s)
        if m:
            peserta, formasi, metode, hadir, th, tl, tms, lulus = (int(m.group(k)) for k in range(1, 9))
            # Check optional rows 8 (TMS-1) & 9 (APS) if present
            m_tms1 = re.search(r"TMS-1\s*\n\s*(?:8\s*\n\s*(\d+)|(\d+)\s*\n\s*8)", after)
            m_aps = re.search(r"(?:9\s*\n\s*APS|APS\s*\n\s*9)\b", after)
            return {
                "peserta_skb": peserta,
                "jumlah_formasi": formasi,
                "metode_skb": metode,
                "hadir": hadir,
                "th": th,
                "tl": tl,
                "tms": tms,
                "lulus_akhir": lulus,
            }
    return None


def compute_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None, "mean": None}
    xs = sorted(values)
    n = len(xs)
    med = round(statistics.median(xs), 3)
    if n >= 4:
        qs = statistics.quantiles(xs, n=4, method="inclusive")
        p25, p75 = round(qs[0], 3), round(qs[2], 3)
    else:
        p25, p75 = round(xs[0], 3), round(xs[-1], 3)
    return {
        "n": n,
        "min": round(xs[0], 3),
        "p25": p25,
        "median": med,
        "p75": p75,
        "max": round(xs[-1], 3),
        "mean": round(sum(xs) / n, 3),
    }


def parse_agency_pdf(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pdf_path = next((p for p in spec["pdf_candidates"] if p.exists()), None)
    if not pdf_path:
        raise FileNotFoundError(f"No PDF found for {spec['instansi_kode']}")

    t0 = time.time()
    pages = iter_pdf_pages(pdf_path)
    fmt = spec["format"]
    sections: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    unmatched: list[tuple[int, str]] = []
    math_errs = 0

    for idx, txt in enumerate(pages):
        pg_num = idx + 1
        if "REKAP HASIL INTEGRASI" in txt:
            if cur is not None:
                sections.append(cur)
            header = parse_rekap_header(txt)
            rekap = parse_rekap_counts(txt)
            cur = {
                "page_rekap": pg_num,
                "header": header,
                "rekap": rekap,
                "rows": [],
            }
        elif cur is not None and ("HASIL INTEGRASI" in txt or "Halaman " in txt):
            if fmt == "ringkas":
                if "(14) (15)" not in txt and "No Peserta" not in txt:
                    continue
                lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                start = 0
                for li, ln in enumerate(lines):
                    if ln == "(1) (14) (15)" or ln == "(15)":
                        start = li + 1
                        break
                end = len(lines)
                for li in range(len(lines) - 1, -1, -1):
                    if lines[li].startswith("Laporan digenerate"):
                        end = li
                        break
                buf = ""
                for ln in lines[start:end]:
                    if RE_PESERTA_START.match(ln):
                        if buf:
                            unmatched.append((pg_num, buf))
                        buf = ln
                    else:
                        buf = (buf + " " + ln).strip() if buf else ln
                    m = RE_RINGKAS_TAIL.search(buf)
                    if m and RE_PESERTA_START.match(buf):
                        twk, tiu, tkp, tot = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
                        skd40 = float(m.group(6))
                        skb = None if m.group(7) == "-" else float(m.group(7))
                        skb60 = 0.0 if m.group(8) == "-" else float(m.group(8))
                        na = float(m.group(9))
                        st = m.group(10)
                        if (
                            twk + tiu + tkp == tot
                            and abs((tot / 5.5) * 0.4 - skd40) <= 0.05
                            and abs(skd40 + skb60 - na) <= 0.05
                        ):
                            cur["rows"].append(
                                {
                                    "skd": tot,
                                    "skb": 0.0 if skb is None else skb,
                                    "na": na,
                                    "st": st,
                                }
                            )
                            buf = ""
                if buf:
                    unmatched.append((pg_num, buf))
            else:
                txt_body = txt.split("Laporan digenerate")[0]
                matches = list(RE_RINCIAN_START.finditer(txt_body))
                for k, m in enumerate(matches):
                    start = m.start()
                    end = matches[k + 1].start() if k + 1 < len(matches) else len(txt_body)
                    blk = txt_body[start:end]
                    m_tiu = RE_RINCIAN_TIU.search(blk)
                    m_tkp = RE_RINCIAN_TKP.search(blk)
                    m_skb = RE_RINCIAN_SKB.search(blk)
                    if not (m_tiu and m_tkp and m_skb):
                        unmatched.append((pg_num, m.group(2)))
                        continue
                    tiu = int(m_tiu.group(1))
                    tkp, skd40, na = int(m_tkp.group(1)), float(m_tkp.group(2)), float(m_tkp.group(3))
                    skb100, skb60, st, twk, tot = (
                        float(m_skb.group(1)),
                        float(m_skb.group(2)),
                        m_skb.group(3),
                        int(m_skb.group(4)),
                        int(m_skb.group(5)),
                    )
                    if (
                        twk + tiu + tkp != tot
                        or abs((tot / 5.5) * 0.4 - skd40) > 0.05
                        or abs(skd40 + skb60 - na) > 0.05
                    ):
                        math_errs += 1
                    cur["rows"].append({"skd": tot, "skb": skb100, "na": na, "st": st})

    if cur is not None:
        sections.append(cur)

    # Validate REKAP totals vs parsed participant rows
    mismatches = []
    for sec in sections:
        rk = sec["rekap"]
        rows = sec["rows"]
        pl_cnt = sum(1 for r in rows if r["st"].startswith("P/L"))
        if not rk:
            mismatches.append((sec["page_rekap"], "missing_rekap"))
        elif len(rows) != rk["peserta_skb"] or pl_cnt != rk["lulus_akhir"]:
            mismatches.append((sec["page_rekap"], len(rows), rk["peserta_skb"], pl_cnt, rk["lulus_akhir"]))

    elapsed = round(time.time() - t0, 2)
    meta = {
        "instansi_kode": spec["instansi_kode"],
        "instansi_id_2024": spec["instansi_id_2024"],
        "instansi_nm": spec["instansi_nm"],
        "pdf_file": pdf_path.name,
        "pages": len(pages),
        "sections": len(sections),
        "parsed_rows": sum(len(s["rows"]) for s in sections),
        "expected_rows": sum((s["rekap"]["peserta_skb"] if s["rekap"] else 0) for s in sections),
        "parsed_pl": sum(sum(1 for r in s["rows"] if r["st"].startswith("P/L")) for s in sections),
        "expected_pl": sum((s["rekap"]["lulus_akhir"] if s["rekap"] else 0) for s in sections),
        "unmatched_buffers": len(unmatched),
        "math_errors": math_errs,
        "mismatched_sections": len(mismatches),
        "elapsed_s": elapsed,
        "sumber": spec["sumber"],
    }
    if unmatched:
        meta["sample_unmatched"] = unmatched[:3]
    if mismatches:
        meta["sample_mismatches"] = mismatches[:5]
    return sections, meta


def _pend_tokens(raw: str) -> set[str]:
    parts = re.split(r"[/|;]+", raw or "")
    return {_norm_key(p) for p in parts if _norm_key(p)}


def match_sections_to_2024_db(
    instansi_id_2024: int, sections: list[dict[str, Any]], conn: sqlite3.Connection
) -> tuple[int, int]:
    """Attach 1-to-1 matched cpns2024.db formasi_id onto each parsed section where possible."""
    db_rows = conn.execute(
        """
        SELECT formasi_id, jabatan_nm, lokasi_nm, jenis_formasi, COALESCE(jumlah_formasi, 0), pendidikan_raw
        FROM formasi
        WHERE instansi_id = ?
        """,
        (instansi_id_2024,),
    ).fetchall()

    candidates = []
    for fid, jab, lok, jf, k, pend in db_rows:
        candidates.append(
            {
                "formasi_id": fid,
                "jab_norm": _norm_key(jab),
                "lok_norm": _norm_key(lok),
                "jf_norm": _norm_key(jf),
                "kuota": int(k),
                "pend_set": _pend_tokens(pend),
            }
        )

    # Pre-index by jab_norm
    by_jab: dict[str, list[dict[str, Any]]] = {}
    for c in candidates:
        by_jab.setdefault(c["jab_norm"], []).append(c)

    # Score candidate pairs per section; assign greedily by highest score
    pairs: list[tuple[float, int, str]] = []
    for s_idx, sec in enumerate(sections):
        hdr = sec["header"]
        j_norm = _norm_key(hdr["jabatan_nm"])
        l_norm = _norm_key(hdr["lokasi_nm"])
        q = int(sec["rekap"]["jumlah_formasi"]) if sec["rekap"] else int(hdr["jumlah_formasi_header"] or 0)
        p_set = _pend_tokens(hdr["pendidikan_raw"])
        pool = by_jab.get(j_norm) or candidates
        for c in pool:
            if c["jab_norm"] != j_norm and pool is not candidates:
                continue
            score = 0.0
            if c["jab_norm"] == j_norm:
                score += 100.0
            if c["kuota"] == q:
                score += 30.0
            if p_set and c["pend_set"]:
                inter = len(p_set & c["pend_set"])
                union = len(p_set | c["pend_set"])
                score += 40.0 * (inter / union)
                if p_set == c["pend_set"]:
                    score += 15.0
            if l_norm and c["lok_norm"]:
                if l_norm == c["lok_norm"]:
                    score += 35.0
                elif c["lok_norm"] in l_norm or l_norm in c["lok_norm"]:
                    score += 18.0
                else:
                    lt1 = set(l_norm.split())
                    lt2 = set(c["lok_norm"].split())
                    if lt1 and lt2:
                        score += 12.0 * (len(lt1 & lt2) / len(lt1 | lt2))
            if score >= 100.0:
                pairs.append((score, s_idx, c["formasi_id"]))

    pairs.sort(key=lambda x: x[0], reverse=True)
    used_sec: set[int] = set()
    used_fid: set[str] = set()
    for score, s_idx, fid in pairs:
        if s_idx in used_sec or fid in used_fid:
            continue
        sections[s_idx]["formasi_id_2024"] = fid
        sections[s_idx]["match_score_2024"] = round(score, 2)
        used_sec.add(s_idx)
        used_fid.add(fid)

    return len(used_sec), len(db_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse CPNS 2024 score PDFs for 6 agencies.")
    parser.add_argument("--only", nargs="*", help="Filter instansi_kode (e.g. BSSN BPK)")
    args = parser.parse_args()

    wanted = {k.upper() for k in args.only} if args.only else None
    specs = [s for s in AGENCY_SPECS if not wanted or s["instansi_kode"] in wanted]

    conn = sqlite3.connect(f"file:{CPNS2024_DB_PATH}?mode=ro", uri=True)
    raw_sections_out: list[dict[str, Any]] = []
    summary_sections_out: list[dict[str, Any]] = []
    agency_meta: dict[str, Any] = {}

    try:
        for spec in specs:
            kode = spec["instansi_kode"]
            print(f"\n>>> Parsing {kode} ({spec['instansi_nm']}) ...", flush=True)
            sections, meta = parse_agency_pdf(spec)
            matched, db_total = match_sections_to_2024_db(spec["instansi_id_2024"], sections, conn)
            meta["db_matched_sections"] = matched
            meta["db_total_rows"] = db_total

            all_pl_na: list[float] = []
            all_pl_skd: list[int] = []
            all_pl_skb: list[float] = []
            all_skb_skd: list[int] = []

            for sec in sections:
                rows = sec["rows"]
                pl_rows = [r for r in rows if r["st"].startswith("P/L")]
                hadir_rows = [r for r in rows if r["st"] not in ("TH", "APS")]

                pl_na = [r["na"] for r in pl_rows]
                pl_skd = [r["skd"] for r in pl_rows]
                pl_skb = [r["skb"] for r in pl_rows]
                skb_skd = [r["skd"] for r in rows]
                all_pl_na.extend(pl_na)
                all_pl_skd.extend(pl_skd)
                all_pl_skb.extend(pl_skb)
                all_skb_skd.extend(skb_skd)

                rk = sec["rekap"] or {}
                hdr = sec["header"]
                rec_base = {
                    "instansi_kode": kode,
                    "instansi_id_2024": spec["instansi_id_2024"],
                    "formasi_id_2024": sec.get("formasi_id_2024"),
                    "page_rekap": sec["page_rekap"],
                    "jab_kode": hdr["jab_kode"],
                    "jabatan_nm": hdr["jabatan_nm"],
                    "lok_kode": hdr["lok_kode"],
                    "lokasi_nm": hdr["lokasi_nm"],
                    "jenis_formasi": hdr["jenis_formasi"],
                    "pendidikan_raw": hdr["pendidikan_raw"],
                    "jumlah_formasi": rk.get("jumlah_formasi"),
                    "peserta_skb": rk.get("peserta_skb"),
                    "hadir_skb": rk.get("hadir"),
                    "n_lulus": len(pl_rows),
                    "nilai_akhir_lulus": compute_stats(pl_na),
                    "skd_lulus": compute_stats([float(x) for x in pl_skd]),
                    "skb_lulus": compute_stats(pl_skb),
                    "skd_peserta_skb": compute_stats([float(x) for x in skb_skd]),
                    "sumber": spec["sumber"],
                }
                summary_sections_out.append(rec_base)
                raw_sections_out.append(
                    {
                        **rec_base,
                        "pl_na": pl_na,
                        "pl_skd": pl_skd,
                        "pl_skb": pl_skb,
                        "skb_skd": skb_skd,
                    }
                )

            meta["overall_nilai_akhir_lulus"] = compute_stats(all_pl_na)
            meta["overall_skd_lulus"] = compute_stats([float(x) for x in all_pl_skd])
            meta["overall_skd_skb"] = compute_stats([float(x) for x in all_skb_skd])
            agency_meta[kode] = meta
            print(
                f"  Done {kode} in {meta['elapsed_s']}s | sec={meta['sections']} | "
                f"rows={meta['parsed_rows']}/{meta['expected_rows']} | PL={meta['parsed_pl']}/{meta['expected_pl']} | "
                f"unm={meta['unmatched_buffers']} math_err={meta['math_errors']} mismatch={meta['mismatched_sections']} | "
                f"db_match={matched}/{db_total}",
                flush=True,
            )
            if meta.get("sample_mismatches") or meta.get("sample_unmatched"):
                print("  WARNING:", meta.get("sample_mismatches"), meta.get("sample_unmatched"), flush=True)
    finally:
        conn.close()

    if not wanted:
        RAW_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_OUT_PATH.write_text(
            json.dumps({"agencies": agency_meta, "sections": raw_sections_out}, ensure_ascii=False),
            encoding="utf-8",
        )
        SUMMARY_OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_OUT_PATH.write_text(
            json.dumps({"agencies": agency_meta, "sections": summary_sections_out}, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nSaved raw: {RAW_OUT_PATH} ({RAW_OUT_PATH.stat().st_size:,} B)")
        print(f"Saved summary: {SUMMARY_OUT_PATH} ({SUMMARY_OUT_PATH.stat().st_size:,} B)")


if __name__ == "__main__":
    main()
