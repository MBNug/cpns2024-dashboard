"""
Batch Downloader for Official TPP & Tukin Regulation PDFs from BPK RI / JDIHN.
Downloads official PDFs for all 544 CPNS 2024 agencies to data/regulasi_pdf/.
Creates a manifest mapping each agency to its PDF file for easy Google Drive upload.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cpns2024.db"
PDF_DIR = BASE_DIR / "data" / "regulasi_pdf"
MANIFEST_PATH = PDF_DIR / "manifest_download.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}


def sanitize_filename(name: str) -> str:
    """Sanitize string to safe filesystem filename."""
    s = re.sub(r'[\\/*?:"<>|]', "", name)
    s = re.sub(r"\s+", "_", s).strip("_")
    return s[:120]


def clean_agency_name(nama: str) -> str:
    return (
        nama.replace("Pemerintah Daerah Daerah Istimewa ", "")
        .replace("Pemerintah Provinsi ", "")
        .replace("Pemerintah Kota ", "")
        .replace("Pemerintah Kab. ", "")
        .replace("Pemerintah ", "")
        .strip()
    )


def fetch_pdf_for_agency(agency: dict) -> dict:
    """Fetch official regulation PDF from BPK RI for a single agency."""
    i_id = agency["instansi_id"]
    nama = agency["nama_instansi"]
    reg = agency["regulasi_tukin"] or ""
    kat = agency["kategori_instansi"]

    # Determine search keyword
    clean_reg = re.sub(r"\(.*?\)", "", reg).strip()
    clean_name = clean_agency_name(nama)

    if kat == "Pusat":
        query = f"{clean_reg} {nama}"
    elif "Provinsi" in kat:
        query = f"{clean_reg} {nama}" if clean_reg else f"Tambahan Penghasilan Pegawai Provinsi {clean_name}"
    else:
        is_kota = "Kota" in nama
        query = f"{clean_reg}" if ("Perbup" in clean_reg or "Perwali" in clean_reg) else f"Tambahan Penghasilan Pegawai {'Kota' if is_kota else 'Kabupaten'} {clean_name}"

    search_url = f"https://peraturan.bpk.go.id/Search?keywords={urllib.parse.quote_plus(query)}"
    
    result = {
        "instansi_id": i_id,
        "nama_instansi": nama,
        "kategori_instansi": kat,
        "regulasi_tukin": reg,
        "query": query,
        "search_url": search_url,
        "detail_url": None,
        "pdf_url": None,
        "filename": None,
        "size_bytes": 0,
        "status": "pending"
    }

    try:
        # Step 1: Search BPK
        req = urllib.request.Request(search_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        details_links = re.findall(r'href=\"(/Details/\d+/[^\"]+)\"', html)
        if not details_links:
            # Fallback broader search
            fallback_query = f"Tambahan Penghasilan Pegawai {clean_name}"
            fb_url = f"https://peraturan.bpk.go.id/Search?keywords={urllib.parse.quote_plus(fallback_query)}"
            req_fb = urllib.request.Request(fb_url, headers=HEADERS)
            with urllib.request.urlopen(req_fb, timeout=12) as resp_fb:
                html_fb = resp_fb.read().decode("utf-8", errors="ignore")
            details_links = re.findall(r'href=\"(/Details/\d+/[^\"]+)\"', html_fb)

        if not details_links:
            result["status"] = "not_found"
            return result

        detail_url = "https://peraturan.bpk.go.id" + details_links[0]
        result["detail_url"] = detail_url

        # Step 2: Extract PDF download URL
        time.sleep(0.3)
        req2 = urllib.request.Request(detail_url, headers=HEADERS)
        with urllib.request.urlopen(req2, timeout=12) as resp2:
            html2 = resp2.read().decode("utf-8", errors="ignore")

        pdf_links = re.findall(r'href=\"(/Download/[^\"]+)\"', html2)
        if not pdf_links:
            result["status"] = "pdf_missing_in_page"
            return result

        pdf_url = "https://peraturan.bpk.go.id" + pdf_links[0]
        result["pdf_url"] = pdf_url

        # Step 3: Download PDF
        safe_agency = sanitize_filename(nama)
        safe_reg = sanitize_filename(clean_reg if clean_reg else "Regulasi")
        filename = f"{i_id}_{safe_agency}_{safe_reg}.pdf"
        out_path = PDF_DIR / filename

        # Skip if already downloaded and valid
        if out_path.exists() and out_path.stat().st_size > 5000:
            result["filename"] = filename
            result["size_bytes"] = out_path.stat().st_size
            result["status"] = "already_downloaded"
            return result

        time.sleep(0.3)
        req3 = urllib.request.Request(pdf_url, headers=HEADERS)
        with urllib.request.urlopen(req3, timeout=30) as resp3:
            content = resp3.read()

        if len(content) > 1000:
            out_path.write_bytes(content)
            result["filename"] = filename
            result["size_bytes"] = len(content)
            result["status"] = "downloaded"
        else:
            result["status"] = "download_too_small"

    except Exception as e:
        result["status"] = f"error: {str(e)[:100]}"

    return result


def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing manifest
    manifest = {}
    if MANIFEST_PATH.exists():
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            print(f"[INFO] Loaded existing manifest with {len(manifest)} entries.")
        except Exception:
            manifest = {}

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT instansi_id, nama_instansi, kategori_instansi, regulasi_tukin FROM instansi ORDER BY instansi_id")
    agencies = [dict(row) for row in cur.fetchall()]
    conn.close()

    total = len(agencies)
    print(f"=== DOWNLOADING OFFICIAL TPP & TUKIN PDFs ({total} AGENCIES) ===")
    print(f"Destination: {PDF_DIR}")

    completed_count = 0
    success_count = sum(1 for m in manifest.values() if m.get("status") in ("downloaded", "already_downloaded"))

    # Filter out already successfully downloaded
    to_download = []
    for a in agencies:
        existing = manifest.get(str(a["instansi_id"]))
        if existing and existing.get("status") in ("downloaded", "already_downloaded"):
            pdf_file = PDF_DIR / (existing.get("filename") or "")
            if pdf_file.exists() and pdf_file.stat().st_size > 5000:
                continue
        to_download.append(a)

    print(f"[STATUS] {success_count}/{total} already downloaded. {len(to_download)} remaining to download.")

    if not to_download:
        print("[SUCCESS] All agencies already downloaded!")
        return

    # Use polite 5 workers
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_pdf_for_agency, a): a for a in to_download}

        for future in as_completed(futures):
            res = future.result()
            i_id_str = str(res["instansi_id"])
            manifest[i_id_str] = res
            completed_count += 1
            cur_total_done = success_count + completed_count

            status = res["status"]
            nama = res["nama_instansi"]
            size_kb = res["size_bytes"] / 1024

            if status in ("downloaded", "already_downloaded"):
                print(f"[{cur_total_done}/{total}] OK: {nama} ({size_kb:.1f} KB) -> {res.get('filename')}")
            else:
                print(f"[{cur_total_done}/{total}] {status.upper()}: {nama}")

            # Save manifest every 10 downloads
            if completed_count % 10 == 0 or completed_count == len(to_download):
                with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
                    json.dump(manifest, f, indent=2, ensure_ascii=False)

    # Final manifest save
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    final_success = sum(1 for m in manifest.values() if m.get("status") in ("downloaded", "already_downloaded"))
    total_size_mb = sum((PDF_DIR / m["filename"]).stat().st_size for m in manifest.values() if m.get("filename") and (PDF_DIR / m["filename"]).exists()) / (1024 * 1024)

    print("\n=======================================================")
    print("  DOWNLOAD REKAPITULASI DOKUMEN TPP & TUKIN RESMI")
    print("=======================================================")
    print(f"Total Instansi: {total}")
    print(f"Berhasil Didownload: {final_success} PDF")
    print(f"Total Ukuran File: {total_size_mb:.2f} MB")
    print(f"Lokasi Folder: {PDF_DIR}")
    print(f"File Manifest: {MANIFEST_PATH}")
    print("=======================================================")


if __name__ == "__main__":
    main()
