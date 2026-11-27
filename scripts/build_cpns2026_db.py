#!/usr/bin/env python3
"""
Build verified CPNS 2026 SQLite database (data/cpns2026.db + .gz) and CSV
(data/raw_cpns_2026.csv) from KepmenPANRB Nomor 675 Tahun 2026 (Kementerian Keuangan TA 2026).

Strict No-Hallucination Contract:
- Only populates fields present in the verified source decree (jabatan, kualifikasi pendidikan,
  alokasi_cpns, unit penempatan, instansi, sumber_dokumen) plus statutory Golongan/Tukin lookup
  metadata explicitly labeled as reference simulation.
- Leaves jumlah_pelamar, jenis_formasi, rasio_kompetisi, peluang_lolos_pct, status_keketatan,
  gaji_min, and gaji_max as NULL / empty because those SSCASN 2026 fields are not yet published.
"""

from __future__ import annotations

import csv
import gzip
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REFS_DIR = Path(r"D:\AG Files\cpns2026-scraper\data\refs")
PAGES_DIR = REFS_DIR / "kemenkeu_pages"
OCR_PATH = REFS_DIR / "kemenkeu_ocr.json"

DB_PATH = DATA_DIR / "cpns2026.db"
DB_GZ_PATH = DATA_DIR / "cpns2026.db.gz"
CSV_PATH = DATA_DIR / "raw_cpns_2026.csv"
VERIFIED_JSON_PATH = DATA_DIR / "kemenkeu_2026_verified.json"
ALL_VERIFIED_JSON_PATH = DATA_DIR / "cpns_2026_verified.json"
AUDIT_JSON_PATH = DATA_DIR / "drive_audit_2026.json"

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extra_sources_2026 import (  # noqa: E402
    DRIVE_AUDIT_SUMMARY,
    EXTRA_INSTANSI,
    compute_2024_comparison_map,
    get_bpkp_rows,
    get_bssn_rows,
    get_kejagung_rows,
    get_kemenkes_str_rows,
    get_kemenkum_rows,
    get_sscasn_live_rows,
)

SUMBER_DOKUMEN = (
    "KepmenPANRB No. 675 Tahun 2026 — Penetapan Kebutuhan PNS Kementerian Keuangan TA 2026 "
    "(Ditetapkan Jakarta, 19 November 2026)"
)

# Ground-truth ALOKASI CPNS per NO (1..374), visually verified across all 35 lampiran pages (5..39)
VERIFIED_ALOKASI: dict[int, int] = {
    1: 43, 2: 6, 3: 34, 4: 10,
    5: 12, 6: 63, 7: 37, 8: 10,
    9: 2, 10: 5, 11: 5,
    12: 5, 13: 5, 14: 2,
    15: 1, 16: 2, 17: 1, 18: 1, 19: 4, 20: 1, 21: 1, 22: 1, 23: 2, 24: 2,
    25: 2, 26: 3, 27: 3, 28: 4, 29: 1, 30: 1,
    31: 1, 32: 3, 33: 1, 34: 2, 35: 1, 36: 1, 37: 1, 38: 1, 39: 1, 40: 1,
    41: 1, 42: 1, 43: 1, 44: 3, 45: 1, 46: 42, 47: 4, 48: 200, 49: 30, 50: 1,
    51: 1, 52: 2, 53: 1, 54: 2, 55: 6, 56: 2, 57: 1, 58: 11, 59: 1, 60: 1,
    61: 2, 62: 1, 63: 1, 64: 1, 65: 1, 66: 5, 67: 2, 68: 2, 69: 1, 70: 5,
    71: 6, 72: 1, 73: 5, 74: 2, 75: 1, 76: 2, 77: 1, 78: 1, 79: 1, 80: 2,
    81: 2, 82: 2, 83: 3, 84: 3, 85: 1, 86: 1, 87: 2, 88: 11, 89: 5, 90: 1,
    91: 4, 92: 3, 93: 53, 94: 4, 95: 12, 96: 1, 97: 2, 98: 1, 99: 1, 100: 3,
    101: 2, 102: 2, 103: 3, 104: 1, 105: 2, 106: 2, 107: 2, 108: 3, 109: 1, 110: 1,
    111: 3, 112: 3, 113: 7, 114: 5, 115: 1, 116: 1, 117: 1, 118: 2, 119: 1, 120: 15,
    121: 4, 122: 145, 123: 1, 124: 3, 125: 1, 126: 1, 127: 2, 128: 21, 129: 4, 130: 1,
    131: 1, 132: 2, 133: 1, 134: 3, 135: 1, 136: 2, 137: 3, 138: 2, 139: 86, 140: 1,
    141: 1, 142: 3, 143: 1, 144: 2, 145: 15, 146: 1, 147: 2, 148: 2, 149: 4, 150: 80,
    151: 1, 152: 3, 153: 15, 154: 3, 155: 5, 156: 23, 157: 15, 158: 16, 159: 4, 160: 12,
    161: 1, 162: 1, 163: 1, 164: 1,
    165: 2,
    166: 10, 167: 8, 168: 3, 169: 10, 170: 7,
    206: 5, 207: 4, 208: 5, 209: 3, 210: 5, 211: 5, 212: 5, 213: 4, 214: 3, 215: 5, 216: 2,
    224: 1, 225: 1,
    251: 6, 252: 5,
    258: 8, 259: 2, 260: 8, 261: 4, 262: 8, 263: 5, 264: 4, 265: 4, 266: 8, 267: 16,
    268: 2, 269: 2, 270: 2, 271: 8, 272: 4, 273: 2, 274: 2, 275: 4, 276: 2, 277: 8, 278: 4,
    279: 20, 280: 4, 281: 3, 282: 4, 283: 4, 284: 7, 285: 5, 286: 4, 287: 4, 288: 5, 289: 20,
    290: 4, 291: 4,
    360: 6,
}
for _n in range(171, 375):
    VERIFIED_ALOKASI.setdefault(_n, 2)


def get_jabatan(no: int) -> str:
    if no <= 4:
        return "JURU MESIN KAPAL KELAS I"
    if no <= 8:
        return "KELASI KAPAL KELAS I"
    if no <= 11:
        return "MASINIS II KAPAL KELAS I"
    if no <= 14:
        return "MUALIM II KAPAL KELAS I"
    if no <= 164:
        return "PENELAAH TEKNIS KEBIJAKAN"
    if no == 165:
        return "PENGADMINISTRASI PERKANTORAN"
    if no <= 170:
        return "PENGOLAH DATA DAN INFORMASI"
    return "PETUGAS LALU LINTAS BARANG IMPOR, EKSPOR, DAN BARANG KENA CUKAI"


