#!/usr/bin/env python3
r"""
Generalized CPNS 2024 SKD-SKB score parser across all harvested agencies
(Pusat, Provinsi, Kabupaten/Kota), writing:
  1. Per-agency checkpoints in D:\AG Files\cpns2026-scraper\data\parsed\per_agency\
  2. Full raw dataset D:\AG Files\cpns2026-scraper\data\parsed\scores_2024_all_raw.json
  3. Indexed SQLite tables (formasi_scores_2024 + scores_2024_sources) inside cpns2024.db
     and lightweight agency summary data\scores_2024_summary.json

Supports:
- Panselnas BKN Ringkas & mixed Ringkas+Rincian PDFs (incl. multi-page Pendidikan wraps)
- Panselnas BKN Rincian PDFs (re-assembling candidates split across page breaks)
- Partial/truncated BKN Ringkas PDFs (zlib stream recovery for Kementan, verified strictly)
- Custom tabular CPNS score announcements (Kab. Merangin)
- Strict candidate arithmetic validation (TWK+TIU+TKP=Total, SKD40+SKB60=NilaiAkhir)
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import sys
import time
import zlib
from typing import Any

try:
    import pypdfium2 as pdfium
except ImportError:  # pragma: no cover - optional for pure-text unit tests
    pdfium = None  # type: ignore[assignment]

BASE_DIR = Path(__file__).resolve().parent.parent
DB_2024_PATH = BASE_DIR / "data" / "cpns2024.db"
SCORES_ROOT = Path(r"D:\AG Files\cpns2026-scraper\data\refs\scores_2024")
PARSED_DIR = Path(r"D:\AG Files\cpns2026-scraper\data\parsed")
PER_AGENCY_DIR = PARSED_DIR / "per_agency"
RAW_ALL_OUT = PARSED_DIR / "scores_2024_all_raw.json"
SUMMARY_ALL_OUT = BASE_DIR / "data" / "scores_2024_summary.json"
LEGACY_JSON_OUT = BASE_DIR / "data" / "scores_2024_6instansi.json"

CAT_SUBDIR = {"Pusat": "pusat", "Provinsi": "provinsi", "Kabupaten/Kota": "kabkota"}

# Preserve exact Phase-1 short kode_instansi & curated official announcement labels
PHASE1_LEGACY_CODES: dict[int, tuple[str, str, str, str]] = {
    111: (
        "BSSN",
        "bssn",
        "4010_HASIL-RINGKAS-CPNS-BSSN-2024.pdf",
        "PENG.3 & PENG.5/BSSN/SU/KP.02.01/01/2025 (Pasca Sanggah: 0 sanggahan diterima)",
    ),
    2: (
        "KEJAGUNG",
        "kejagung",
        "HASIL_INTEGRASI_SKD_SKB_LAMPIRAN_I_RINGKAS.pdf",
        "Lampiran I Ringkas Hasil Integrasi SKD-SKB Kejaksaan Agung TA 2024",
    ),
    4: (
        "BPKP",
        "bpkp",
        "20250107220401_Lampiran_I.pdf",
        "KP.00.01/PENG-1 & PENG-2/SU/02/2025 (Pasca Sanggah: 0 dari 128 sanggahan diterima)",
    ),
    10: (
        "KEMENKEU",
        "kemenkeu",
        "0e5a6b92-6bc9-4ad7-b865-0b67a5338ed0.pdf",
        "PENG-08/PANREK/2025 (Pasca Pembatalan & Penggantian Kelulusan, 14 Mar 2025)",
    ),
    11: (
        "KEMENKES",
        "kemenkes",
        "Lampiran_I_Ringkasan_hasil_Integrasi_SKD_dan_SKB.pdf",
        "KP.01.02/A/78/2025 Lampiran I Ringkasan Hasil Integrasi SKD-SKB (Pra-Sanggah 9 Jan 2025)",
    ),
    102: (
        "BPK",
        "bpk",
        "Lampiran-Rekap-Hasil-Integrasi-SKD-dan-SKB-Rincian-_0.pdf",
        "2/S.Peng/X/01/2025 & 3/S.Peng/X/01/2025 (Pasca Sanggah: 0 sanggahan diterima)",
    ),
}

STATUS_RE_STR = r"(P/L(?:-[A-Z0-9]+)?|U-[123]|E-[123]|L(?:-[A-Z0-9]+)?|TL|TH|TMS(?:-\d+)?|APS)"
STATUS_EXACT_RE = re.compile(rf"^{STATUS_RE_STR}$")
PESERTA_RE = re.compile(r"\b(24\d{15})\b")


def is_lulus_status(st: str) -> bool:
    u = st.upper()
    return u.startswith("P/L") or u.startswith("U-") or u.startswith("E-") or u == "L" or u.startswith("L-")


def _to_float(tok: str) -> float:
    return float(tok.replace(",", "."))


def compute_stats(values: list[float] | list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None, "mean": None}
    s = sorted(float(v) for v in values)
    n = len(s)
    if n >= 2:
        try:
            q = statistics.quantiles(s, n=4, method="inclusive")
            p25, med, p75 = q[0], q[1], q[2]
        except Exception:
            p25 = med = p75 = statistics.median(s)
    else:
        p25 = med = p75 = s[0]
    return {
        "n": n,
        "min": round(s[0], 3),
        "p25": round(p25, 3),
        "median": round(med, 3),
        "p75": round(p75, 3),
        "max": round(s[-1], 3),
        "mean": round(sum(s) / n, 3),
    }


def _extract_pdf_chunk(args: tuple[str, int, int]) -> list[str]:
    path_str, start, end = args
    doc = pdfium.PdfDocument(path_str)
    out = [doc[i].get_textpage().get_text_range() for i in range(start, end)]
    doc.close()
    return out


def extract_pdf_pages_fast(pdf_path: Path, workers: int = 6) -> list[str]:
    doc = pdfium.PdfDocument(str(pdf_path))
    n = len(doc)
    doc.close()
    if n < 150 or workers <= 1:
        return _extract_pdf_chunk((str(pdf_path), 0, n))
    chunk = max(60, (n + workers - 1) // workers)
    tasks = [(str(pdf_path), i, min(n, i + chunk)) for i in range(0, n, chunk)]
    pages: list[str] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(_extract_pdf_chunk, tasks):
            pages.extend(res)
    return pages


def _unescape_pdf_str(raw: bytes) -> str:
    # Handle PDF literal escapes \(, \), \\, octal \ddd
    s = raw.decode("latin-1", errors="ignore")
    s = re.sub(r"\\([0-7]{1,3})", lambda m: chr(int(m.group(1), 8)), s)
    return s.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\").replace(r"\r", " ").replace(r"\n", " ")


def extract_zlib_stream_pages(pdf_path: Path) -> list[str]:
    """Recover intact PDFium text pages directly from zlib content streams in truncated PDFs."""
    raw = pdf_path.read_bytes()
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S)
    pages: list[str] = []
    token_re = re.compile(
        rb"\b(BT)\b|"
        rb"([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+Td\b|"
        rb"(?:[-+]?\d+(?:\.\d+)?\s+){4}([-+]?\d+(?:\.\d+)?)\s+([-+]?\d+(?:\.\d+)?)\s+Tm\b|"
        rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*Tj\b|"
        rb"\[([^\]]+)\]\s*TJ\b"
    )
    for st in streams:
        try:
            dec = zlib.decompress(st)
        except Exception:
            continue
        if b"PANITIA SELEKSI NASIONAL" not in dec and b"REKAP HASIL" not in dec and b"243006" not in dec:
            continue
        cur_x = 0.0
        cur_y = 0.0
        out_lines: list[str] = []
        cur_line: list[str] = []
        last_y: float | None = None
        for m in token_re.finditer(dec):
            if m.group(1) is not None:
                cur_x = 0.0
                cur_y = 0.0
            elif m.group(2) is not None:
                cur_x += float(m.group(2))
                cur_y += float(m.group(3))
            elif m.group(4) is not None:
                cur_x = float(m.group(4))
                cur_y = float(m.group(5))
            else:
                if m.group(6) is not None:
                    txt = _unescape_pdf_str(m.group(6)).strip()
                else:
                    parts = [_unescape_pdf_str(p) for p in re.findall(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)", m.group(7))]
                    txt = "".join(parts).strip()
                if txt:
                    if last_y is not None and abs(cur_y - last_y) > 2.5 and cur_line:
                        out_lines.append(" ".join(cur_line))
                        cur_line = []
                    cur_line.append(txt)
                    last_y = cur_y
        if cur_line:
            out_lines.append(" ".join(cur_line))
        page_txt = "\n".join(out_lines)
        if page_txt.strip():
            pages.append(page_txt)
    return pages


def _clean_hdr_tail(text: str) -> str:
    """Strip trailing table labels (: - Kode Jumlah) left by zlib/PDFium splits."""
    s = " ".join(text.split())
    s = re.sub(r"(?:\s+(?:[:\-]+|Kode|Jumlah))+$", "", s, flags=re.I).strip()
    s = re.sub(r"\s*[:\-]+\s*$", "", s).strip()
    return s


def parse_rekap_header_v2(page_txt: str) -> dict[str, Any]:
    hdr: dict[str, Any] = {
        "jab_kode": None,
        "jabatan_nm": None,
        "jabatan_qty": None,
        "instansi_kode_pdf": None,
        "lok_kode": None,
        "lokasi_nm": None,
        "lok_qty": None,
        "jf_kode": None,
        "jenis_formasi": None,
        "jf_qty": None,
        "pendidikan_raw": None,
        "jumlah_formasi_header": None,
    }
    page_txt = re.sub(r"(?m)^.*Laporan digenerate secara otomatis[^\r\n]*$", "", page_txt)
    lines = [" ".join(ln.split()) for ln in page_txt.splitlines() if ln.strip()]

    # Handle wrapped Jabatan Formasi between "Jabatan Formasi" and "Instansi" (or Lokasi/Jenis/Pendidikan)
    m_jblk = re.search(r"Jabatan Formasi\s*(.*?)(?=\b(?:Instansi|Lokasi Formasi|Jenis Formasi|Pendidikan)\b|\Z)", page_txt, re.S)
    if m_jblk:
        jlines = [
            " ".join(x.split())
            for x in m_jblk.group(1).splitlines()
            if x.strip() and x.strip() not in ("Kode", "Jumlah", "Kode Jumlah", ":", "-")
        ]
        joined_j = _clean_hdr_tail(re.sub(r"^\s*[:\-]+\s*", "", " ".join(jlines)))
        # Rejoin hyphenated sub-codes split across PDF lines (e.g. "JF0018704- 1101" -> "JF0018704-1101")
        joined_j = re.sub(r"\b([A-Z]{1,4}\d+)-\s+(\d+)\b", r"\1-\2", joined_j)
        m_j = re.match(r"^([A-Z]{1,4}\d+(?:-\d+)*)\s*(.*)$", joined_j)
        if m_j:
            hdr["jab_kode"] = m_j.group(1).strip()
            tail = _clean_hdr_tail(re.sub(r"^[\s:\-]+", "", m_j.group(2)))
            m_qty = re.search(r"^(.*?)\s+(\d+)\s*$", tail)
            if m_qty:
                hdr["jabatan_nm"] = _clean_hdr_tail(m_qty.group(1))
                hdr["jabatan_qty"] = int(m_qty.group(2))
            else:
                hdr["jabatan_nm"] = tail

    m_ins = re.search(r"Instansi\s*:?\s*(\d{3,5})\s*(?:-|\s)\s*([^\r\n]+)", page_txt)
    if m_ins:
        hdr["instansi_kode_pdf"] = m_ins.group(1).strip()

    # Handle Lokasi Formasi: wrapped text above/after CODE, wrapped Instansi lines, and BNPT order (Instansi before Jabatan)
    m_iblk = re.search(r"Instansi\b(.*?)(?=\bJenis Formasi\b|\Z)", page_txt, re.S)
    if m_iblk:
        raw_blk = m_iblk.group(1)
        # If Instansi appeared above Jabatan Formasi (e.g. BNPT), narrow slice from "Lokasi Formasi" (or after Jabatan line)
        m_jf_in_blk = re.search(r"\bJabatan Formasi\b[^\r\n]*\r?\n", raw_blk)
        if m_jf_in_blk and "Lokasi Formasi" in raw_blk[m_jf_in_blk.end() :]:
            raw_blk = raw_blk[m_jf_in_blk.end() :]
        blk_lines = [" ".join(x.split()) for x in raw_blk.splitlines() if x.strip()]
        rest_lines: list[str] = []
        past_instansi_hdr = False
        for ln in blk_lines:
            if not past_instansi_hdr:
                if ln in (":", "-", "Kode", "Jumlah", "Kode Jumlah") or re.fullmatch(r"\d{3,5}", ln):
                    continue
                if re.match(r"^:?\s*\d{3,5}\s*-\s*.*$", ln):
                    # Check if line has a qty at end; if NOT, next line might be wrapped agency suffix (e.g. "Kreatif - 395")
                    past_instansi_hdr = True
                    continue
                m_zins = re.match(r"^:?\s*\d{3,5}\s+([^|\r\n]+?)(?:\s+\d+\s*[:\- ]*)?$", ln)
                if m_zins:
                    past_instansi_hdr = True
                    continue
                if "|" not in ln and not re.search(r"Lokasi Formasi|\d{6,}", ln):
                    past_instansi_hdr = True
                    continue
                past_instansi_hdr = True
            # Skip wrapped Instansi continuation line like "Kreatif - 395" / "Kreatif 395" before "|" or "Lokasi Formasi"
            if not rest_lines and "|" not in ln and "Lokasi Formasi" not in ln and not re.search(r"\d{6,}", ln) and re.search(r"\s-\s*\d+$", ln):
                continue
            ln_clean = re.sub(r"^:?\s*\d{3,5}\s+[^|]+\s+\d+\s*:\s*-\s*", "", ln)
            rest_lines.append(ln_clean)

        rest_joined = " ".join(rest_lines)
        m_lk = re.search(r"\b(\d{6,10})\b", rest_joined)
        if m_lk:
            hdr["lok_kode"] = m_lk.group(1)
            rest_joined = rest_joined[: m_lk.start()] + " " + rest_joined[m_lk.end() :]

        cleaned_l = re.sub(r"\bLokasi Formasi\b", " ", rest_joined)
        cleaned_l = re.sub(r"(?:^|\s)[:\-]+(?:\s|$)", " ", cleaned_l)
        cleaned_l = _clean_hdr_tail(cleaned_l)
        toks = cleaned_l.split()
        # Peel AT MOST ONE leading/trailing qty token (preserves "ZONA 1", "SDN Panggung 4")
        if toks and toks[0].isdigit():
            hdr["lok_qty"] = int(toks.pop(0))
        if toks and toks[-1].isdigit():
            hdr["lok_qty"] = int(toks.pop())
        hdr["lokasi_nm"] = _clean_hdr_tail(" ".join(toks))

    # Fallback regex if Instansi..Jenis block didn't resolve lokasi_nm
    if not hdr["lokasi_nm"]:
        for idx, ln in enumerate(lines):
            m_lok = re.match(r"^(.*?)\bLokasi Formasi\s*:?\s*(\d+)\s*-\s*(.*)$", ln)
            if m_lok:
                hdr["lok_kode"] = m_lok.group(2).strip()
                hdr["lokasi_nm"] = _clean_hdr_tail(m_lok.group(3).strip() or m_lok.group(1).strip())
                break

    m_jf = re.search(
        r"Jenis Formasi\s*(.*?)(?=\b(?:Pendidikan|REKAP HASIL INTEGRASI|Jumlah\s+Peserta|Laporan digenerate)\b|\Z)",
        page_txt,
        re.S,
    )
    if m_jf:
        jfl = [
            " ".join(x.split())
            for x in m_jf.group(1).splitlines()
            if x.strip() and x.strip() not in (":", "-")
        ]
        tail_jf = _clean_hdr_tail(re.sub(r"^\s*:\s*", "", " ".join(jfl)))
        m_jfp = re.match(r"^([A-Z0-9]+)\s*[:-]?\s*(.*)$", tail_jf)
        if m_jfp:
            hdr["jf_kode"] = m_jfp.group(1).strip()
            tail = _clean_hdr_tail(re.sub(r"^[\s:\-]+", "", m_jfp.group(2)))
            m_qty = re.search(r"^(.*?)\s+(\d+)\s*$", tail)
            if m_qty:
                hdr["jenis_formasi"] = _clean_hdr_tail(m_qty.group(1))
                hdr["jf_qty"] = int(m_qty.group(2))
            else:
                hdr["jenis_formasi"] = tail

    m_pend = re.search(
        r"Pendidikan\s*:?\s*(.*?)(?=\s*REKAP HASIL INTEGRASI|\s*HASIL INTEGRASI|\s*Laporan digenerate|\Z)",
        page_txt,
        re.S,
    )
    if m_pend:
        raw_p = " ".join(m_pend.group(1).split()).strip()
        raw_p = re.sub(r"^(?:\d+\s+|[:\-]+\s+)+", "", raw_p)
        m_pqty = re.search(r"^(.*?)\s+(\d+)\s*$", raw_p)
        if m_pqty:
            hdr["pendidikan_raw"] = m_pqty.group(1).strip()
            hdr["jumlah_formasi_header"] = int(m_pqty.group(2))
        else:
            hdr["pendidikan_raw"] = raw_p
            hdr["jumlah_formasi_header"] = hdr["jf_qty"]

    if hdr["jumlah_formasi_header"] is None:
        hdr["jumlah_formasi_header"] = hdr["jf_qty"] or hdr["lok_qty"] or hdr["jabatan_qty"]

    return hdr


def parse_rekap_counts_v2(page_txt: str, require_marker: bool = True) -> dict[str, int] | None:
    pos = page_txt.find("REKAP HASIL INTEGRASI")
    if pos == -1:
        if require_marker:
            return None
        sub = page_txt
    else:
        sub = page_txt[pos:]
    lines = [" ".join(ln.split()) for ln in sub.splitlines() if ln.strip()]

    # Pattern A: "1 2 3 4 5 6 7 10" followed by 8 ints -> col[7] is Lulus Akhir (col 10)
    for idx, ln in enumerate(lines):
        if re.fullmatch(r"1\s+2\s+3\s+4\s+5\s+6\s+7\s+10", ln) and idx + 1 < len(lines):
            nums = [int(x) for x in re.findall(r"\b\d+\b", lines[idx + 1])]
            if len(nums) == 8:
                return {
                    "peserta_skb": nums[0],
                    "jumlah_formasi": nums[1],
                    "metode_skb": nums[2],
                    "hadir": nums[3],
                    "th": nums[4],
                    "tl": nums[5],
                    "tms": nums[6],
                    "tms_1": 0,
                    "aps": 0,
                    "lulus_akhir": nums[7],
                }
        # Pattern B: "1 2 3 4 5 6 7 8 9 10" followed by 10 ints
        if re.fullmatch(r"1\s+2\s+3\s+4\s+5\s+6\s+7\s+8\s+9\s+10", ln) and idx + 1 < len(lines):
            nums = [int(x) for x in re.findall(r"\b\d+\b", lines[idx + 1])]
            if len(nums) == 10:
                return {
                    "peserta_skb": nums[0],
                    "jumlah_formasi": nums[1],
                    "metode_skb": nums[2],
                    "hadir": nums[3],
                    "th": nums[4],
                    "tl": nums[5],
                    "tms": nums[6],
                    "tms_1": nums[7],
                    "aps": nums[8],
                    "lulus_akhir": nums[9],
                }

    # Pattern C: fallback search for standalone 8-int or 10-int data line after header labels
    for ln in lines:
        if re.fullmatch(r"(?:\d+\s+){7}\d+", ln):
            nums = [int(x) for x in ln.split()]
            if nums != [1, 2, 3, 4, 5, 6, 7, 10] and nums[0] == nums[3] + nums[4]:
                return {
                    "peserta_skb": nums[0],
                    "jumlah_formasi": nums[1],
                    "metode_skb": nums[2],
                    "hadir": nums[3],
                    "th": nums[4],
                    "tl": nums[5],
                    "tms": nums[6],
                    "tms_1": 0,
                    "aps": 0,
                    "lulus_akhir": nums[7],
                }
        if re.fullmatch(r"(?:\d+\s+){9}\d+", ln):
            nums = [int(x) for x in ln.split()]
            if nums != list(range(1, 11)) and nums[0] == nums[3] + nums[4]:
                return {
                    "peserta_skb": nums[0],
                    "jumlah_formasi": nums[1],
                    "metode_skb": nums[2],
                    "hadir": nums[3],
                    "th": nums[4],
                    "tl": nums[5],
                    "tms": nums[6],
                    "tms_1": nums[7],
                    "aps": nums[8],
                    "lulus_akhir": nums[9],
                }
    return None


def _valid_scores(
    twk: int, tiu: int, tkp: int, total_skd: int, skd40: float, skb_val: float, skb60: float, na: float
) -> bool:
    if not (0 <= twk <= 150 and 0 <= tiu <= 175 and 0 <= tkp <= 225 and 0 <= total_skd <= 550):
        return False
    if twk + tiu + tkp != total_skd:
        return False
    if abs((total_skd / 5.5) * 0.40 - skd40) > 0.08:
        return False
    if not (0.0 <= skb_val <= 100.05):
        return False
    if abs(skb_val * 0.60 - skb60) > 0.08:
        return False
    if abs((skd40 + skb60) - na) > 0.08:
        return False
    if not (0.0 <= na <= 100.05):
        return False
    return True


def _strip_bkn_page_chrome(page_txt: str) -> str:
    # Remove single-line "Laporan digenerate..." footer (even if PDFium emits it mid-page!) and top banner chrome.
    txt = re.sub(r"(?m)^.*Laporan digenerate secara otomatis[^\r\n]*$", "", page_txt)
    lines = txt.splitlines()
    out: list[str] = []
    in_banner = False
    for ln in lines:
        s = ln.strip()
        if "PANITIA SELEKSI NASIONAL PENGADAAN CASN" in s:
            in_banner = True
            continue
        if in_banner:
            if re.match(r"^Halaman\s+\d+\s+dari\s+\d+\s+halaman$", s):
                in_banner = False
                continue
            if s.startswith("1.") or PESERTA_RE.search(s):
                # Reached candidate data directly
                in_banner = False
                out.append(ln)
                continue
            continue
        out.append(ln)
    return "\n".join(out)


def _match_ringkas_tail(nums: list[float]) -> tuple[int, float, float, float] | None:
    """Validate last 8 or 9 or 5 numeric tokens of a Ringkas candidate block."""
    # Try 8 tokens ending row: TWK, TIU, TKP, TOT, SKD40, SKB, SKB60, NA
    if len(nums) >= 8:
        t = nums[-8:]
        if all(float(x).is_integer() for x in t[:4]):
            twk, tiu, tkp, tot = int(t[0]), int(t[1]), int(t[2]), int(t[3])
            skd40, skb_val, skb60, na = t[4], t[5], t[6], t[7]
            if _valid_scores(twk, tiu, tkp, tot, skd40, skb_val, skb60, na):
                return tot, skd40, skb_val, na
    # Try 9 tokens ending row: TWK, TIU, TKP, TOT, SKD100, SKD40, SKB, SKB60, NA
    if len(nums) >= 9:
        t = nums[-9:]
        if all(float(x).is_integer() for x in t[:4]):
            twk, tiu, tkp, tot = int(t[0]), int(t[1]), int(t[2]), int(t[3])
            skd40, skb_val, skb60, na = t[5], t[6], t[7], t[8]
            if _valid_scores(twk, tiu, tkp, tot, skd40, skb_val, skb60, na):
                return tot, skd40, skb_val, na
    # Try 5 tokens compact row: TWK, TIU, TKP, SKB, NA
    if len(nums) >= 5:
        t = nums[-5:]
        if all(float(x).is_integer() for x in t[:3]):
            twk, tiu, tkp = int(t[0]), int(t[1]), int(t[2])
            tot = twk + tiu + tkp
            skd40 = round((tot / 5.5) * 0.40, 3)
            skb_val = t[3]
            skb60 = round(skb_val * 0.60, 3)
            na = t[4]
            if _valid_scores(twk, tiu, tkp, tot, skd40, skb_val, skb60, na):
                return tot, skd40, skb_val, na
    return None


def extract_candidates_ringkas(section_text: str) -> tuple[list[dict[str, Any]], int]:
    """Extract & arithmetically verify candidates from BKN Ringkas pages."""
    anchors = list(PESERTA_RE.finditer(section_text))
    candidates: list[dict[str, Any]] = []
    failures = 0
    seen_ids: set[str] = set()
    tail_re = re.compile(rf"(.*?)\b{STATUS_RE_STR}\b", re.S)

    for idx, m in enumerate(anchors):
        pid = m.group(1)
        if pid in seen_ids:
            continue
        start = m.end()
        end = anchors[idx + 1].start() if idx + 1 < len(anchors) else len(section_text)
        chunk = section_text[start:end]
        # Candidate score tail sits up to the status token (before next candidate row or trailing junk)
        best: tuple[int, float, float, float, str] | None = None
        for sm in tail_re.finditer(chunk):
            status = sm.group(2)
            head_txt = sm.group(1)
            # Remove dates & header "(1) (14) (15)" fragments only if failing, first parse all standalone numeric tokens
            toks = re.findall(r"(?<![A-Za-z\d./-])\d+(?:[.,]\d+)?(?![A-Za-z\d./-])", head_txt)
            if not toks:
                continue
            nums = [_to_float(x) for x in toks[-12:]]
            matched = _match_ringkas_tail(nums)
            if matched:
                tot, skd40, skb_val, na = matched
                best = (tot, skd40, skb_val, na, status)
                break
        if best is None:
            failures += 1
            continue
        seen_ids.add(pid)
        tot, skd40, skb_val, na, status = best
        candidates.append(
            {
                "no_peserta": pid,
                "total_skd": tot,
                "skor_skd": skd40,
                "nilai_skb": skb_val,
                "nilai_akhir": na,
                "status": status,
                "is_lulus": is_lulus_status(status),
            }
        )
    return candidates, failures


def _parse_single_rincian_block(pid: str, raw_chunk: str) -> dict[str, Any] | None:
    """Parse one BKN Rincian candidate detail block using TIU/TKP/SKB anchors + strict math."""
    cut = raw_chunk.find("Skala 100")
    primary = raw_chunk[:cut] if cut != -1 else raw_chunk

    for block in (primary, raw_chunk) if cut != -1 else (primary,):
        m_tiu = re.search(r"2\.\s*Tes Intelegensi Umum\s*\(TIU\)\s+(\d+)\s+(\d+(?:[.,]\d+)?)", block)
        m_tkp = re.search(r"3\.\s*Tes Karakteristik Pribadi\s*\(TKP\)\s+(\d+)", block)
        if not m_tiu or not m_tkp:
            continue
        tiu = int(m_tiu.group(1))
        skd_100 = _to_float(m_tiu.group(2))
        tkp = int(m_tkp.group(1))

        # Expected total_skd is around round(skd_100 * 5.5); find exact integer pair (twk, tot) in block
        ints_in_block = [int(x) for x in re.findall(r"(?<![\d.,/%-])\b\d{1,3}\b(?![\d.,/%-])", block)]
        exp_tot = round(skd_100 * 5.5)
        twk_tot: tuple[int, int] | None = None
        for tot_cand in (exp_tot, exp_tot - 1, exp_tot + 1):
            twk_cand = tot_cand - tiu - tkp
            if 0 <= twk_cand <= 150 and twk_cand in ints_in_block and tot_cand in ints_in_block:
                if abs(tot_cand / 5.5 - skd_100) <= 0.08:
                    twk_tot = (twk_cand, tot_cand)
                    break
        if twk_tot is None:
            continue
        twk, total_skd = twk_tot

        # Status sits after SKB subtotal/skb60 and before trailing footer
        m_skb_hdr = re.search(r"Seleksi Kompetensi Bidang\s*\(SKB\)\s*-\s*60%\s*(.*)", block, re.S)
        if not m_skb_hdr:
            continue
        skb_part = m_skb_hdr.group(1)
        m_ket = re.search(rf"\b{STATUS_RE_STR}\b", skb_part)
        if not m_ket:
            continue
        status = m_ket.group(1)

        # Floats between TKP and SKB header give skd40 and optional nilai_akhir
        between = block[m_tkp.end() : m_skb_hdr.start()]
        bet_floats = [_to_float(x) for x in re.findall(r"\b\d+[.,]\d+\b", between)]
        skd40_exp = round((total_skd / 5.5) * 0.40, 3)
        skd40 = next((f for f in bet_floats if abs(f - skd40_exp) <= 0.08), skd40_exp)

        # Look for SKB subtotal & skb60 right before status in skb_part[:m_ket.start()]
        pre_ket = skb_part[: m_ket.start()]
        # Remove percentage annotations like "50 %" so floats are clean scores
        pre_ket_clean = re.sub(r"\d+(?:[.,]\d+)?\s*%", " ", pre_ket)
        skb_floats = [_to_float(x) for x in re.findall(r"\b\d+[.,]\d+\b", pre_ket_clean)]

        # Also candidate nilai_akhir can be right on "SKB - 60% <NA>" or in bet_floats[-1]
        na_candidates = [f for f in bet_floats if abs(f - skd40) > 0.001 or f == skd40]
        m_na_inline = re.match(r"^(\d+[.,]\d+)\b", skb_part.lstrip())
        if m_na_inline:
            na_candidates.insert(0, _to_float(m_na_inline.group(1)))

        # Try pairs (skb_val, skb60) from the tail of skb_floats
        found = None
        if len(skb_floats) >= 2:
            for i in range(len(skb_floats) - 1):
                sv, s60 = skb_floats[i], skb_floats[i + 1]
                if 0.0 <= sv <= 100.05 and abs(sv * 0.60 - s60) <= 0.08:
                    # Prefer trailing pair (subtotal + skb60) over sub-component line matches
                    na_calc = round(skd40 + s60, 3)
                    na_picked = next((nc for nc in na_candidates if abs(nc - na_calc) <= 0.08), na_calc)
                    if _valid_scores(twk, tiu, tkp, total_skd, skd40, sv, s60, na_picked):
                        found = (sv, na_picked)
        # Fallback if SKB had integer-only 0 or missing float
        if found is None and status == "TH":
            found = (0.0, skd40)

        if found is not None:
            skb_val, na = found
            return {
                "no_peserta": pid,
                "total_skd": total_skd,
                "skor_skd": round(skd40, 3),
                "nilai_skb": round(skb_val, 3),
                "nilai_akhir": round(na, 3),
                "status": status,
                "is_lulus": is_lulus_status(status),
            }
    return None


def extract_candidates_rincian(section_text: str) -> tuple[list[dict[str, Any]], int]:
    anchors = list(PESERTA_RE.finditer(section_text))
    candidates: list[dict[str, Any]] = []
    failures = 0
    seen_ids: set[str] = set()
    for idx, m in enumerate(anchors):
        pid = m.group(1)
        if pid in seen_ids:
            continue
        start = m.end()
        end = anchors[idx + 1].start() if idx + 1 < len(anchors) else len(section_text)
        parsed = _parse_single_rincian_block(pid, section_text[start:end])
        if parsed is None:
            failures += 1
        else:
            seen_ids.add(pid)
            candidates.append(parsed)
    return candidates, failures


def parse_bkn_pages(pages: list[str], allow_mode: str = "all") -> dict[str, Any]:
    """Group Panselnas REKAP + candidate pages into sections and compute verified stats."""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    total_failures = 0

    def _flush() -> None:
        nonlocal total_failures
        if current is None:
            return
        full_cand_txt = "\n".join(current["cand_chunks"])
        if current["mode"] == "rincian":
            cands, fail = extract_candidates_rincian(full_cand_txt)
        else:
            cands, fail = extract_candidates_ringkas(full_cand_txt)
        total_failures += fail
        current["candidates"] = cands
        current["cand_failures"] = fail
        del current["cand_chunks"]
        sections.append(current)

    for page_idx, raw_txt in enumerate(pages):
        up = raw_txt.upper()
        if "PENGADAAN PPPK" in up and "PENGADAAN CPNS" not in up and "CALON PEGAWAI NEGERI SIPIL" not in up:
            continue

        if "REKAP HASIL INTEGRASI" in raw_txt:
            mode = "rincian" if "(RINCIAN)" in raw_txt else "ringkas"
            _flush()
            hdr = parse_rekap_header_v2(raw_txt)
            cnts = parse_rekap_counts_v2(raw_txt)
            current = {
                "page_rekap": page_idx + 1,
                "mode": mode,
                "hdr": hdr,
                "counts": cnts,
                "cand_chunks": [],
                "header_done": cnts is not None,
            }
            continue

        if current is None:
            continue

        # Multi-page Pendidikan/REKAP continuation (e.g., BRIN pages 5..9) before candidates start
        if not current["header_done"] and not PESERTA_RE.search(raw_txt):
            if "Pendidikan" in raw_txt and current["hdr"].get("pendidikan_raw") is not None:
                m_p = re.search(r"Pendidikan\s*:?\s*(.*)$", raw_txt, re.S)
                if m_p:
                    extra = " ".join(m_p.group(1).split())
                    m_q = re.search(r"^(.*?)\s+(\d+)\s*$", extra)
                    if m_q:
                        current["hdr"]["pendidikan_raw"] += " " + m_q.group(1).strip()
                        if current["hdr"]["jumlah_formasi_header"] is None:
                            current["hdr"]["jumlah_formasi_header"] = int(m_q.group(2))
                    else:
                        current["hdr"]["pendidikan_raw"] += " " + extra
            c2 = parse_rekap_counts_v2(raw_txt, require_marker=False)
            if c2:
                current["counts"] = c2
                current["header_done"] = True
            continue

        if "PANITIA SELEKSI NASIONAL PENGADAAN CASN" not in raw_txt and "HASIL INTEGRASI" not in raw_txt:
            # Exited Panselnas report into appended regional summary / pass-list pages; close active section.
            _flush()
            current = None
            continue

        if "HASIL INTEGRASI" in raw_txt or PESERTA_RE.search(raw_txt):
            current["header_done"] = True
            cleaned = _strip_bkn_page_chrome(raw_txt)
            if cleaned.strip():
                current["cand_chunks"].append(cleaned)

    _flush()

    # In mixed PDFs (Ringkas followed by Rincian), keep unique (jab_kode, lok_kode, jf_kode), preferring Ringkas
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    ordered_keys: list[tuple[str, str, str]] = []
    for sec in sections:
        hdr = sec["hdr"]
        if not hdr.get("jabatan_nm"):
            continue
        if allow_mode == "ringkas" and sec["mode"] == "rincian":
            continue
        if allow_mode == "rincian" and sec["mode"] == "ringkas":
            continue
        pend_key = re.sub(r"\s+", " ", (hdr.get("pendidikan_raw") or "")).strip().upper()[:180]
        key = (
            hdr.get("jab_kode") or hdr["jabatan_nm"],
            hdr.get("lok_kode") or (hdr.get("lokasi_nm") or ""),
            hdr.get("jf_kode") or (hdr.get("jenis_formasi") or "UMUM"),
            pend_key,
        )
        if key not in by_key:
            by_key[key] = sec
            ordered_keys.append(key)
        else:
            old = by_key[key]
            # Prefer section with more valid parsed candidates, tie-breaking on Ringkas
            if len(sec["candidates"]) > len(old["candidates"]) or (
                len(sec["candidates"]) == len(old["candidates"]) and old["mode"] == "rincian" and sec["mode"] == "ringkas"
            ):
                by_key[key] = sec

    final_sections = [by_key[k] for k in ordered_keys]
    return {"sections": final_sections, "failures": total_failures}


def _norm_txt(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"\s+", " ", s).strip().upper()
    s = s.replace("PEMERINTAH KABUPATEN ", "PEMERINTAH KAB. ")
    s = s.replace("PEMERINTAH DAERAH KABUPATEN ", "PEMERINTAH KAB. ")
    s = s.replace("PEMERINTAH KOTA ADMINISTRASI ", "PEMERINTAH KOTA ")
    return s


def _norm_jf(s: str | None) -> str:
    u = _norm_txt(s)
    if not u or u == "UMUM":
        return "UMUM"
    if "TERBAIK" in u or "CUMLAUDE" in u:
        return "LULUSAN TERBAIK"
    if "DISABILITAS" in u:
        return "PENYANDANG DISABILITAS"
    if "PAPUA" in u:
        return "PUTRA/PUTRI PAPUA"
    if "KALIMANTAN" in u:
        return "PUTRA/PUTRI KALIMANTAN"
    if "DIASPORA" in u:
        return "DIASPORA"
    return u


def _norm_relaxed(s: str | None) -> str:
    u = _norm_txt(s)
    u = re.sub(r"\s*-\s*", " ", u)
    u = re.sub(r"[^A-Z0-9| ]+", " ", u)
    return re.sub(r"\s+", " ", u).strip()


def _norm_no_digits(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\b\d+\b", " ", _norm_relaxed(s))).strip()


def match_sections_to_db(
    instansi_id_2024: int, parsed_sections: list[dict[str, Any]], conn: sqlite3.Connection
) -> tuple[int, int]:
    """Match parsed sections 1-to-1 against cpns2024.db formasi rows."""
    db_rows = conn.execute(
        """
        SELECT formasi_id, jabatan_nm, lokasi_nm, jenis_formasi, jumlah_formasi, jumlah_pelamar
        FROM formasi
        WHERE instansi_id = ?
        """,
        (instansi_id_2024,),
    ).fetchall()
    if not db_rows:
        return 0, 0

    exact_map: dict[tuple[str, str, str], list[tuple[str, int]]] = {}
    jfnorm_map: dict[tuple[str, str, str], list[tuple[str, int]]] = {}
    no_jf_map: dict[tuple[str, str], list[tuple[str, int]]] = {}
    rel_map: dict[tuple[str, str, str], list[tuple[str, int]]] = {}
    rel_nojf_map: dict[tuple[str, str], list[tuple[str, int]]] = {}
    nodig_map: dict[tuple[str, str, str], list[tuple[str, int]]] = {}

    for fid, jab, lok, jf, kuota, _pel in db_rows:
        jn = _norm_txt(jab)
        ln = _norm_txt(lok)
        jf_raw = _norm_txt(jf or "UMUM")
        jf_bkt = _norm_jf(jf)
        jr = _norm_relaxed(jab)
        lr = _norm_relaxed(lok)
        lnd = _norm_no_digits(lok)
        k = int(kuota or 0)
        exact_map.setdefault((jn, ln, jf_raw), []).append((fid, k))
        jfnorm_map.setdefault((jn, ln, jf_bkt), []).append((fid, k))
        no_jf_map.setdefault((jn, ln), []).append((fid, k))
        rel_map.setdefault((jr, lr, jf_bkt), []).append((fid, k))
        rel_nojf_map.setdefault((jr, lr), []).append((fid, k))
        nodig_map.setdefault((jr, lnd, jf_bkt), []).append((fid, k))

    used_fids: set[str] = set()
    matched = 0

    for sec in parsed_sections:
        hdr = sec["hdr"]
        jn = _norm_txt(hdr.get("jabatan_nm"))
        ln = _norm_txt(hdr.get("lokasi_nm"))
        jf_raw = _norm_txt(hdr.get("jenis_formasi") or "UMUM")
        jf_bkt = _norm_jf(jf_raw)
        jr = _norm_relaxed(hdr.get("jabatan_nm"))
        lr = _norm_relaxed(hdr.get("lokasi_nm"))
        lnd = _norm_no_digits(hdr.get("lokasi_nm"))
        cnts = sec.get("counts") or {}
        sec_k = cnts.get("jumlah_formasi") or hdr.get("jumlah_formasi_header")

        picked: str | None = None
        for pool_list in (
            exact_map.get((jn, ln, jf_raw), []),
            jfnorm_map.get((jn, ln, jf_bkt), []),
            no_jf_map.get((jn, ln), []),
            rel_map.get((jr, lr, jf_bkt), []),
            rel_nojf_map.get((jr, lr), []),
            nodig_map.get((jr, lnd, jf_bkt), []),
        ):
            avail = [(fid, k) for fid, k in pool_list if fid not in used_fids]
            if not avail:
                continue
            if sec_k is not None:
                exact_k = [fid for fid, k in avail if k == int(sec_k)]
                if exact_k:
                    picked = exact_k[0]
                    break
            picked = avail[0][0]
            break

        if picked:
            used_fids.add(picked)
            matched += 1
        sec["formasi_id_2024"] = picked

    return matched, len(db_rows)


def _file_stage_rank(name: str) -> int:
    lo = name.lower()
    score = 0
    if "kedua" in lo or "ke-2" in lo or "perubahan" in lo:
        score += 4
    if "pasca" in lo or "penggant" in lo or "pengolahan kembali" in lo or "final" in lo:
        score += 3
    if "kesatu" in lo or "akhir" in lo:
        score += 1
    if "pra" in lo or "sebelum" in lo:
        score -= 2
    return score


def discover_agency_dirs() -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {}
    for _cat, sub in CAT_SUBDIR.items():
        base = SCORES_ROOT / sub
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and not d.name.startswith("_") and d.name.startswith("INS-"):
                kode = d.name.split("_")[0]
                out.setdefault(kode, []).append(d)
    return out


def _quick_classify_pdf(pdf_path: Path, expected_nama: str) -> dict[str, Any] | None:
    sz = pdf_path.stat().st_size
    if sz < 200 or not pdf_path.open("rb").read(4).startswith(b"%PDF"):
        return None
    try:
        doc = pdfium.PdfDocument(str(pdf_path))
        n = len(doc)
        idxs = sorted(set(list(range(min(10, n))) + [n // 4, n // 2, (3 * n) // 4, max(0, n - 1)]))
        rekap = rincian = 0
        has_pppk = has_cpns = False
        instansi_hdr = None
        for i in idxs:
            txt = doc[i].get_textpage().get_text_range()
            up = txt.upper()
            if "PENGADAAN PPPK" in up or "PEGAWAI PEMERINTAH DENGAN PERJANJIAN KERJA" in up:
                has_pppk = True
            if "PENGADAAN CPNS" in up or "CALON PEGAWAI NEGERI SIPIL" in up or "SKD (40%)" in up:
                has_cpns = True
            if "REKAP HASIL INTEGRASI" in up:
                if "(RINCIAN)" in up:
                    rincian += 1
                else:
                    rekap += 1
            elif "INFORMASI HASIL INTEGRASI NILAI" in up:
                rincian += 1
            if not instansi_hdr:
                mi = re.search(r"Instansi\s*:\s*(\d{3,5}\s*-\s*[^\r\n]+)", txt)
                if mi:
                    instansi_hdr = mi.group(1).strip()
        doc.close()
    except Exception:
        # Check zlib stream recovery (e.g., Kementan truncated PDF)
        if sz >= 100_000 and b"REKAP HASIL INTEGRASI" in zlib_sample_probe(pdf_path):
            return {"path": pdf_path, "sha": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "kind": "zlib_ringkas", "pages": 750, "size": sz, "stage": _file_stage_rank(pdf_path.name)}
        return None

    if has_pppk and not has_cpns and "cpns" not in pdf_path.name.lower():
        return None
    if rekap == 0 and rincian == 0:
        # Check Merangin / Berau custom tabular formats
        if "merangin" in expected_nama.lower() and "lulus-pra-sanggah" in pdf_path.name.lower():
            return {"path": pdf_path, "sha": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "kind": "custom_merangin", "pages": n, "size": sz, "stage": _file_stage_rank(pdf_path.name)}
        if "berau" in expected_nama.lower() and "skd skb cpns pemerintah kabupaten berau" in pdf_path.name.lower():
            return {"path": pdf_path, "sha": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16], "kind": "custom_berau", "pages": n, "size": sz, "stage": _file_stage_rank(pdf_path.name)}
        return None

    # Verify instansi header actually matches this agency
    if instansi_hdr:
        clean_nm = re.sub(r"^(Pemerintah|Kementerian|Badan|Lembaga|Kab\.|Kota|Provinsi|Setjen|Sekretariat Jenderal)\s+", "", expected_nama, flags=re.I)
        words = [w for w in clean_nm.lower().split() if len(w) > 3]
        if words and not any(w in instansi_hdr.lower() for w in words):
            return None

    if rekap and rincian:
        kind = "mixed"
    elif rekap:
        kind = "ringkas"
    else:
        kind = "rincian"

    return {
        "path": pdf_path,
        "sha": hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16],
        "kind": kind,
        "pages": n,
        "size": sz,
        "stage": _file_stage_rank(pdf_path.name),
    }


def zlib_sample_probe(pdf_path: Path) -> bytes:
    raw = pdf_path.read_bytes()
    for st in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S)[:25]:
        try:
            dec = zlib.decompress(st)
            if b"REKAP HASIL INTEGRASI" in dec:
                return dec
        except Exception:
            continue
    return b""


def parse_merangin_pdf(pdf_path: Path, iid24: int, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Parse Kab. Merangin tabular announcement and aggregate per matching 2024 formation."""
    pages = extract_pdf_pages_fast(pdf_path, workers=1)
    # In Merangin, p.3-11 list rows with NO 245504... NAMA JABATAN UNIT TIU TWK TKP TOTAL SKD100 SKOR40 SKB SKOR60 NA STATUS
    full = "\n".join(pages[2:])
    anchors = list(PESERTA_RE.finditer(full))
    db_rows = conn.execute(
        "SELECT formasi_id, jabatan_nm, lokasi_nm, jenis_formasi, jumlah_formasi FROM formasi WHERE instansi_id = ?",
        (iid24,),
    ).fetchall()

    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for idx, m in enumerate(anchors):
        pid = m.group(1)
        start = m.end()
        end = anchors[idx + 1].start() if idx + 1 < len(anchors) else len(full)
        chunk = " ".join(full[start:end].split())
        mt = re.search(rf"^(.*?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)\s+(\d+[.,]\d+)\s+{STATUS_RE_STR}\b", chunk)
        if not mt:
            continue
        tiu, twk, tkp, tot = int(mt.group(2)), int(mt.group(3)), int(mt.group(4)), int(mt.group(5))
        skd40, skb_val, skb60, na = _to_float(mt.group(7)), _to_float(mt.group(8)), _to_float(mt.group(9)), _to_float(mt.group(10))
        st = mt.group(11)
        if not _valid_scores(twk, tiu, tkp, tot, skd40, skb_val, skb60, na):
            continue
        prefix = mt.group(1).strip()
        by_group.setdefault((prefix, pid), []).append(
            {"no_peserta": pid, "total_skd": tot, "skor_skd": skd40, "nilai_skb": skb_val, "nilai_akhir": na, "status": st, "is_lulus": is_lulus_status(st), "prefix": prefix}
        )

    # Map each prefix string uniquely to (jabatan_nm, lokasi_nm) in cpns2024.db
    grouped_by_fid: dict[str, dict[str, Any]] = {}
    for (_pfx, _pid), items in by_group.items():
        c = items[0]
        up_pfx = re.sub(r"\s+", " ", c["prefix"].upper())
        best_row = None
        for fid, jab, lok, jf, kuota in db_rows:
            ju = jab.upper()
            # Merangin puts NAME JABATAN UNIT; check if jabatan_nm appears in prefix
            if ju in up_pfx:
                # Prefer longest unit tail match
                unit_words = [w for w in lok.upper().split("|")[-1].split() if len(w) > 3]
                score = len(ju) + sum(5 for w in unit_words if w in up_pfx)
                if best_row is None or score > best_row[0]:
                    best_row = (score, fid, jab, lok, jf or "UMUM", int(kuota or 1))
        if best_row is None:
            continue
        _, fid, jab, lok, jf, kuota = best_row
        sec = grouped_by_fid.setdefault(
            fid,
            {
                "formasi_id_2024": fid,
                "hdr": {"jab_kode": None, "jabatan_nm": jab, "lok_kode": None, "lokasi_nm": lok, "jenis_formasi": jf, "pendidikan_raw": "", "jumlah_formasi_header": kuota},
                "counts": {"peserta_skb": 0, "hadir": 0, "jumlah_formasi": kuota, "lulus_akhir": 0},
                "page_rekap": 3,
                "mode": "custom_merangin",
                "candidates": [],
            },
        )
        sec["candidates"].append(c)
        sec["counts"]["peserta_skb"] += 1
        if c["status"] != "TH":
            sec["counts"]["hadir"] += 1
        if c["is_lulus"]:
            sec["counts"]["lulus_akhir"] += 1

    return list(grouped_by_fid.values())


