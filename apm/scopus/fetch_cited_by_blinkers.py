"""
Fetch all "cited-by" (child) papers for every parent paper in all_blinkers.csv,
then produce a single deduplicated RIS file ready for Zotero import.

WHAT IT DOES
------------
For each of the 62 parent papers in all_blinkers.csv (column "Url"):

    1.  Extract the numeric Scopus paper ID from the URL.
    2.  Run the advanced Scopus search:  REFEID(2-s2.0-{paper_id})
        This returns every paper that cites that parent.
    3.  Export the results as a .ris file saved in tutorial/all_cite_blink/.
    4.  After all parents are processed, combine every individual .ris into one
        file, removing duplicates (same paper may cite multiple parents).

RESUME SUPPORT
--------------
The script records progress in  tutorial/all_cite_blink/status.csv.
If it is interrupted, simply re-run — already-downloaded papers are skipped.
Use  --force  to re-download everything from scratch.

USAGE
-----
    # From the project root:
    python tutorial/fetch_cited_by_blinkers.py
    python tutorial/fetch_cited_by_blinkers.py --force
    python tutorial/fetch_cited_by_blinkers.py --verbose

OUTPUT
------
tutorial/all_cite_blink/
    {paper_id}_cited_by.ris         <- one RIS per parent paper (may be absent
                                       if nobody cites that paper yet)
    all_blinkers_cite_dedup.ris     <- ZOTERO-READY: all citing papers combined
                                       and deduplicated (DOI > EID > title+year)
    duplicates_report.csv           <- which entries were removed as duplicates
    status.csv                      <- per-paper download status / counts

ZOTERO IMPORT
-------------
    Zotero Desktop  →  File  →  Import
    Select:  tutorial/all_cite_blink/all_blinkers_cite_dedup.ris
    Import into collection: e.g. "all_blinkers_cited_by_2026"

PREREQUISITES
-------------
1.  Selenium Chrome profile at  C:\\selenium\\chrome-profile  already logged
    in to Scopus.  If not yet logged in, run Chrome once with:

        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            --user-data-dir=C:\\selenium\\chrome-profile
            --profile-directory=Default

    Navigate to https://www.scopus.com, authenticate, tick "Keep me signed in",
    close Chrome.  Subsequent runs will reuse the saved session automatically.

2.  scopus_config.json in the project root (created automatically from defaults
    if absent).

3.  Python packages:  pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import csv
import logging
import shutil
import sys
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scopus_automation.browser import build_driver, set_download_dir
from scopus_automation.config import ScopusConfig
from scopus_automation.cited_by import download_cited_by, _extract_paper_id
from scopus_automation.dedupe import combine_ris_directory
from scopus_automation.logging_setup import setup_logging

log = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────────
INPUT_CSV     = PROJECT_ROOT / "all_blinkers.csv"
OUTPUT_DIR    = PROJECT_ROOT / "output" / "fetch_cited_by_blinkers"
STATUS_CSV    = OUTPUT_DIR / "status.csv"
DEDUP_RIS     = OUTPUT_DIR / "all_blinkers_cite_dedup.ris"
LOGS_DIR      = OUTPUT_DIR / "logs"

URL_COLUMN    = "Url"           # column name in all_blinkers.csv


# ── Status helpers ─────────────────────────────────────────────────────────────

def _load_status() -> dict[str, dict]:
    """Return {paper_id: row_dict} from status.csv (if it exists)."""
    if not STATUS_CSV.exists():
        return {}
    with STATUS_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return {row["paper_id"]: row for row in reader}


def _save_status(rows: list[dict]) -> None:
    STATUS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "paper_id", "title", "url",
        "downloaded", "downloaded_at",
        "ris_file", "result_count", "error",
    ]
    with STATUS_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ── Main ───────────────────────────────────────────────────────────────────────

def _load_input() -> list[dict]:
    """Read all_blinkers.csv and return rows that have a Scopus URL."""
    rows = []
    with INPUT_CSV.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            url = row.get(URL_COLUMN, "").strip()
            if url and url.lower() not in ("nan", ""):
                rows.append(row)
    log.info("Loaded %d papers from %s", len(rows), INPUT_CSV)
    return rows


def _title_preview(row: dict) -> str:
    return (row.get("Title") or "")[:70]


def run(force: bool = False) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    config = ScopusConfig.from_file(str(PROJECT_ROOT / "setting/scopus_setup/scopus_config.json"))
    # Override output_dir so logs/screenshots go inside our folder
    config.output_dir = str(OUTPUT_DIR)

    input_rows   = _load_input()
    status_cache = _load_status()

    driver = build_driver(config, download_dir=OUTPUT_DIR)
    set_download_dir(driver, OUTPUT_DIR)

    status_rows: list[dict] = []
    collected_ris: list[Path] = []

    try:
        total = len(input_rows)
        for i, row in enumerate(input_rows, start=1):
            url   = row.get(URL_COLUMN, "").strip()
            title = _title_preview(row)
            pid   = _extract_paper_id(url)

            print(f"\n[{i}/{total}] Paper {pid}")
            print(f"  Title:  {title}")
            print(f"  URL:    {url}")

            cached = status_cache.get(pid, {})
            already_done = (
                str(cached.get("downloaded", "")).lower() == "true"
                and cached.get("ris_file", "")
                and Path(cached["ris_file"]).exists()
            )

            if already_done and not force:
                print(f"  -> Already downloaded — skipping (use --force to redo).")
                log.info("Skip %s — already downloaded.", pid)
                status_rows.append({**cached, "paper_id": pid, "title": title, "url": url})
                existing = Path(cached["ris_file"])
                if existing.exists():
                    collected_ris.append(existing)
                continue

            result = download_cited_by(
                driver=driver,
                paper_link=url,
                config=config,
                output_dir=OUTPUT_DIR,
                force=force,
            )

            status_row = {
                "paper_id":      pid,
                "title":         title,
                "url":           url,
                "downloaded":    result.get("cited_by_downloaded", False),
                "downloaded_at": result.get("cited_by_downloaded_at", ""),
                "ris_file":      result.get("cited_by_ris_file", ""),
                "result_count":  result.get("cited_by_result_count", 0),
                "error":         result.get("cited_by_error", ""),
            }
            status_rows.append(status_row)
            _save_status(status_rows)

            ris_path_str = result.get("cited_by_ris_file", "")
            if ris_path_str:
                p = Path(ris_path_str)
                if p.exists():
                    collected_ris.append(p)
                    print(f"  -> {result.get('cited_by_result_count', 0)} citing papers saved: {p.name}")
                else:
                    print(f"  -> 0 citing papers.")
            else:
                err = result.get("cited_by_error", "")
                if err:
                    print(f"  -> ERROR: {err}")
                else:
                    print(f"  -> 0 citing papers.")

    finally:
        driver.quit()

    _save_status(status_rows)
    print(f"\nStatus saved: {STATUS_CSV}")

    # ── Combine & deduplicate ──────────────────────────────────────────────────
    ris_in_dir = list(OUTPUT_DIR.glob("*_cited_by.ris"))
    if not ris_in_dir:
        print("\nNo RIS files to combine.")
        return

    print(f"\nCombining {len(ris_in_dir)} RIS file(s) and deduplicating...")
    unique_count, dup_count = combine_ris_directory(
        input_dir=OUTPUT_DIR,
        output_file=DEDUP_RIS,
        report_file=OUTPUT_DIR / "duplicates_report.csv",
    )

    print(f"\nDone.")
    print(f"  Unique papers:    {unique_count}")
    print(f"  Duplicates removed: {dup_count}")
    print(f"  Zotero-ready RIS: {DEDUP_RIS}")
    print(f"  Duplicates report: {OUTPUT_DIR / 'duplicates_report.csv'}")
    print()
    print("ZOTERO IMPORT:")
    print("  Zotero Desktop -> File -> Import")
    print(f"  Select: {DEDUP_RIS}")


# ── Entry point ────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--force",   action="store_true", help="Re-download all papers, ignoring cached status.")
    p.add_argument("--verbose", action="store_true", help="Enable DEBUG-level logging.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    setup_logging(
        logs_dir=LOGS_DIR,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    run(force=args.force)