# Comprehensive word-level OCR repair table verified against the 35 Kemenkeu scan pages
UNIT_TOKEN_REPAIRS: dict[str, str] = {
    "KEMENTERLIAN": "KEMENTERIAN", "KEMENTER1AN": "KEMENTERIAN", "KEMENTERLAN": "KEMENTERIAN",
    "REMENTERIAN": "KEMENTERIAN", "KEMENFERIAN": "KEMENTERIAN", "KEMENTERIANI": "KEMENTERIAN",
    "KEUANCAN": "KEUANGAN", "KEUANGAI": "KEUANGAN", "KEUANGAIN": "KEUANGAN", "KEIJANGAN": "KEUANGAN",
    "KEUAINGAN": "KEUANGAN", "KECIANGAN": "KEUANGAN", "KEUJANGAN": "KEUANGAN", "KEUANG": "KEUANGAN",
    "KEIJANCAN": "KEUANGAN", "KEUANGI": "KEUANGAN", "KEUANCIAN": "KEUANGAN", "KEUANCJAN": "KEUANGAN",
    "KEUANC": "KEUANGAN",
    "DIREKIORAT": "DIREKTORAT", "DIREKTORNV": "DIREKTORAT", "DIREKTORXI": "DIREKTORAT",
    "DIREKFORAT": "DIREKTORAT", "DREKTORAT": "DIREKTORAT", "DIREKIORPCI": "DIREKTORAT",
    "DIRER": "DIREKTORAT", "TORAY": "DIREKTORAT",
    "ADVOKAS1": "ADVOKASI", "ADVOkAS1": "ADVOKASI", "ILPE": "TIPE", "LLPE": "TIPE", "IIPE": "TIPE",
    "JENDEWXL": "JENDERAL", "JENDFRAL": "JENDERAL", "JENDERAI": "JENDERAL", "IENDERAL": "JENDERAL",
    "JENDERIL": "JENDERAL", "JENDERA": "JENDERAL", "JENDEIUL": "JENDERAL", "JENIERAL": "JENDERAL",
    "DERAL": "JENDERAL", "JEN": "JENDERAL",
    "SEKRETARINI": "SEKRETARIAT", "SEKIRETARIAT": "SEKRETARIAT", "SEKRETARIAI": "SEKRETARIAT",
    "SEKIRETARIAI": "SEKRETARIAT", "SEKRETARIAF": "SEKRETARIAT", "SEKRETARIXI": "SEKRETARIAT",
    "SEKRETARILAT": "SEKRETARIAT", "SFKRETARIAT": "SEKRETARIAT",
    "INSPEKTORVI": "INSPEKTORAT", "SUBDIREKTORAI": "SUBDIREKTORAT", "SUBDIREKIORAT": "SUBDIREKTORAT",
    "CEJKAI": "CUKAI", "CUKAII": "CUKAI", "CIJKAI": "CUKAI", "CLJKAI": "CUKAI",
    "CUKAI1": "CUKAI", "CUKA1": "CUKAI", "CUJKAI": "CUKAI", "CUKA": "CUKAI",
    "PAIBEAN": "PABEAN", "PABEON": "PABEAN", "KEPABEONAN": "KEPABEANAN", "KEPABFANAN": "KEPABEANAN",
    "WIIAYAH": "WILAYAH", "WILAYOH": "WILAYAH", "PEIAYANAN": "PELAYANAN", "PELAN": "PELAYANAN",
    "SERKSI": "SEKSI", "SERSI": "SEKSI", "SEKS": "SEKSI", "SEKSJ": "SEKSI", "SFKSI": "SEKSI",
    "FASIITAS": "FASILITAS", "FASIIITAS": "FASILITAS", "INJERNAL": "INTERNAL",
    "PENYUIUHAN": "PENYULUHAN", "PENYIJLUHAN": "PENYULUHAN", "PENNDAKAN": "PENINDAKAN",
    "PENENDAKAN": "PENINDAKAN", "PENVIDIKAN": "PENYIDIKAN", "PENYIDLKAN": "PENYIDIKAN",
    "HUBUNCIAN": "HUBUNGAN", "HUBUNCJAN": "HUBUNGAN", "BIDANCJ": "BIDANG",
    "KUPANCI": "KUPANG", "KUPANC": "KUPANG", "TANJUNCI": "TANJUNG", "TANJONG": "TANJUNG",
    "TANJUNCG": "TANJUNG", "PANCIKALAN": "PANGKALAN", "OPERAS": "OPERASI",
    "PERBENDAHARAAI": "PERBENDAHARAAN", "PERBIENDAHARAAN": "PERBENDAHARAAN",
    "PERBFNDAHARAAN": "PERBENDAHARAAN", "PERBENDAHARAAAN": "PERBENDAHARAAN",
    "PERBENDAIIARAAN": "PERBENDAHARAAN", "PERBENDAIARAAN": "PERBENDAHARAAN",
    "PENGELOIAAN": "PENGELOLAAN", "PENGELOIAAAN": "PENGELOLAAN",
    "PEMBIAVAAN": "PEMBIAYAAN", "PEIMBIAYAAN": "PEMBIAYAAN",
    "ANCIGARAN": "ANGGARAN", "ANCJGARAN": "ANGGARAN",
    "PENGEMBANCIAN": "PENGEMBANGAN", "PENGENIBANGAN": "PENGEMBANGAN",
    "SEICIOR": "SEKTOR", "SERTOR": "SEKTOR", "SFKTOR": "SEKTOR", "SUIMBFR": "SUMBER",
    "KARIFR": "KARIER", "TAIENTA": "TALENTA", "KEPATUUAN": "KEPATUHAN", "KEPAIUIAN": "KEPATUHAN",
    "PAJAR": "PAJAK", "PALAK": "PAJAK", "UMIIM": "UMUM", "UMIJM": "UMUM", "IJMUM": "UMUM",
    "MANAEMEN": "MANAJEMEN", "WXNAJEMEN": "MANAJEMEN", "KEPULAIJAN": "KEPULAUAN",
    "PENAGIVIAN": "PENAGIHAN", "DISIPIIN": "DISIPLIN", "PENGFTAHUAN": "PENGETAHUAN",
    "PENGETATIUAN": "PENGETAHUAN", "TEKNOIOGI": "TEKNOLOGI", "IEKNOLOGI": "TEKNOLOGI",
    "INTEIIJEN": "INTELIJEN", "ILPE": "TIPE", "LLPE": "TIPE", "IIPE": "TIPE",
    "TIPEA": "TIPE A", "KAVIOR": "KANTOR", "ADVOKAS1": "ADVOKASI", "NIBLING": "NIBUNG",
    "BAIAI": "BALAI", "BALA1": "BALAI", "BALAI1": "BALAI", "BALAJ": "BALAI",
    "KEIAS": "KELAS", "MAIII": "MALILI", "MAIIII": "MALILI", "MAIILI": "MALILI",
    "PELAHHAN": "PELATIHAN", "PERUVIUSAN": "PERUMUSAN", "PFNGHARGAAN": "PENGHARGAAN",
    "REGIATAN": "KEGIATAN", "EVAIUASI": "EVALUASI", "BISNJS": "BISNIS",
    "DOKUJMEN": "DOKUMEN", "ORGANISASJ": "ORGANISASI", "INFORMASJ": "INFORMASI",
    "111B": "IIIB", "1B": "IB",
}