def _norm_berau(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\ufffe", "-").replace(" | ", "|").upper()).strip()


def parse_berau_pdf(pdf_path: Path, iid24: int, conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Parse Kab. Berau tabular SKD+SKB announcement and aggregate per matching 2024 formation."""
    pages = extract_pdf_pages_fast(pdf_path, workers=1)
    clean_lines: list[str] = []
    for pg in pages:
        for line in pg.splitlines():
            s = " ".join(line.split())
            if not s or re.match(
                r"^(?:TWK TIU|Total|\(Skala|1 2 3|Jenis|Formasi No|Nilai|Skor|Tahun|SKD|SKB|100\)|No No\. Peserta)",
                s,
            ):
                continue
            clean_lines.append(s)

    blocks = re.split(r"(?m)^(?=\d+\s+246904\d{11}\b)", "\n".join(clean_lines))
    row_re = re.compile(
        r"^(\d+)\s+(246904\d{11})\s+(.+?)\s+Pemerintah Kab\.\s+Berau\s+"
        r"(PEMERINTAH KABUPATEN BERAU\s*\|.+)\s+"
        r"(UMUM|LULUSAN TERBAIK|PENYANDAN\s*G\s*DISABILITAS|PENYANDANG\s*DISABILITAS|PUTRA/PUTRI KALIMANTAN)\s+"
        r"(.+?)\s+"
        r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+"
        r"(P/(?:L(?:-U\d|-E\d)?|TL|TH|TMS(?:-1)?|APS)|L(?:-U\d|-E\d)?|TL|TH|TMS(?:-1)?|APS)\s+(20\d{2})\b"
    )

    db_rows = conn.execute(
        "SELECT formasi_id, jabatan_nm, lokasi_nm, jenis_formasi, jumlah_formasi FROM formasi WHERE instansi_id = ?",
        (iid24,),
    ).fetchall()
    db_norm = [(_norm_berau(j), _norm_berau(l), fid, j, l, jf or "UMUM", int(kuota or 1)) for fid, j, l, jf, kuota in db_rows]

    grouped_by_fid: dict[str, dict[str, Any]] = {}
    for b in blocks:
        b1 = " ".join(b.split())
        if not re.match(r"^\d+\s+246904\d{11}\b", b1):
            continue
        mt = row_re.match(b1)
        if not mt:
            continue
        pid = mt.group(2)
        lok = _norm_berau(mt.group(4))
        rest = _norm_berau(mt.group(6))
        twk, tiu, tkp, tot = int(mt.group(7)), int(mt.group(8)), int(mt.group(9)), int(mt.group(10))
        skd40, skb_val, skb60, na = _to_float(mt.group(12)), _to_float(mt.group(13)), _to_float(mt.group(14)), _to_float(mt.group(15))
        st = mt.group(16)
        if not _valid_scores(twk, tiu, tkp, tot, skd40, skb_val, skb60, na):
            continue

        cands = [row for row in db_norm if row[1] == lok and rest.startswith(row[0])]
        if not cands:
            tail = lok.split("|")[-1].strip()
            cands = [row for row in db_norm if rest.startswith(row[0]) and tail in row[1]]
        if not cands:
            continue
        cands.sort(key=lambda r: len(r[0]), reverse=True)
        _, _, fid, jab_orig, lok_orig, jf_orig, kuota = cands[0]

        sec = grouped_by_fid.setdefault(
            fid,
            {
                "formasi_id_2024": fid,
                "hdr": {"jab_kode": None, "jabatan_nm": jab_orig, "lok_kode": None, "lokasi_nm": lok_orig, "jenis_formasi": jf_orig, "pendidikan_raw": "", "jumlah_formasi_header": kuota},
                "counts": {"peserta_skb": 0, "hadir": 0, "jumlah_formasi": kuota, "lulus_akhir": 0},
                "page_rekap": 5,
                "mode": "custom_berau",
                "candidates": [],
            },
        )
        lulus = is_lulus_status(st)
        sec["candidates"].append(
            {"no_peserta": pid, "total_skd": tot, "skor_skd": skd40, "nilai_skb": skb_val, "nilai_akhir": na, "status": st, "is_lulus": lulus}
        )
        sec["counts"]["peserta_skb"] += 1
        if not st.endswith("TH"):
            sec["counts"]["hadir"] += 1
        if lulus:
            sec["counts"]["lulus_akhir"] += 1

    return list(grouped_by_fid.values())


def select_best_files(cands: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Select full-corpus base file + any clean Panselnas overlay delta files."""
    if not cands:
        return None, []
    # Dedup by sha
    uniq: list[dict[str, Any]] = []
    seen_sha: set[str] = set()
    for c in sorted(cands, key=lambda x: (x["stage"], x["pages"], x["size"]), reverse=True):
        if c["sha"] not in seen_sha:
            seen_sha.add(c["sha"])
            uniq.append(c)

    mer = [c for c in uniq if c["kind"] in ("custom_merangin", "custom_berau")]
    if mer:
        return mer[0], []

    zlibs = [c for c in uniq if c["kind"] == "zlib_ringkas"]
    ringkas_pool = [c for c in uniq if c["kind"] in ("ringkas", "mixed")]
    rincian_pool = [c for c in uniq if c["kind"] == "rincian"]

    if ringkas_pool and (max(x["pages"] for x in ringkas_pool) >= 15 or not rincian_pool):
        pool = ringkas_pool
    elif rincian_pool:
        pool = rincian_pool
    elif zlibs:
        return zlibs[0], []
    else:
        pool = uniq

    max_p = max(x["pages"] for x in pool)
    fulls = [x for x in pool if x["pages"] >= 0.65 * max_p]
    fulls.sort(key=lambda x: (x["stage"], 1 if x["kind"] == "ringkas" else 0, x["pages"], x["size"]), reverse=True)
    base = fulls[0]

    # Overlay deltas ONLY if explicitly pasca/pengganti/perubahan and smaller subset in BKN format
    overlays = [
        x for x in uniq
        if x["sha"] != base["sha"]
        and x["kind"] in ("ringkas", "rincian", "mixed")
        and x["pages"] < 0.65 * max_p
        and x["stage"] > base["stage"]
        and x["pages"] >= 2
    ]
    return base, overlays


def process_one_agency(
    iid: int,
    kode: str,
    nama: str,
    dirs: list[Path],
    conn: sqlite3.Connection,
) -> dict[str, Any] | None:
    t0 = time.perf_counter()

    # Check Phase-1 curated legacy source first if it exists
    sumber_override = None
    out_kode = kode
    cands: list[dict[str, Any]] = []

    if iid in PHASE1_LEGACY_CODES:
        short_code, legacy_dir, legacy_file, legacy_sumber = PHASE1_LEGACY_CODES[iid]
        out_kode = short_code
        sumber_override = legacy_sumber
        p_leg = SCORES_ROOT / legacy_dir / legacy_file
        if p_leg.exists():
            cl = _quick_classify_pdf(p_leg, nama)
            if cl:
                cl["stage"] += 10  # Pin Phase-1 curated artifact cleanly
                cands.append(cl)

    for d in dirs:
        for f in sorted(d.glob("*.pdf")):
            cl = _quick_classify_pdf(f, nama)
            if cl:
                cands.append(cl)

    base, overlays = select_best_files(cands)
    if base is None:
        return None

    pdf_path: Path = base["path"]
    if base["kind"] == "custom_merangin":
        parsed_secs = parse_merangin_pdf(pdf_path, iid, conn)
        math_failures = 0
        sumber_label = f"Pengumuman Hasil Akhir Pra-Sanggah CPNS {nama} TA 2024 ({pdf_path.name})"
    elif base["kind"] == "custom_berau":
        parsed_secs = parse_berau_pdf(pdf_path, iid, conn)
        math_failures = 0
        sumber_label = f"Pengumuman Hasil Akhir SKD-SKB CPNS {nama} TA 2024 ({pdf_path.name})"
    elif base["kind"] == "zlib_ringkas":
        pages = extract_zlib_stream_pages(pdf_path)
        res = parse_bkn_pages(pages, allow_mode="ringkas")
        # Strictly keep ONLY Kementan partial sections with exact candidate count == expected_peserta_skb (or complete pl == lulus)
        parsed_secs = [
            s for s in res["sections"]
            if s.get("counts")
            and len(s["candidates"]) == s["counts"]["peserta_skb"]
            and sum(1 for c in s["candidates"] if c["is_lulus"]) == s["counts"]["lulus_akhir"]
        ]
        math_failures = res["failures"]
        sumber_label = f"Lampiran I Ringkas Hasil Integrasi SKD-SKB {nama} TA 2024 (parsial terverifikasi: {pdf_path.name})"
    else:
        pages = extract_pdf_pages_fast(pdf_path)
        allow = "ringkas" if base["kind"] == "mixed" else base["kind"]
        res = parse_bkn_pages(pages, allow_mode=allow)
        parsed_secs = res["sections"]
        math_failures = res["failures"]
        # Fallback to rincian if mixed yielded too few
        if not parsed_secs and base["kind"] == "mixed":
            res = parse_bkn_pages(pages, allow_mode="all")
            parsed_secs = res["sections"]
            math_failures = res["failures"]

        # Apply any smaller pasca/pengganti Panselnas overlay cleanly
        if overlays:
            by_key = {
                (s["hdr"].get("jab_kode") or s["hdr"]["jabatan_nm"], s["hdr"].get("lok_kode") or s["hdr"].get("lokasi_nm"), s["hdr"].get("jf_kode") or s["hdr"].get("jenis_formasi")): s
                for s in parsed_secs
            }
            for ov in overlays:
                ov_pages = extract_pdf_pages_fast(ov["path"], workers=1)
                ov_res = parse_bkn_pages(ov_pages, allow_mode="all")
                for os_sec in ov_res["sections"]:
                    oh = os_sec["hdr"]
                    k = (oh.get("jab_kode") or oh["jabatan_nm"], oh.get("lok_kode") or oh.get("lokasi_nm"), oh.get("jf_kode") or oh.get("jenis_formasi"))
                    oc = os_sec.get("counts") or {}
                    if k in by_key and oc and len(os_sec["candidates"]) == oc.get("peserta_skb", -1):
                        by_key[k] = os_sec
            parsed_secs = list(by_key.values())

        sumber_label = sumber_override or f"Lampiran Resmi Hasil Integrasi SKD-SKB {nama} TA 2024 ({pdf_path.name})"

    if not parsed_secs:
        return None

    # Match to cpns2024.db (for non-Merangin/Berau, which already carry formasi_id_2024)
    if base["kind"] in ("custom_merangin", "custom_berau"):
        db_total = conn.execute("SELECT COUNT(*) FROM formasi WHERE instansi_id = ?", (iid,)).fetchone()[0]
        db_matched = sum(1 for s in parsed_secs if s.get("formasi_id_2024"))
    else:
        db_matched, db_total = match_sections_to_db(iid, parsed_secs, conn)

    parsed_rows = sum(len(s["candidates"]) for s in parsed_secs)
    parsed_pl = sum(1 for s in parsed_secs for c in s["candidates"] if c["is_lulus"])
    expected_rows = sum((s.get("counts") or {}).get("peserta_skb", 0) for s in parsed_secs)
    expected_pl = sum((s.get("counts") or {}).get("lulus_akhir", 0) for s in parsed_secs)

    out_sections: list[dict[str, Any]] = []
    all_pl_na: list[float] = []
    all_pl_skd: list[int] = []
    all_all_skd: list[int] = []

    for s in parsed_secs:
        hdr = s["hdr"]
        cnts = s.get("counts") or {}
        cands = s["candidates"]
        pl = [c for c in cands if c["is_lulus"]]
        pl_na = [c["nilai_akhir"] for c in pl]
        pl_skd = [c["total_skd"] for c in pl]
        pl_skb = [c["nilai_skb"] for c in pl]
        skb_skd = [c["total_skd"] for c in cands]

        all_pl_na.extend(pl_na)
        all_pl_skd.extend(pl_skd)
        all_all_skd.extend(skb_skd)

        peserta_cnt = cnts.get("peserta_skb", len(cands))
        hadir_cnt = cnts.get("hadir", sum(1 for c in cands if c["status"] != "TH"))

        out_sections.append(
            {
                "instansi_kode": out_kode,
                "instansi_kode_canonical": kode,
                "instansi_id_2024": iid,
                "formasi_id_2024": s.get("formasi_id_2024"),
                "page_rekap": s["page_rekap"],
                "jab_kode": hdr.get("jab_kode"),
                "jabatan_nm": hdr.get("jabatan_nm"),
                "lok_kode": hdr.get("lok_kode"),
                "lokasi_nm": hdr.get("lokasi_nm"),
                "jenis_formasi": hdr.get("jenis_formasi") or "UMUM",
                "pendidikan_raw": hdr.get("pendidikan_raw"),
                "jumlah_formasi": cnts.get("jumlah_formasi") or hdr.get("jumlah_formasi_header"),
                "peserta_skb": peserta_cnt,
                "hadir_skb": hadir_cnt,
                "n_lulus": len(pl),
                "nilai_akhir_lulus": compute_stats(pl_na),
                "skd_lulus": compute_stats(pl_skd),
                "skb_lulus": compute_stats(pl_skb),
                "skd_peserta_skb": compute_stats(skb_skd),
                "sumber": sumber_label,
                # Keep exact raw vectors for zero-approximation aggregation into cpns2026.db
                "pl_na": pl_na,
                "pl_skd": pl_skd,
                "pl_skb": pl_skb,
                "skb_skd": skb_skd,
            }
        )

    elapsed = round(time.perf_counter() - t0, 2)
    meta = {
        "instansi_kode": out_kode,
        "instansi_kode_canonical": kode,
        "instansi_id_2024": iid,
        "instansi_nm": nama,
        "pdf_file": pdf_path.name,
        "pdf_kind": base["kind"],
        "pages": base["pages"],
        "sections": len(out_sections),
        "parsed_rows": parsed_rows,
        "expected_rows": expected_rows,
        "parsed_pl": parsed_pl,
        "expected_pl": expected_pl,
        "math_failures": math_failures,
        "elapsed_s": elapsed,
        "sumber": sumber_label,
        "db_matched_sections": db_matched,
        "db_total_rows": db_total,
        "overall_nilai_akhir_lulus": compute_stats(all_pl_na),
        "overall_skd_lulus": compute_stats(all_pl_skd),
        "overall_skd_skb": compute_stats(all_all_skd),
    }
    return {"meta": meta, "sections": out_sections}


def write_outputs_and_load_sqlite(agency_payloads: list[dict[str, Any]], load_db: bool = True) -> None:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_agencies: dict[str, Any] = {}
    summary_agencies: dict[str, Any] = {}
    raw_sections: list[dict[str, Any]] = []
    phase1_summary_sections: list[dict[str, Any]] = []

    for p in agency_payloads:
        m = p["meta"]
        canonical = m["instansi_kode_canonical"]
        raw_agencies[canonical] = m
        summary_agencies[m["instansi_kode"]] = m
        for s in p["sections"]:
            raw_sections.append(s)
            if m["instansi_id_2024"] in PHASE1_LEGACY_CODES:
                phase1_summary_sections.append({k: v for k, v in s.items() if k not in ("pl_na", "pl_skd", "pl_skb", "skb_skd")})

    RAW_ALL_OUT.write_text(json.dumps({"agencies": raw_agencies, "sections": raw_sections}, ensure_ascii=False), encoding="utf-8")
    SUMMARY_ALL_OUT.write_text(json.dumps({"agencies": summary_agencies}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Also keep Phase-1 6-agency raw & summary updated cleanly for any backward callers
    p1_raw_secs = [s for s in raw_sections if s["instansi_id_2024"] in PHASE1_LEGACY_CODES]
    p1_agencies = {m["instansi_kode"]: m for m in raw_agencies.values() if m["instansi_id_2024"] in PHASE1_LEGACY_CODES}
    if p1_raw_secs:
        (PARSED_DIR / "scores_2024_6instansi_raw.json").write_text(
            json.dumps({"agencies": p1_agencies, "sections": p1_raw_secs}, ensure_ascii=False), encoding="utf-8"
        )
        LEGACY_JSON_OUT.write_text(
            json.dumps({"agencies": p1_agencies, "sections": phase1_summary_sections}, ensure_ascii=False), encoding="utf-8"
        )

    if not load_db:
        return

    print(f"\nLoading {len(raw_sections):,} sections into {DB_2024_PATH} ...")
    conn = sqlite3.connect(str(DB_2024_PATH))
    conn.execute("PRAGMA journal_mode = DELETE;")
    conn.execute("PRAGMA synchronous = OFF;")
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS formasi_scores_2024;
        DROP TABLE IF EXISTS scores_2024_sources;

        CREATE TABLE scores_2024_sources (
            source_id INTEGER PRIMARY KEY AUTOINCREMENT,
            instansi_kode TEXT NOT NULL,
            sumber TEXT NOT NULL UNIQUE
        );

        CREATE TABLE formasi_scores_2024 (
            formasi_id TEXT PRIMARY KEY,
            source_id INTEGER NOT NULL,
            peserta_skb INTEGER NOT NULL DEFAULT 0,
            hadir_skb INTEGER NOT NULL DEFAULT 0,
            n_lulus INTEGER NOT NULL DEFAULT 0,
            jenis_formasi TEXT,
            na_n INTEGER NOT NULL DEFAULT 0,
            na_min REAL, na_p25 REAL, na_median REAL, na_p75 REAL, na_max REAL, na_mean REAL,
            skd_n INTEGER NOT NULL DEFAULT 0,
            skd_min REAL, skd_p25 REAL, skd_median REAL, skd_p75 REAL, skd_max REAL, skd_mean REAL,
            skb_n INTEGER NOT NULL DEFAULT 0,
            skb_min REAL, skb_p25 REAL, skb_median REAL, skb_p75 REAL, skb_max REAL, skb_mean REAL,
            skd_skb_n INTEGER NOT NULL DEFAULT 0,
            skd_skb_min REAL, skd_skb_p25 REAL, skd_skb_median REAL, skd_skb_p75 REAL, skd_skb_max REAL, skd_skb_mean REAL,
            FOREIGN KEY (formasi_id) REFERENCES formasi(formasi_id),
            FOREIGN KEY (source_id) REFERENCES scores_2024_sources(source_id)
        );
        """
    )

    source_cache: dict[tuple[str, str], int] = {}
    rows_to_insert: list[tuple[Any, ...]] = []
    seen_fids: set[str] = set()

    for s in raw_sections:
        fid = s.get("formasi_id_2024")
        if not fid or fid in seen_fids:
            continue
        seen_fids.add(fid)

        src_key = (s["instansi_kode"], s["sumber"])
        if src_key not in source_cache:
            cur.execute(
                "INSERT OR IGNORE INTO scores_2024_sources (instansi_kode, sumber) VALUES (?, ?)",
                (s["instansi_kode"], s["sumber"]),
            )
            sid = cur.execute("SELECT source_id FROM scores_2024_sources WHERE sumber = ?", (s["sumber"],)).fetchone()[0]
            source_cache[src_key] = sid
        sid = source_cache[src_key]

        na = s["nilai_akhir_lulus"]
        skd = s["skd_lulus"]
        skb = s["skb_lulus"]
        sskd = s["skd_peserta_skb"]
        rows_to_insert.append(
            (
                fid, sid,
                int(s.get("peserta_skb") or 0), int(s.get("hadir_skb") or 0), int(s.get("n_lulus") or 0),
                s.get("jenis_formasi") or "UMUM",
                na["n"], na["min"], na["p25"], na["median"], na["p75"], na["max"], na["mean"],
                skd["n"], skd["min"], skd["p25"], skd["median"], skd["p75"], skd["max"], skd["mean"],
                skb["n"], skb["min"], skb["p25"], skb["median"], skb["p75"], skb["max"], skb["mean"],
                sskd["n"], sskd["min"], sskd["p25"], sskd["median"], sskd["p75"], sskd["max"], sskd["mean"],
            )
        )

    cur.executemany(
        """
        INSERT INTO formasi_scores_2024 VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """,
        rows_to_insert,
    )
    conn.commit()
    conn.close()
    print(f"Inserted {len(rows_to_insert):,} unique matched formation score records across {len(raw_agencies)} agencies.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse all harvested CPNS 2024 score PDFs.")
    ap.add_argument("--only", nargs="*", help="Filter by canonical INS-xxxx codes (e.g. INS-0008 INS-0066)")
    ap.add_argument("--resume", action="store_true", help="Skip agencies with an existing checkpoint in per_agency/")
    ap.add_argument("--no-load-db", action="store_true", help="Only parse & checkpoint without modifying cpns2024.db")
    args = ap.parse_args()

    PER_AGENCY_DIR.mkdir(parents=True, exist_ok=True)
    dir_map = discover_agency_dirs()

    conn = sqlite3.connect(f"file:{DB_2024_PATH}?mode=ro", uri=True)
    agencies = conn.execute(
        "SELECT instansi_id, kode_instansi, nama_instansi, kategori_instansi FROM instansi ORDER BY instansi_id"
    ).fetchall()

    only_set = set(args.only) if args.only else None
    all_payloads: list[dict[str, Any]] = []

    for iid, kode, nama, cat in agencies:
        if only_set and kode not in only_set:
            continue
        ckpt = PER_AGENCY_DIR / f"{kode}.json"
        if args.resume and ckpt.exists():
            payload = json.loads(ckpt.read_text(encoding="utf-8"))
            all_payloads.append(payload)
            m = payload["meta"]
            print(f"[CACHED] {kode} {nama}: sec={m['sections']} db={m['db_matched_sections']}/{m['db_total_rows']} rows={m['parsed_rows']}/{m['expected_rows']}")
            continue

        dirs = dir_map.get(kode, [])
        if not dirs and iid not in PHASE1_LEGACY_CODES:
            continue

        payload = process_one_agency(iid, kode, nama, dirs, conn)
        if payload is None:
            continue
        ckpt.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        all_payloads.append(payload)
        m = payload["meta"]
        print(
            f"[PARSED] {kode} {nama} ({m['pdf_kind']} {m['pages']}p): "
            f"sec={m['sections']} db={m['db_matched_sections']}/{m['db_total_rows']} "
            f"rows={m['parsed_rows']}/{m['expected_rows']} pl={m['parsed_pl']}/{m['expected_pl']} "
            f"fail={m['math_failures']} ({m['elapsed_s']}s)"
        )

    conn.close()

    if only_set:
        # In --only test mode without full run, don't overwrite full SQLite unless all checkpoints loaded
        print(f"\nTargeted run complete: {len(all_payloads)} agencies.")
        if not args.no_load_db:
            write_outputs_and_load_sqlite(all_payloads, load_db=False)
        return

    write_outputs_and_load_sqlite(all_payloads, load_db=not args.no_load_db)


if __name__ == "__main__":
    main()
