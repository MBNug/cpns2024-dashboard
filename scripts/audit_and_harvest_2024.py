"""Headless harvester and REKAP auditor for CPNS 2024 score PDFs (Phase 2).

Runs completely in background CLI without touching any IDE browser sidebar.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any

import httpx
import pypdfium2 as pdfium


SCORES_ROOT = Path(r"D:\AG Files\cpns2026-scraper\data\refs\scores_2024")
REGISTRY_PATH = SCORES_ROOT / "registry_544.json"
CHROME_BIN = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"}


def _count_pdf_chunk(args: tuple[str, int, int]) -> tuple[int, int, int, str | None, str | None]:
    path_str, s, e = args
    d = pdfium.PdfDocument(path_str)
    rekap = ringkas = rincian = 0
    ins_first = None
    jab_first = None
    for i in range(s, e):
        t = d[i].get_textpage().get_text_range()
        if "REKAP HASIL INTEGRASI" in t:
            rekap += 1
            if "(RINCIAN)" in t:
                rincian += 1
            else:
                ringkas += 1
            if ins_first is None:
                mi = re.search(r"Instansi\s*:\s*([^\r\n]+)", t)
                mj = re.search(r"Jabatan Formasi\s*:?\s*([^\r\n]+)", t)
                ins_first = mi.group(1).strip() if mi else None
                jab_first = mj.group(1).strip() if mj else None
    return rekap, ringkas, rincian, ins_first, jab_first


def audit_pdf(path: Path) -> dict[str, Any]:
    sz = path.stat().st_size
    if sz < 100 or not path.read_bytes()[:4].startswith(b"%PDF"):
        return {"file": str(path), "size": sz, "valid_pdf": False}
    try:
        d = pdfium.PdfDocument(str(path))
        n = len(d)
        p1 = d[0].get_textpage().get_text_range().replace("\r\n", " ").replace("\n", " ")[:200]
        d.close()
    except Exception as exc:
        return {"file": str(path), "size": sz, "valid_pdf": False, "error": str(exc)}

    if n >= 300:
        workers = 6
        chunk = max(80, (n + workers - 1) // workers)
        tasks = [(str(path), i, min(n, i + chunk)) for i in range(0, n, chunk)]
        rekap = ringkas = rincian = 0
        ins_first = jab_first = None
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for r, rg, rc, i1, j1 in pool.map(_count_pdf_chunk, tasks):
                rekap += r
                ringkas += rg
                rincian += rc
                if ins_first is None and i1:
                    ins_first, jab_first = i1, j1
    else:
        rekap, ringkas, rincian, ins_first, jab_first = _count_pdf_chunk((str(path), 0, n))

    return {
        "file": str(path.relative_to(SCORES_ROOT)),
        "size": sz,
        "valid_pdf": True,
        "pages": n,
        "rekap_total": rekap,
        "rekap_ringkas": ringkas,
        "rekap_rincian": rincian,
        "instansi_hdr": ins_first,
        "first_jabatan": jab_first,
        "p1_snippet": p1,
    }


def chrome_dump_dom(url: str, wait_ms: int = 7000, timeout_s: int = 25) -> str:
    if not CHROME_BIN.exists():
        return ""
    with tempfile.TemporaryDirectory() as tmpd:
        res = subprocess.run(
            [
                str(CHROME_BIN),
                f"--user-data-dir={tmpd}",
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--virtual-time-budget={wait_ms}",
                "--dump-dom",
                url,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout_s,
        )
        return res.stdout or ""


def download_gdrive_file(file_id: str, out_path: Path, client: httpx.Client) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = client.get(f"https://drive.google.com/uc?export=download&id={file_id}", timeout=45.0)
    if r.content[:4] == b"%PDF":
        out_path.write_bytes(r.content)
        return out_path.stat().st_size
    m_act = re.search(r'action="(https://drive\.usercontent\.google\.com/download[^"]*)"', r.text)
    inputs = dict(re.findall(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', r.text))
    if m_act:
        with client.stream("GET", m_act.group(1), params=inputs, timeout=180.0) as r2:
            with open(out_path, "wb") as f:
                for ch in r2.iter_bytes():
                    f.write(ch)
        return out_path.stat().st_size
    with client.stream(
        "GET",
        f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
        timeout=180.0,
    ) as r3:
        with open(out_path, "wb") as f:
            for ch in r3.iter_bytes():
                f.write(ch)
    return out_path.stat().st_size


def list_gdrive_folder(folder_id: str) -> list[tuple[str, str]]:
    """Use isolated headless Chrome to extract (file_id, title) pairs inside a public Drive folder."""
    dom = chrome_dump_dom(f"https://drive.google.com/drive/folders/{folder_id}", wait_ms=8000, timeout_s=28)
    # Match data-id="..." and nearest title or file links
    found: dict[str, str] = {}
    for m in re.finditer(r'data-id="([A-Za-z0-9_-]{20,})"', dom):
        fid = m.group(1)
        if fid == folder_id:
            continue
        snippet = dom[m.start() : m.start() + 900]
        mt = re.search(r'(?:aria-label|data-tooltip|title)="([^"]+)"', snippet)
        label = mt.group(1).strip() if mt else ""
        if label or fid not in found:
            found[fid] = label
    return [(fid, lbl) for fid, lbl in found.items()]


def cmd_audit(subpath: str) -> None:
    target = SCORES_ROOT / subpath
    pdfs = sorted(target.rglob("*.pdf"))
    reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    by_slug = {f"{a['kode_instansi']}_{a['slug']}": a for a in reg["agencies"]}
    by_kode = {a["kode_instansi"]: a for a in reg["agencies"]}
    for p in pdfs:
        info = audit_pdf(p)
        folder = p.parent.name
        m_k = re.match(r"(INS-\d+)", folder)
        ag = by_kode.get(m_k.group(1)) if m_k else None
        exp = f" (db_formasi={ag['total_formasi']}, db_kuota={ag['total_kuota']:,})" if ag else ""
        if not info["valid_pdf"]:
            print(f"[BAD] {p.name}: sz={info['size']} err={info.get('error')}", flush=True)
        else:
            print(
                f"[OK] {info['file']} | {info['size']:,} B | pages={info['pages']:,} | "
                f"rekap={info['rekap_total']:,} (ringkas={info['rekap_ringkas']:,}, rincian={info['rekap_rincian']:,}){exp} | {info['instansi_hdr']}",
                flush=True,
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_a = sub.add_parser("audit")
    p_a.add_argument("--subdir", default="pusat")
    p_gd = sub.add_parser("gdrive-list")
    p_gd.add_argument("folder_id")
    p_dom = sub.add_parser("dom-links")
    p_dom.add_argument("url")

    args = parser.parse_args()
    if args.cmd == "audit":
        cmd_audit(args.subdir)
    elif args.cmd == "gdrive-list":
        for fid, lbl in list_gdrive_folder(args.folder_id):
            print(f"  {fid} | {lbl}", flush=True)
    elif args.cmd == "dom-links":
        dom = chrome_dump_dom(args.url)
        hits = sorted(set(re.findall(r'https?://[^\s"\'<>\\]+', dom)))
        for h in hits:
            if any(k in h.lower() for k in [".pdf", "drive.google", "download", "unduh", "sharepoint", "s.id", "bit.ly", "lampiran"]):
                print(" ", h[:180], flush=True)


if __name__ == "__main__":
    main()