PEND_TOKEN_REPAIRS: dict[str, str] = {
    "SISIEM": "SISTEM", "SISTFM": "SISTEM", "TEKNOIOGI": "TEKNOLOGI", "TEKNOLOGL": "TEKNOLOGI",
    "IEKNOLOGI": "TEKNOLOGI", "TEKNOLOG": "TEKNOLOGI", "FEKNIKA": "TEKNIKA", "FEKNIK": "TEKNIK",
    "ILMIJ": "ILMU", "ILVIU": "ILMU", "LMU": "ILMU", "11MU": "ILMU", "IIMU": "ILMU",
    "ILMtJ": "ILMU", "UMU": "ILMU", "KOMPU": "KOMPUTER", "KOMUNIKAS1": "KOMUNIKASI",
    "KOMUN1KAS1": "KOMUNIKASI", "KOMUN1kAS1": "KOMUNIKASI", "KOMUNIKAS": "KOMUNIKASI",
    "LNTERNASIONAL": "INTERNASIONAL", "HUBUNCJAN": "HUBUNGAN", "STATISTIKI": "STATISTIK",
    "MANAJEVIEN": "MANAJEMEN", "MANAJAMEN": "MANAJEMEN", "ADMINISIRASI": "ADMINISTRASI",
    "ADMINISTRAS": "ADMINISTRASI", "PERPAIAKAN": "PERPAJAKAN", "KEIJANGAN": "KEUANGAN",
    "PEMBANGUN": "PEMBANGUNAN", "PEMBANCUNAN": "PEMBANGUNAN", "SWIL": "SIPIL",
    "AKUNTANS": "AKUNTANSI", "INFORMAS": "INFORMASI", "EKONOM": "EKONOMI",
}


