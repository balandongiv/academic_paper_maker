"""
Fetch "cited-by" papers for NEW parent papers in zotero_Db/latest_blinker.csv,
skipping parents already processed in all_blinkers.csv, and filtering the final
output against current_masterlist.csv to produce only net-new Zotero entries.

LOGIC
-----
1.  Load zotero_Db/latest_blinker.csv  (113 papers).
2.  Load all_blinkers.csv — extract already-processed Scopus paper IDs.
3.  Skip any paper whose Scopus ID already appears in all_blinkers.csv.
4.  Skip any paper without a Scopus URL (cannot run REFEID query).
5.  For each remaining NEW paper, download all citing papers from Scopus and
    save a per-parent .ris file in  tutorial/all_cite_blink_latest/.
6.  Combine + deduplicate within the new batch.
7.  Filter out anything already in  zotero_Db/current_masterlist.csv
    (match priority: DOI > EID > title+year) — same as dedupe.py logic.
8.  Write the final Zotero-ready RIS:  tutorial/all_cite_blink_latest/latest_cite_new_only.ris

RESUME SUPPORT
--------------
Progress is saved in  tutorial/all_cite_blink_latest/status.csv.
Re-running skips already-downloaded papers.  Use --force to redo everything.

USAGE
-----
    python tutorial/fetch_cited_by_latest.py
    python tutorial/fetch_cited_by_latest.py --force
    python tutorial/fetch_cited_by_latest.py --verbose
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import string
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows cp1252 console can't print non-ASCII titles — upgrade to UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scopus_automation.browser import build_driver, set_download_dir
from scopus_automation.config import ScopusConfig
from scopus_automation.cited_by import download_cited_by, _extract_paper_id
from scopus_automation.dedupe import (
    combine_ris_directory,
    _normalise_doi, _get_doi, _get_eid, _get_title, _get_year,
)
from scopus_automation.logging_setup import setup_logging
from scopus_automation.ris import parse_ris_file, write_ris_file

log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ZOTERO_DB_DIR    = PROJECT_ROOT / "zotero_Db"
INPUT_CSV        = ZOTERO_DB_DIR / "latest_blinker.csv"
EXISTING_CSV     = PROJECT_ROOT / "all_blinkers.csv"
MASTERLIST_CSV   = ZOTERO_DB_DIR / "current_masterlist.csv"

OUTPUT_DIR       = PROJECT_ROOT / "output" / "fetch_cited_by_latest"
STATUS_CSV       = OUTPUT_DIR / "status.csv"
COMBINED_RIS     = OUTPUT_DIR / "latest_cite_dedup.ris"
NEW_ONLY_RIS     = OUTPUT_DIR / "latest_cite_new_only.ris"
LOGS_DIR         = OUTPUT_DIR / "logs"

URL_COLUMN       = "Url"


# ── ID extraction ─────────────────────────────────────────────────────────────

def _scopus_id(url: str) -> str | None:
    """Extract numeric Scopus paper ID from URL, or None if not a Scopus URL."""
    m = re.search(r"scopus\.com/pages/publications/(\d+)", url or "")
    return m.group(1) if m else None


# ── Status helpers ────────────────────────────────────────────────────────────

def _load_status() -> dict[str, dict]:
    if not STATUS_CSV.exists():
        return {}
    with STATUS_CSV.open(encoding="utf-8") as fh:
        return {row["paper_id"]: row for row in csv.DictReader(fh)}


def _save_status(rows: list[dict]) -> None:
    STATUS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["paper_id", "title", "url", "downloaded", "downloaded_at",
              "ris_file", "result_count", "error"]
    with STATUS_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ── Masterlist fingerprint builder ────────────────────────────────────────────

def _build_masterlist_fingerprints(csv_path: Path) -> set[str]:
    """
    Parse current_masterlist.csv (Zotero CSV export) and return a set of
    normalised fingerprint strings using priority: DOI > title+year.
    """
    fps: set[str] = set()
    with csv_path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            doi = row.get("DOI", "").strip()
            if doi:
                fps.add("doi:" + _normalise_doi(doi))
                continue

            # Fall back to normalised title + year
            title = row.get("Title", "").strip().lower()
            title = title.translate(str.maketrans("", "", string.punctuation))
            title = re.sub(r"\s+", " ", title).strip()

            year_raw = row.get("Publication Year", "") or row.get("Date", "")
            m = re.search(r"\d{4}", str(year_raw))
            year = m.group(0) if m else ""

            if title:
                fps.add(f"title_year:{title}|{year}")

    log.info("Built %d masterlist fingerprints from %s", len(fps), csv_path.name)
    return fps


def _ris_fingerprint(entry: dict) -> str:
    """Return the same-style fingerprint for a RIS entry."""
    doi = _get_doi(entry)
    if doi:
        return "doi:" + doi

    title = _get_title(entry)
    year  = _get_year(entry)
    if title:
        return f"title_year:{title}|{year}"

    return "unknown:" + str(entry)


def _filter_against_masterlist(
    entries: list[dict],
    masterlist_fps: set[str],
) -> tuple[list[dict], int]:
    """Remove entries whose fingerprint is in masterlist_fps.

    Returns (kept_entries, removed_count).
    """
    kept, removed = [], 0
    for entry in entries:
        fp = _ris_fingerprint(entry)
        if fp in masterlist_fps:
            removed += 1
        else:
            kept.append(entry)
    return kept, removed


# ── Input loading ─────────────────────────────────────────────────────────────

def _load_existing_ids() -> set[str]:
    """Return Scopus paper IDs from all_blinkers.csv (already processed)."""
    ids: set[str] = set()
    with EXISTING_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = _scopus_id(row.get(URL_COLUMN, ""))
            if sid:
                ids.add(sid)
    return ids


def _load_new_papers(existing_ids: set[str]) -> list[dict]:
    """
    Read latest_blinker.csv and return only rows that:
      - have a Scopus URL
      - whose Scopus paper ID is NOT in existing_ids
    """
    new_rows = []
    skipped_existing = 0
    skipped_no_scopus = 0

    with INPUT_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            url = row.get(URL_COLUMN, "").strip()
            sid = _scopus_id(url)

            if not sid:
                skipped_no_scopus += 1
                log.debug("Skip (no Scopus URL): %s", url or "(empty)")
                continue

            if sid in existing_ids:
                skipped_existing += 1
                log.debug("Skip (already processed): %s", sid)
                continue

            new_rows.append(row)

    log.info(
        "latest_blinker.csv: %d new, %d already in all_blinkers, %d non-Scopus",
        len(new_rows), skipped_existing, skipped_no_scopus,
    )
    return new_rows


def _title_preview(row: dict) -> str:
    return (row.get("Title") or "")[:70]


# ── Main ──────────────────────────────────────────────────────────────────────

def run(force: bool = False) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    config = ScopusConfig.from_file(str(PROJECT_ROOT / "setting/scopus_setup/scopus_config.json"))
    config.output_dir = str(OUTPUT_DIR)

    existing_ids  = _load_existing_ids()
    new_rows      = _load_new_papers(existing_ids)
    status_cache  = _load_status()
    masterlist_fps = _build_masterlist_fingerprints(MASTERLIST_CSV)

    if not new_rows:
        print("No new papers to process — all parents are already in all_blinkers.csv.")
        return

    print(f"\nNew parent papers to fetch cited-by for: {len(new_rows)}")
    print(f"Masterlist fingerprints loaded: {len(masterlist_fps)}")

    driver = build_driver(config, download_dir=OUTPUT_DIR)
    set_download_dir(driver, OUTPUT_DIR)

    status_rows: list[dict] = []

    try:
        total = len(new_rows)
        for i, row in enumerate(new_rows, start=1):
            url   = row.get(URL_COLUMN, "").strip()
            title = _title_preview(row)
            pid   = _extract_paper_id(url)

            print(f"\n[{i}/{total}] Paper {pid}")
            print(f"  Title: {title}")
            print(f"  URL:   {url}")

            cached = status_cache.get(pid, {})
            already_done = (
                str(cached.get("downloaded", "")).lower() == "true"
                and cached.get("ris_file", "")
                and Path(cached["ris_file"]).exists()
            )

            if already_done and not force:
                print("  -> Already downloaded — skipping.")
                status_rows.append({**cached, "paper_id": pid, "title": title, "url": url})
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

            ris_str = result.get("cited_by_ris_file", "")
            if ris_str and Path(ris_str).exists():
                print(f"  -> {result.get('cited_by_result_count', 0)} citing papers: {Path(ris_str).name}")
            else:
                err = result.get("cited_by_error", "")
                print(f"  -> {'ERROR: ' + err if err else '0 citing papers.'}")

    finally:
        driver.quit()

    _save_status(status_rows)
    print(f"\nStatus saved: {STATUS_CSV}")

    # ── Combine & deduplicate within new batch ────────────────────────────────
    ris_in_dir = list(OUTPUT_DIR.glob("*_cited_by.ris"))
    if not ris_in_dir:
        print("\nNo RIS files to combine.")
        return

    print(f"\nCombining {len(ris_in_dir)} RIS file(s) and deduplicating within batch...")
    unique_count, dup_count = combine_ris_directory(
        input_dir=OUTPUT_DIR,
        output_file=COMBINED_RIS,
        report_file=OUTPUT_DIR / "duplicates_report.csv",
    )
    print(f"  Unique in batch:  {unique_count}")
    print(f"  Intra-batch dups: {dup_count}")

    # ── Filter against masterlist ─────────────────────────────────────────────
    print(f"\nFiltering against masterlist ({len(masterlist_fps)} entries)...")
    batch_entries = parse_ris_file(COMBINED_RIS)
    kept_entries, removed_count = _filter_against_masterlist(batch_entries, masterlist_fps)
    write_ris_file(kept_entries, NEW_ONLY_RIS)

    print(f"\nDone.")
    print(f"  Unique in batch:          {unique_count}")
    print(f"  Already in masterlist:    {removed_count}")
    print(f"  Net-new for Zotero:       {len(kept_entries)}")
    print(f"  Zotero-ready RIS:         {NEW_ONLY_RIS}")
    print()
    print("ZOTERO IMPORT:")
    print("  Zotero Desktop -> File -> Import")
    print(f"  Select: {NEW_ONLY_RIS}")


# ── Entry point ───────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--force",   action="store_true", help="Re-download all, ignoring cached status.")
    p.add_argument("--verbose", action="store_true", help="Enable DEBUG-level logging.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    setup_logging(
        logs_dir=LOGS_DIR,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    run(force=args.force)