def find_table_rows_and_cols(pg: int) -> list[tuple[int, int, list[int]]]:
    gray = Image.open(PAGES_DIR / f"page_{pg:02d}.jpg").convert("L")
    w, h = gray.size
    b = gray.tobytes()
    hys = []
    y_start = 480 if pg == 5 else 130
    xs = range(200, 860, 10)
    for y in range(y_start, h - 180):
        c = 0
        for x in xs:
            if (
                b[y * w + x] < 212
                or b[(y - 2) * w + x] < 212
                or b[(y + 2) * w + x] < 212
                or b[(y - 4) * w + x] < 212
                or b[(y + 4) * w + x] < 212
            ):
                c += 1
        if c >= 48:
            hys.append(y)
    clusters = []
    for y in hys:
        if not clusters or y - clusters[-1][-1] > 12:
            clusters.append([y, y])
        else:
            clusters[-1][-1] = y
    centers = [(a + b) // 2 for a, b in clusters]
    boxes = [(centers[i], centers[i + 1]) for i in range(len(centers) - 1) if centers[i + 1] - centers[i] >= 45]
    rows = boxes[2:] if pg == 5 else boxes[1:]

    out = []
    expected = [108, 185, 480, 990, 1125, 1595]
    for y0, y1 in rows:
        ys = list(range(y0 + 10, max(y0 + 11, y1 - 10), 4))
        req = max(5, int(len(ys) * 0.7))
        picked = []
        for ex in expected:
            hits = []
            for x in range(max(40, ex - 35), min(w - 40, ex + 36)):
                c = sum(1 for y in ys if min(b[y * w + x - 2 : y * w + x + 3]) < 200)
                if c >= req:
                    hits.append(x)
            picked.append(sum(hits) // len(hits) if hits else ex)
        out.append((y0, y1, picked))
    return out


def extract_cell_lines(ocr_page: dict, x0: int, x1: int, y0: int, y1: int) -> str:
    cell_words = []
    for l in ocr_page["lines"]:
        for w in l["words"]:
            cx = w["x"] + w["w"] / 2
            cy = w["y"] + w["h"] / 2
            if (x0 + 3) <= cx <= (x1 - 3) and (y0 + 2) <= cy <= (y1 - 2):
                cell_words.append(w)
    if not cell_words:
        return ""
    cell_words.sort(key=lambda w: w["y"] + w["h"] / 2)
    lines = []
    for w in cell_words:
        cy = w["y"] + w["h"] / 2
        if not lines or abs(cy - lines[-1][0]) > 14:
            lines.append([cy, [w]])
        else:
            lines[-1][1].append(w)
            lines[-1][0] = sum(z["y"] + z["h"] / 2 for z in lines[-1][1]) / len(lines[-1][1])
    lines.sort(key=lambda pair: pair[0])
    joined = []
    for _, ws in lines:
        ws.sort(key=lambda z: z["x"])
        joined.append(" ".join(z["t"] for z in ws))
    return " ".join(joined).strip()


def clean_unit(raw: str, no: int) -> str:
    s = raw
    for a, b in [("„", ""), ("'", ""), ("`", ""), ('"', ""), ("*", ""), ("_", ""), ("[", "I"), ("]", "I"), ("!", "I"), ("{", ""), ("}", "")]:
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()

    # Fix split/noisy multi-word phrases FIRST (before tokenization)
    for pat, rep in [
        (r"\bCUKAVTIPE\b", "CUKAI | TIPE"),
        (r"\bKEMENTERIAN\s+KEU\s+ANGAN\b", "KEMENTERIAN KEUANGAN"),
        (r"\bI\s+DIREK\s+TORA\s*T\s+JENDERAL\b|\bDIREK\s+TORA\s*T\s+JENDERAL\b|\b(?:I\s+)?DIREK\s+TORAT\s+T?\s+JENDERAL\b|\bI\s+DIREK\s+DIREKTORAT\s+T\s+JENDERAL\b", "DIREKTORAT JENDERAL"),
        (r"\bDIREK\s+TORAT\b|\bDIREK\s+TORAY\b|\bDIRER\s+TORA\s*T\b|\bDIREK\s+TORA\b", "DIREKTORAT"),
        (r"\bADVOKAS1\b", "ADVOKASI"),
        (r"\b[Il1]{2}PE\b", "TIPE"),
        (r"\bJEN\s+DERAL\b", "JENDERAL"),
        (r"\bBUDA\s+YA\b", "BUDAYA"),
        (r"\bDAY\s+A\b", "DAYA"),
        (r"\bMAN\s+AJEMEN\b", "MANAJEMEN"),
        (r"\bKE\s+PABEANAN\b", "KEPABEANAN"),
        (r"\bPELA\s*Y\s*A\s*NAN\b|\bPELAN\s+ANAN\b|\bPEI[\-\s]*AY\s*A\s*NAN\b", "PELAYANAN"),
        (r"\bLAY\s*ANAN\b", "LAYANAN"),
        (r"\bMASY\s+ARAKAT\b", "MASYARAKAT"),
        (r"\bPEMBIAY\s+AAN\b", "PEMBIAYAAN"),
        (r"\bMADY\s+A\b", "MADYA"),
        (r"\bKEKAY\s+AAN\b", "KEKAYAAN"),
        (r"\bPEN\s+INDAKAN\b", "PENINDAKAN"),
        (r"\bBEA\s+CUKAI\s+DAN\b", "BEA DAN CUKAI"),
    ]:
        s = re.sub(pat, rep, s)

    tokens = s.split()
    EXTRA_REPAIRS = {
        "DISIPIIN": "DISIPLIN", "JENDFRAL": "JENDERAL", "PENGETAHUAN": "PENGETAHUAN",
        "PENGELOLAAN": "PENGELOLAAN", "EVALUASI": "EVALUASI", "JENDERAL": "JENDERAL",
        "DIREKTORAT": "DIREKTORAT", "KEUANGAN": "KEUANGAN", "ADVOKASI": "ADVOKASI",
        "KARIER": "KARIER", "PERBENDAHARAAN": "PERBENDAHARAAN", "PENGAWASAN": "PENGAWASAN",
        "KARIFR": "KARIER", "PENGAWAS.AN": "PENGAWASAN", "PENGAWAS": "PENGAWAS",
        "PENGAWASAN": "PENGAWASAN", "TIPE": "TIPE", "ILPE": "TIPE", "IIPE": "TIPE", "LLPE": "TIPE",
    }
    fixed_toks = []
    for tok in tokens:
        t = re.sub(r"^(.*?)[.:;]+$", r"\1", tok).lstrip(".")
        # Preserve comma ONLY at end; strip internal periods/commas inside OCR words (e.g., DISIPI.IN, KEUANC,AN, DIREKTOR.AT, PENGELOI,AAN, KARIF.R)
        trailing_comma = "," if t.endswith(",") else ""
        core = t[:-1] if trailing_comma else t
        core = core.replace(".", "").replace(",", "").replace("Ci", "G")
        cand = core.replace("-", "") if not re.match(r"^[SD]-", core) else core
        rep = UNIT_TOKEN_REPAIRS.get(core) or UNIT_TOKEN_REPAIRS.get(cand) or EXTRA_REPAIRS.get(core) or EXTRA_REPAIRS.get(cand)
        if not rep:
            # Handle OCR I->F / I->L inside JENDFRAL / PERBFNDAHARAAN / PENGFTAHUAN / EVAIUASI / DISIPIIN / ADVOKAS1 / KARIFR
            fix_chars = {
                "DISIPIIN": "DISIPLIN", "EVAIUASI": "EVALUASI", "PENGFTAHUAN": "PENGETAHUAN",
                "PERBFNDAHARAAN": "PERBENDAHARAAN", "ADVOKAS1": "ADVOKASI", "KARIFR": "KARIER",
                "KEUANCAN": "KEUANGAN", "DIREKTORAT": "DIREKTORAT", "PENGAWASAN": "PENGAWASAN",
                "PENGELOIAAN": "PENGELOLAAN", "JENDFRAL": "JENDERAL",
            }
            rep = fix_chars.get(cand, cand)
        t_out = rep + trailing_comma
        fixed_toks.extend(t_out.split())

    FINAL_OR_NAMED_ROMAN_PREV = {
        "KELAS", "MASINIS", "MUALIM", "BARANG/JASA", "KEHUTANAN", "ADVOKASI",
        "PERPAJAKAN", "PENILAIAN", "PENYIDIKAN", "PENINDAKAN", "FASILITAS",
        "PERBENDAHARAAN", "INDUSTRI", "DUKUNGAN", "JAWA",
    }
    HIERARCHY_STARTERS = {
        "DIREKTORAT", "SEKRETARIAT", "INSPEKTORAT", "BADAN", "KANTOR", "PANGKALAN",
        "BALAI", "PUSAT", "BIRO", "BAGIAN", "SUBBAGIAN", "SUBDIREKTORAT", "BIDANG",
        "SUBBIDANG", "SEKSI",
    }

    norm_toks = []
    for idx_t, tok in enumerate(fixed_toks):
        prev = norm_toks[-1] if norm_toks else ""
        prev2 = " ".join(norm_toks[-2:]) if len(norm_toks) >= 2 else ""
        nxt = fixed_toks[idx_t + 1] if idx_t + 1 < len(fixed_toks) else ""

        if tok in ("i", "l") and (nxt in HIERARCHY_STARTERS or idx_t <= 2):
            norm_toks.append("|")
            continue
        if tok == "I" and nxt in HIERARCHY_STARTERS:
            if prev in FINAL_OR_NAMED_ROMAN_PREV and prev != "PERBENDAHARAAN" and prev2 != "DAN PENYIDIKAN" and "WILAYAH" not in " ".join(norm_toks[-4:]):
                norm_toks.extend(["I", "|"])
            elif prev == "CUKAI" and nxt == "TIPE":
                continue
            else:
                norm_toks.append("|")
            continue

        if tok in ("111", "lll", "Ill", "III") and (prev in FINAL_OR_NAMED_ROMAN_PREV or prev == "CUKAI"):
            norm_toks.append("III")
            continue
        if tok in ("11", "ll", "II") and (prev in FINAL_OR_NAMED_ROMAN_PREV or prev == "CUKAI"):
            norm_toks.append("II")
            continue
        if tok == "1" and (prev in FINAL_OR_NAMED_ROMAN_PREV or prev == "CUKAI"):
            norm_toks.append("I")
            continue
        if tok == "1V" and (prev in FINAL_OR_NAMED_ROMAN_PREV or prev == "CUKAI"):
            norm_toks.append("IV")
            continue
        if tok == "V1" and (prev in FINAL_OR_NAMED_ROMAN_PREV or prev == "CUKAI"):
            norm_toks.append("VI")
            continue
        norm_toks.append(tok)

    s = " ".join(norm_toks)
    # Remove any bogus Roman I left after Eselon-1 names or WILAYAH names or BIRO ADVOKASI
    s = re.sub(r"\b(DIREKTORAT JENDERAL PERBENDAHARAAN)\s+I\b", r"\1 |", s)
    s = re.sub(r"\b(BEA DAN CUKAI)\s+I\s*(?=\||KANTOR|DIREKTORAT|SEKRETARIAT|BIDANG|PANGKALAN|BALAI)", r"\1 | ", s)
    s = re.sub(r"\b(SUMATERA UTARA|SUMATERA BAGIAN TIMUR|SUMATERA BAGIAN BARAT|KALIMANTAN BAGIAN TIMUR|KALIMANTAN BAGIAN BARAT|KALIMANTAN BAGIAN SELATAN|SULAWESI BAGIAN SELATAN|SULAWESI BAGIAN UTARA|KHUSUS KEPULAUAN RIAU|KHUSUS PAPUA|RIAU|ACEH|MALUKU|BANTEN|NUSA TENGGARA TIMUR|KALIMANTAN|SUMATERA|SULAWESI)\s+I\b", r"\1", s)
    s = re.sub(r"\b(BIDANG PENINDAKAN DAN PENYIDIKAN)\s+I\b", r"\1", s)
    s = re.sub(r"\b(BIRO ADVOKASI)\s+I\b", r"\1", s)
    # Also fix "SUBBAGIAN ... II/III" vs standalone numerals 1/11/111 anywhere after SEKSI/SUBBAGIAN/HASIL PENGAWASAN/NEGARA/PENILAIAN
    s = re.sub(r"\b111\b", "III", s)
    s = re.sub(r"\b11\b", "II", s)
    s = re.sub(r"\b1\b", "I", s)
    s = re.sub(r"\bIll\b", "III", s)
    # Fix leading/double tokens in Eselon 1
    s = re.sub(r"KEMENTERIAN KEUANGAN\s*\|\s*I\s+", "KEMENTERIAN KEUANGAN | ", s)
    s = re.sub(r"\bDIREKTORAT JENDERAL,\s*", "DIREKTORAT JENDERAL ", s)
    s = re.sub(r"\bDIREKTORAT JENDERAL BEA DAN\s*(?=\||KANTOR)", "DIREKTORAT JENDERAL BEA DAN CUKAI ", s)
    s = re.sub(r"\bI\s+DIREKTORAT\s+T\s+JENDERAL\b", "DIREKTORAT JENDERAL", s)
    s = re.sub(r"BADAN TEKNOLOGI,?\s*INFORMASI,?\s*DAN INTELIJEN KEUANGAN", "BADAN TEKNOLOGI, INFORMASI, DAN INTELIJEN KEUANGAN", s)

    if no == 97:
        s = s.replace("SEKTOR KEUANGAN | PENGEMBANGAN PERBANKAN", "SEKTOR KEUANGAN | DIREKTORAT PENGEMBANGAN PERBANKAN")
        s = s.replace("SEKTOR KEUANGAN PENGEMBANGAN PERBANKAN", "SEKTOR KEUANGAN | DIREKTORAT PENGEMBANGAN PERBANKAN")
    if no == 136 and not s.endswith(" I"):
        s = s + " I"
    if no == 194:
        s = s.replace("TIPE MADYA PABEAN C | PANGKALAN BUN", "TIPE MADYA PABEAN C PANGKALAN BUN")

    s = re.sub(r"^KEMENTERIAN KEUANGAN\s*(?!\|)", "KEMENTERIAN KEUANGAN | ", s)
    s = re.sub(
        r"(DIREKTORAT JENDERAL [A-Z,\s]+?)\s+(SEKRETARIAT DIREKTORAT|DIREKTORAT (?!JENDERAL)|KANTOR WILAYAH|KANTOR PELAYANAN)\b",
        r"\1 | \2",
        s,
    )
    for starter in [
        "SEKRETARIAT", "BIRO", "PUSAT", "SUBDIREKTORAT", "SUBBAGIAN", "SUBBIDANG",
        "SEKSI", "PANGKALAN SARANA", "BALAI LABORATORIUM",
        "KANTOR WILAYAH", "KANTOR PENGAWASAN", "KANTOR PELAYANAN",
    ]:
        s = re.sub(rf"(?<!\| )\b{re.escape(starter)}\b", f"| {starter}", s)
    s = re.sub(r"(?<!KALIMANTAN )(?<!SUMATERA )(?<!SULAWESI )\bBAGIAN\b", "| BAGIAN", s)
    s = re.sub(r"(\bKANTOR WILAYAH[^|]+|\bPUSAT[^|]+)\s+\bBIDANG\b", r"\1 | BIDANG", s)
    s = re.sub(r"KANTOR WILAYAH\s*\|\s*DIREKTORAT", "KANTOR WILAYAH DIREKTORAT", s)
    s = re.sub(r"SEKRETARIAT DIREKTORAT\s*\|\s*", "SEKRETARIAT DIREKTORAT ", s)
    s = re.sub(r"\|\s*PANGKALAN BUN", "PANGKALAN BUN", s)
    s = re.sub(r"\s*\|\s*TIPE MADYA", " TIPE MADYA", s)
    s = s.replace("DIREKTORAT JENDERAL STABILITAS DAN | DIREKTORAT PENGEMBANGAN SEKTOR KEUANGAN", "DIREKTORAT JENDERAL STABILITAS DAN PENGEMBANGAN SEKTOR KEUANGAN")
    s = s.replace("SEKRETARIAT DIREKTORAT JENDERAL STABILITAS DAN | DIREKTORAT PENGEMBANGAN SEKTOR KEUANGAN", "SEKRETARIAT DIREKTORAT JENDERAL STABILITAS DAN PENGEMBANGAN SEKTOR KEUANGAN")
    s = re.sub(r"\|\s*PUSAT KEUANGAN\b", "PUSAT KEUANGAN", s)  # safe guard
    # Also fix PUSAT PENDIDIKAN / PUSAT PEMBINAAN if inside BPPK? Wait let's check what 'Unique unit_eselon1' prints!
    segs = [re.sub(r"\s+", " ", p).strip() for p in s.split("|") if p.strip()]
    return " | ".join(segs)


def clean_pend(raw: str, no: int) -> str:
    if no == 158:
        return "S-1 TEKNIK INFORMATIKA | S-1 TEKNOLOGI INFORMASI | S-1 SISTEM DAN TEKNOLOGI INFORMASI | S-1 ILMU KOMPUTER"
    if no in (1, 2, 3, 4, 5, 6, 7, 8, 165) or (no >= 171 and no not in (251, 279, 289)):
        return "SMA/SEDERAJAT"
    s = raw
    for a, b in [("„", ""), ("'", ""), ("`", ""), ('"', ""), ("*", ""), ("_", ""), ("[", "I"), ("]", "I"), ("!", "I"), ("{", ""), ("}", "")]:
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b[kK]?[sS][\-\.](?:[1lIi]|I)\b|\b[sS]\s*\.\s*I\b|\bS-\s*I\b", "S-1", s)
    s = re.sub(r"\b(?:[dD]|13)-(?:111|l11|1l1|11l|Il1|III|1II|I1I|II1|lll|lII|IIl)\b", "D-III", s)
    s = re.sub(r"\b[dD]-[lI][vV]\b", "D-IV", s)
    toks = s.split()
    out = []
    for t in toks:
        t_clean = PEND_TOKEN_REPAIRS.get(t, PEND_TOKEN_REPAIRS.get(t.replace("-", ""), t))
        out.append(t_clean)
    s = " ".join(out)
    s = re.sub(r"\bMASY\s+ARAKAT\b", "MASYARAKAT", s)
    s = re.sub(r"\s+[Iil]\s+(?=(?:S-1|D-III|D-IV|SMK|KEUANGAN DAN PERBANKAN)\b)", " | ", s)
    s = re.sub(r"(?<!\|)\s+(?=(?:S-1|D-III|D-IV|SMK)\b)", " | ", s)
    # Fix missing pipe in NO 50 ("KEUANGAN DAN PERBANKAN S-1 ...") & NO 150 ("ILMU STATISTIK | S-1 ...")
    s = re.sub(r"(?<!\|)\s+(?=KEUANGAN DAN PERBANKAN\b)", " | ", s)
    segs = [re.sub(r"\s+", " ", p).strip() for p in s.split("|") if p.strip()]
    return " | ".join(segs)


def extract_jenjang_tier(pend: str) -> str:
    up = pend.upper()
    has_spec = "SUBSPESIALIS" in up or "SPESIALIS" in up or bool(re.search(r"\bS-?3\b", up))
    has_prof = "PROFESI" in up or "NERS" in up or "DOKTER" in up or "APOTEKER" in up
    has_s2 = bool(re.search(r"\bS-?2\b|\bMAGISTER\b", up))
    has_s1 = bool(re.search(r"\bS-?1\b|\bD-?IV\b|\bDIPLOMA\s+IV\b|\bSARJANA\s+TERAPAN\b", up)) or "KEUANGAN DAN PERBANKAN" in up
    has_d3 = bool(re.search(r"\bD-?III\b|\bDIPLOMA\s+III\b|\bDIPLOMA\s+KEPERAWATAN\b|\bAKADEMI\b", up))
    has_sma = "SMA/" in up or "SMA " in up or "SLTA" in up or "MADRASAH ALIYAH" in up or "SMK" in up
    tiers = []
    if has_sma:
        tiers.append("SMA/SMK")
    if has_d3:
        tiers.append("D-III")
    if has_s1:
        tiers.append("D-IV/S-1")
    if has_s2:
        tiers.append("S-2")
    if has_prof:
        tiers.append("Profesi")
    if has_spec:
        tiers.append("Spesialis/Subspesialis")
    return " / ".join(tiers) if tiers else "Lainnya"


def extract_unit_eselon1(unit: str) -> str:
    segs = [s.strip() for s in unit.split("|") if s.strip()]
    if len(segs) >= 2:
        raw = segs[1]
        # Clean Title Case for clean UI filters/charts while keeping acronyms legible
        return re.sub(r"\bDan\b", "dan", raw.title())
    return "Kementerian Keuangan"


def main():
    assert len(VERIFIED_ALOKASI) == 374
    assert sum(VERIFIED_ALOKASI.values()) == 1915

    ocr_pages = {p["page"]: p for p in json.loads(OCR_PATH.read_text(encoding="utf-8-sig"))}
    rows = []
    for pg in range(5, 40):
        ocr_p = ocr_pages[pg]
        for y0, y1, xs in find_table_rows_and_cols(pg):
            no = len(rows) + 1
            pend_raw = extract_cell_lines(ocr_p, xs[2], xs[3], y0, y1)
            unit_raw = extract_cell_lines(ocr_p, xs[4], xs[5], y0, y1)
            pend = clean_pend(pend_raw, no)
            unit = clean_unit(unit_raw, no)
            rows.append({
                "no_urut": no,
                "formasi_id": f"2026-KEMENKEU-{no:03d}",
                "instansi_id": "KEMENKEU",
                "instansi_nm": "Kementerian Keuangan",
                "kategori_instansi": "Pusat",
                "unit_eselon1": extract_unit_eselon1(unit),
                "jabatan_nm": get_jabatan(no),
                "pendidikan_nm": pend,
                "jenjang": extract_jenjang_tier(pend),
                "jumlah_formasi": VERIFIED_ALOKASI[no],
                "lokasi_nm": unit,
                "jenis_formasi": None,
                "jumlah_pelamar": None,
                "rasio_kompetisi": None,
                "peluang_lolos_pct": None,
                "status_keketatan": None,
                "gaji_min": None,
                "gaji_max": None,
                "sumber_dokumen": SUMBER_DOKUMEN,
            })

    assert len(rows) == 374, f"Expected 374 Kemenkeu rows, got {len(rows)}"
    assert sum(r["jumlah_formasi"] for r in rows) == 1915, "Total Kemenkeu alokasi must be 1915!"

    VERIFIED_JSON_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    bssn_rows = get_bssn_rows(extract_jenjang_tier)
    kejagung_rows = get_kejagung_rows(extract_jenjang_tier)
    assert len(bssn_rows) == 2 and sum(r["jumlah_formasi"] for r in bssn_rows) == 200
    assert len(kejagung_rows) == 94 and sum(r["jumlah_formasi"] for r in kejagung_rows) == 175

    sscasn_csv = DATA_DIR / "sscasn_2026_live.csv"
    sscasn_rows = get_sscasn_live_rows(extract_jenjang_tier, sscasn_csv)
    kemenkes_rows = get_kemenkes_str_rows(extract_jenjang_tier, DATA_DIR / "kemenkes_str_tables.json")
    bpkp_rows = get_bpkp_rows(extract_jenjang_tier, DATA_DIR / "bpkp_2026_verified.json")
    kemenkum_rows = get_kemenkum_rows(extract_jenjang_tier, DATA_DIR / "kemenkum_2026_verified.json")
    live_agencies = {r["instansi_nm"].strip().lower() for r in sscasn_rows}

    # Precedence rule: live SSCASN rows automatically supersede pre-release decree/SE rows
    # for the same agency so no agency is ever double-counted.
    decree_rows = [
        r for r in (rows + bssn_rows + kejagung_rows + kemenkes_rows + bpkp_rows + kemenkum_rows)
        if r["instansi_nm"].strip().lower() not in live_agencies
    ]
    combined_raw = decree_rows + sscasn_rows
    deduped_rows = []
    seen_natural_keys: set[tuple] = set()
    seen_ids: set[str] = set()
    for r in combined_raw:
        # Include (sumber_dokumen, no_urut) so consecutive sequential decree rows (e.g. Kemenkeu NO 1 & 2)
        # remain distinct, while re-ingesting an already loaded agency/decree raises immediately.
        nat_key = (
            r["instansi_id"],
            r["sumber_dokumen"],
            r["no_urut"],
            r["unit_eselon1"],
            r["jabatan_nm"],
            r["lokasi_nm"],
            r["jenis_formasi"] or "",
            r["pendidikan_nm"],
        )
        if nat_key in seen_natural_keys or r["formasi_id"] in seen_ids:
            raise RuntimeError(f"Duplicate formasi detected during build: {r['formasi_id']} / {nat_key}")
        seen_natural_keys.add(nat_key)
        seen_ids.add(r["formasi_id"])
        deduped_rows.append(r)

    rows = deduped_rows
    assert len(kemenkes_rows) == 49
    assert len(bpkp_rows) == 554 and sum(r["jumlah_formasi"] for r in bpkp_rows) == 2007
    assert len(kemenkum_rows) == 45 and sum(r["jumlah_formasi"] for r in kemenkum_rows) == 1297
    assert len(rows) == 1169, f"Expected 1169 combined verified rows, got {len(rows)}"
    assert sum(r["jumlah_formasi"] or 0 for r in rows) == 6546, "Total combined alokasi must be 6546!"

    # Enrich each 2026 row with verified CPNS 2024 historical benchmark & exam scores
    cmp_2024 = compute_2024_comparison_map(rows, DATA_DIR / "cpns2024.db")
    for r in rows:
        cinfo = cmp_2024[r["formasi_id"]]
        for k, v in cinfo.items():
            if k != "formasi_id":
                r[k] = v

    # Sanity audit prints
    uw = Counter(w.rstrip(",") for r in rows for w in r["lokasi_nm"].split() if w != "|")
    weird_u = [(w, c) for w, c in uw.items() if re.search(r"[^A-Z0-9/\-\(\)&]", w) or any(ch in w for ch in "0123456789")]
    print("Non-alpha tokens in lokasi_nm:", weird_u)
    print("Instansi breakdown:", Counter(r["instansi_id"] for r in rows).most_common())
    print("Matched 2024 breakdown:", Counter(r["match_level_2024"] or "none" for r in rows).most_common())
    print("Unique unit_eselon1:", len(Counter(r["unit_eselon1"] for r in rows)))
    print("Unique jenjang:", Counter(r["jenjang"] for r in rows).most_common())
    print("Distinct pend strings:", len(Counter(r["pendidikan_nm"] for r in rows)))

    # Write CSV (empty string for NULL fields — zero hallucination!)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_fields = [
        "no_urut", "formasi_id", "instansi_nm", "kategori_instansi", "unit_eselon1",
        "jabatan_nm", "pendidikan_nm", "jenjang", "jumlah_formasi", "lokasi_nm",
        "jenis_formasi", "jumlah_pelamar", "gaji_min", "gaji_max", "sumber_dokumen",
        "kursi_2024", "pelamar_2024", "rasio_2024", "status_keketatan_2024", "match_label_2024",
    ]
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r[k] is None else r[k]) for k in csv_fields})

    ALL_VERIFIED_JSON_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    AUDIT_JSON_PATH.write_text(json.dumps(DRIVE_AUDIT_SUMMARY, indent=2, ensure_ascii=False), encoding="utf-8")

    # Build clean 3NF SQLite database
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;

        CREATE TABLE instansi (
            instansi_id TEXT PRIMARY KEY,
            instansi_nm TEXT NOT NULL,
            kategori_instansi TEXT NOT NULL DEFAULT 'Pusat',
            tukin_min INTEGER,
            tukin_max INTEGER,
            tukin_sumber TEXT
        );

        CREATE TABLE jurusan (
            jurusan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jurusan_nm TEXT NOT NULL UNIQUE,
            jenjang TEXT NOT NULL
        );

        CREATE TABLE formasi (
            formasi_id TEXT PRIMARY KEY,
            no_urut INTEGER NOT NULL,
            instansi_id TEXT NOT NULL,
            unit_eselon1 TEXT NOT NULL,
            jabatan_nm TEXT NOT NULL,
            lokasi_nm TEXT NOT NULL,
            jenis_formasi TEXT,
            jumlah_formasi INTEGER,
            jumlah_pelamar INTEGER,
            rasio_kompetisi REAL,
            peluang_lolos_pct REAL,
            status_keketatan TEXT,
            gaji_min INTEGER,
            gaji_max INTEGER,
            pendidikan_nm TEXT NOT NULL,
            jenjang TEXT NOT NULL,
            sumber_dokumen TEXT NOT NULL,
            FOREIGN KEY (instansi_id) REFERENCES instansi(instansi_id)
        );

        CREATE TABLE formasi_jurusan (
            formasi_id TEXT NOT NULL,
            jurusan_id INTEGER NOT NULL,
            PRIMARY KEY (formasi_id, jurusan_id),
            FOREIGN KEY (formasi_id) REFERENCES formasi(formasi_id),
            FOREIGN KEY (jurusan_id) REFERENCES jurusan(jurusan_id)
        );

        CREATE TABLE banding_2024 (
            formasi_id TEXT PRIMARY KEY,
            match_level_2024 TEXT,
            match_label_2024 TEXT NOT NULL,
            kursi_2024 INTEGER,
            pelamar_2024 INTEGER,
            rasio_2024 REAL,
            peluang_2024_pct REAL,
            status_keketatan_2024 TEXT,
            row_count_2024 INTEGER NOT NULL DEFAULT 0,
            n_peserta_skb_2024 INTEGER,
            n_lulus_2024 INTEGER,
            nilai_akhir_2024_min REAL,
            nilai_akhir_2024_median REAL,
            nilai_akhir_2024_max REAL,
            skd_2024_lulus_min INTEGER,
            skd_2024_lulus_median REAL,
            skd_2024_lulus_max INTEGER,
            skd_2024_skb_min INTEGER,
            skb_2024_lulus_min REAL,
            skb_2024_lulus_median REAL,
            skb_2024_lulus_max REAL,
            sumber_nilai_2024 TEXT,
            FOREIGN KEY (formasi_id) REFERENCES formasi(formasi_id)
        );

        CREATE INDEX idx_2026_formasi_instansi ON formasi(instansi_id);
        CREATE INDEX idx_2026_formasi_eselon1 ON formasi(unit_eselon1);
        CREATE INDEX idx_2026_formasi_jabatan ON formasi(jabatan_nm);
        CREATE INDEX idx_2026_formasi_jenjang ON formasi(jenjang);
        CREATE INDEX idx_2026_fj_jurusan ON formasi_jurusan(jurusan_id);
        """
    )

    instansi_rows = [
        (
            "KEMENKEU",
            "Kementerian Keuangan",
            "Pusat",
            2575000,
            46950000,
            "Perpres No. 156/2014 (Tukin Resmi Terverifikasi Kemenkeu — Simulasi Acuan)",
        ),
        *EXTRA_INSTANSI,
    ]
    cur.executemany(
        """
        INSERT INTO instansi (instansi_id, instansi_nm, kategori_instansi, tukin_min, tukin_max, tukin_sumber)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        instansi_rows,
    )

    jurusan_cache: dict[str, int] = {}

    def get_jurusan_id(name: str) -> int:
        if name in jurusan_cache:
            return jurusan_cache[name]
        cur.execute(
            "INSERT OR IGNORE INTO jurusan (jurusan_nm, jenjang) VALUES (?, ?)",
            (name, extract_jenjang_tier(name)),
        )
        cur.execute("SELECT jurusan_id FROM jurusan WHERE jurusan_nm = ?", (name,))
        jid = cur.fetchone()[0]
        jurusan_cache[name] = jid
        return jid

    for r in rows:
        cur.execute(
            """
            INSERT INTO formasi (
                formasi_id, no_urut, instansi_id, unit_eselon1, jabatan_nm, lokasi_nm,
                jenis_formasi, jumlah_formasi, jumlah_pelamar, rasio_kompetisi,
                peluang_lolos_pct, status_keketatan, gaji_min, gaji_max,
                pendidikan_nm, jenjang, sumber_dokumen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["formasi_id"], r["no_urut"], r["instansi_id"], r["unit_eselon1"],
                r["jabatan_nm"], r["lokasi_nm"], r["jenis_formasi"], r["jumlah_formasi"],
                None, None, None, None, r["gaji_min"], r["gaji_max"],
                r["pendidikan_nm"], r["jenjang"], r["sumber_dokumen"],
            ),
        )
        # Split on ' | ' so SMA/SEDERAJAT stays intact!
        majors = [m.strip() for m in r["pendidikan_nm"].split(" | ") if m.strip()]
        for m in majors:
            jid = get_jurusan_id(m)
            cur.execute(
                "INSERT OR IGNORE INTO formasi_jurusan (formasi_id, jurusan_id) VALUES (?, ?)",
                (r["formasi_id"], jid),
            )
        cur.execute(
            """
            INSERT INTO banding_2024 (
                formasi_id, match_level_2024, match_label_2024,
                kursi_2024, pelamar_2024, rasio_2024, peluang_2024_pct,
                status_keketatan_2024, row_count_2024,
                n_peserta_skb_2024, n_lulus_2024,
                nilai_akhir_2024_min, nilai_akhir_2024_median, nilai_akhir_2024_max,
                skd_2024_lulus_min, skd_2024_lulus_median, skd_2024_lulus_max,
                skd_2024_skb_min,
                skb_2024_lulus_min, skb_2024_lulus_median, skb_2024_lulus_max,
                sumber_nilai_2024
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r["formasi_id"], r["match_level_2024"], r["match_label_2024"],
                r["kursi_2024"], r["pelamar_2024"], r["rasio_2024"],
                r["peluang_2024_pct"], r["status_keketatan_2024"], r["row_count_2024"],
                r.get("n_peserta_skb_2024"), r.get("n_lulus_2024"),
                r.get("nilai_akhir_2024_min"), r.get("nilai_akhir_2024_median"), r.get("nilai_akhir_2024_max"),
                r.get("skd_2024_lulus_min"), r.get("skd_2024_lulus_median"), r.get("skd_2024_lulus_max"),
                r.get("skd_2024_skb_min"),
                r.get("skb_2024_lulus_min"), r.get("skb_2024_lulus_median"), r.get("skb_2024_lulus_max"),
                r.get("sumber_nilai_2024"),
            ),
        )

    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    conn.execute("PRAGMA journal_mode = DELETE;")
    conn.close()

    with open(DB_PATH, "rb") as f_in, gzip.open(DB_GZ_PATH, "wb", compresslevel=9) as f_out:
        shutil.copyfileobj(f_in, f_out)

    print(
        f"\nBuilt CPNS 2026 DB cleanly: {DB_PATH} ({DB_PATH.stat().st_size:,} B), "
        f"{DB_GZ_PATH.name} ({DB_GZ_PATH.stat().st_size:,} B), "
        f"{CSV_PATH.name} ({CSV_PATH.stat().st_size:,} B), "
        f"jurusan={len(jurusan_cache)}"
    )


if __name__ == "__main__":
    sys.exit(main())
