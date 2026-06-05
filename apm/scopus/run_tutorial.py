"""
EEG Driver-Fatigue Literature Pipeline — Tutorial Script
=========================================================

PURPOSE
-------
A self-contained, two-stage Scopus literature collection pipeline that
demonstrates how to use the scopus_automation package end-to-end.

    Stage 1 — Advanced Search
        Query Scopus for EEG-based driver fatigue / drowsiness papers
        published in 2026 and export the results as a single RIS file.

    Stage 2 — Cited-by Harvest
        For every parent paper discovered in Stage 1, search Scopus for
        all papers that cite it (REFEID query) and download each result
        as an individual RIS file named:

            {first_author_last_name}_{year}_child_cite.ris

        Example:  smith_2026_child_cite.ris

OUTPUT LAYOUT
-------------
tutorial/
├── run_tutorial.py          ← this script
├── search/
│   └── eeg_driver_fatigue_2026.ris    # all Stage 1 parent papers
├── cited_by/
│   ├── smith_2026_child_cite.ris      # papers that cite Smith 2026
│   ├── kumar_2026_child_cite.ris      # papers that cite Kumar 2026
│   └── ...
├── logs/
│   ├── scopus_automation_*.log        # full debug log with timestamps
│   └── *.png                          # browser screenshots at key steps
└── summary.csv                        # per-parent-paper status table

SUMMARY COLUMNS (summary.csv)
------------------------------
index        Row number (1-based).
label        {author}_{year} label used in the file name.
paper_id     Numeric Scopus paper ID extracted from the UR field.
title        Document title from the RIS.
status       ok | 0 citations | already downloaded | skipped (no URL) | error: …
count        Number of citing papers downloaded (empty if 0 or skipped).
file         Output RIS filename (empty if nothing was downloaded).

PREREQUISITES
-------------
1. Python packages:
       pip install -r requirements.txt   (from the project root)

2. Chrome profile already logged in to Scopus.
   Create and log in once if you have not done so:

       "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^
           --user-data-dir=C:\\selenium\\chrome-profile ^
           --profile-directory=Default

   Navigate to https://www.scopus.com, authenticate through your institution,
   then close the browser.  The session cookie is saved in the profile and
   reused on every subsequent run — no interactive login required.

3. scopus_config.json in the project root.
   If the file is missing, the script uses built-in defaults that match the
   Chrome profile path above.

USAGE
-----
Run from the project root (recommended):

    python tutorial/run_tutorial.py

Enable verbose (DEBUG-level) logging — useful for troubleshooting:

    python tutorial/run_tutorial.py --verbose

Force a full re-download even if output files already exist:

    python tutorial/run_tutorial.py --force

Point to a custom config file:

    python tutorial/run_tutorial.py --config path/to/scopus_config.json

RESUME BEHAVIOUR
----------------
If the script is interrupted (network drop, timeout, Ctrl-C), simply run it
again without --force.  Stage 1 is skipped if eeg_driver_fatigue_2026.ris
already exists, and Stage 2 skips any parent paper whose cited-by RIS file
is already present in tutorial/cited_by/.  Only missing papers are downloaded.

RENAME COLLISION HANDLING
--------------------------
If two parent papers share the same first author last name and publication year
(e.g., two papers by "Smith" in 2026), the second one is named:

    smith_2026_{paper_id}_child_cite.ris

where {paper_id} is the numeric Scopus ID, guaranteeing uniqueness.

TROUBLESHOOTING
---------------
"Chrome opens but stays blank / no search form found"
    The Selenium profile session may have expired.  Open Chrome manually with
    --user-data-dir=C:\\selenium\\chrome-profile and re-authenticate to Scopus.

"Download timed out"
    Scopus can be slow.  Increase download_timeout_sec in scopus_config.json
    (default is 120 seconds).

"0 citing papers" for all entries
    Check that the REFEID query is being built correctly.  The logs/ directory
    contains browser screenshots taken at each export step for diagnosis.

"No valid Scopus URL in UR field"
    The parent RIS file was exported without the URL field.  Re-export from
    Scopus with the "URL" field enabled in the export modal, or add the UR
    tag manually.
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
# Allows running as  python apm/scopus/run_tutorial.py  from the project root
# as well as  python run_tutorial.py  from inside the apm/scopus/ directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scopus_automation.browser import build_driver, set_download_dir
from scopus_automation.config import ScopusConfig
from scopus_automation.login import ensure_logged_in
from scopus_automation.logging_setup import setup_logging
from scopus_automation.ris import parse_ris_file
from scopus_automation.search_export import search_and_export
from scopus_automation.cited_by import download_cited_by

log = logging.getLogger(__name__)

# ── Output directories (all inside output/run_tutorial/) ─────────────────────
SEARCH_DIR   = PROJECT_ROOT / "output" / "run_tutorial" / "search"
CITED_DIR    = PROJECT_ROOT / "output" / "run_tutorial" / "cited_by"
LOGS_DIR     = PROJECT_ROOT / "output" / "run_tutorial" / "logs"
SUMMARY_CSV  = PROJECT_ROOT / "output" / "run_tutorial" / "summary.csv"

# Fixed name for the Stage 1 RIS output
SEARCH_RIS_NAME = "eeg_driver_fatigue_2026.ris"

# ── Scopus advanced search query ─────────────────────────────────────────────
# Finds EEG-based driver fatigue / drowsiness detection papers from 2026.
# Edit this string to change the query without touching anything else.
SEARCH_QUERY = (
    'TITLE-ABS-KEY('
    '  (eeg OR electroencephalogra*)'
    '  AND'
    '  ("driver fatigue" OR "driver drowsiness" OR "driving fatigue"'
    '   OR "drowsiness detection" OR "fatigue detection")'
    '  AND'
    '  (driving OR driver* OR "driving simulator*"'
    '   OR "real driving" OR "on-road driving")'
    ') AND PUBYEAR = 2026'
)


# ── Filename helpers ──────────────────────────────────────────────────────────

def _safe_filename(text: str) -> str:
    """Convert arbitrary text to a safe, lowercase filename component.

    Replaces every character that is not a word character (letter, digit,
    underscore) with an underscore, collapses repeated underscores, and
    strips leading/trailing underscores.
    """
    cleaned = re.sub(r"[^\w]", "_", str(text).lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or "unknown"


def _author_year_label(entry: dict) -> str:
    """Build a short 'lastnamelower_year' label from an RIS entry dict.

    Scopus stores authors as  'Last, First'  (or  'Last, F.').
    We take the portion before the first comma as the family name.

    If multiple AU lines are present, only the first author is used.
    """
    au = entry.get("AU", "unknown")
    if isinstance(au, list):
        au = au[0]                          # first author
    last_name = str(au).split(",")[0]       # 'Smith' from 'Smith, J.'
    year = str(entry.get("PY", "unknown"))[:4]
    return f"{_safe_filename(last_name)}_{year}"


def _cited_by_dest(label: str, paper_id: str) -> Path:
    """Return the destination Path for a cited-by RIS file.

    The preferred name is  {label}_child_cite.ris.
    If that file already exists (a previous paper claimed the same label),
    the Scopus paper_id is inserted to guarantee uniqueness:
        {label}_{paper_id}_child_cite.ris
    """
    preferred = CITED_DIR / f"{label}_child_cite.ris"
    if not preferred.exists():
        return preferred
    return CITED_DIR / f"{label}_{paper_id}_child_cite.ris"


def _write_summary(rows: list[dict]) -> None:
    """Persist the current summary table to SUMMARY_CSV.

    Called after every paper so partial results survive an interruption.
    """
    fields = ["index", "label", "paper_id", "title", "status", "count", "file"]
    SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(config: ScopusConfig, force: bool = False) -> None:
    """Run Stage 1 (search) then Stage 2 (cited-by harvest).

    Parameters
    ----------
    config:
        ScopusConfig instance loaded from scopus_config.json.
    force:
        When True, re-download even if output files already exist.
    """
    SEARCH_DIR.mkdir(parents=True, exist_ok=True)
    CITED_DIR.mkdir(parents=True, exist_ok=True)

    # ── STAGE 1: Advanced search ──────────────────────────────────────────
    print("\n" + "=" * 66)
    print("  STAGE 1 — Advanced Scopus Search")
    print("=" * 66)
    print(f"\n  Query:\n  {SEARCH_QUERY}\n")

    # Build the Chrome driver.  Initial download directory = search output.
    driver = build_driver(config, SEARCH_DIR)
    try:
        # Verify the Scopus session before doing any work.
        if not ensure_logged_in(driver, config):
            print(
                "\n  ERROR: Could not verify Scopus login.\n"
                f"  Profile: {config.chrome_profile_path}\n\n"
                "  Fix: open Chrome manually with that profile and log in:\n"
                "    chrome.exe --user-data-dir=C:\\selenium\\chrome-profile\n"
            )
            return

        search_ris_path = SEARCH_DIR / SEARCH_RIS_NAME

        if search_ris_path.exists() and not force:
            print(f"  Stage 1 RIS already exists — skipping download.")
            print(f"  File : {search_ris_path}")
            print("  Tip  : pass --force to re-download.\n")
        else:
            meta = search_and_export(
                driver, SEARCH_QUERY, config, output_dir=SEARCH_DIR
            )

            if meta.get("error") or not meta.get("ris_file"):
                print(f"\n  Search failed: {meta.get('error', 'no RIS produced')}")
                return

            # Rename the Scopus auto-generated filename to our fixed name.
            raw_path = Path(meta["ris_file"])
            if raw_path.resolve() != search_ris_path.resolve():
                if search_ris_path.exists():
                    search_ris_path.unlink()
                raw_path.rename(search_ris_path)

            print(f"\n  Stage 1 complete — {meta['result_count']} parent papers found.")
            print(f"  Saved : {search_ris_path}\n")

        # ── STAGE 2: Cited-by harvest ─────────────────────────────────────
        print("=" * 66)
        print("  STAGE 2 — Cited-by Harvest")
        print("=" * 66)

        parent_entries = parse_ris_file(search_ris_path)
        total = len(parent_entries)
        print(f"\n  {total} parent paper(s) to process.\n")

        if total == 0:
            print("  No entries found in the Stage 1 RIS — nothing to do.")
            return

        # Redirect Chrome downloads to cited_by/ for Stage 2.
        set_download_dir(driver, CITED_DIR)

        summary_rows: list[dict] = []

        for i, entry in enumerate(parent_entries, 1):
            title  = str(entry.get("TI", "(no title)"))
            url    = str(entry.get("UR", "")).strip()
            label  = _author_year_label(entry)

            # Extract the numeric Scopus ID from the UR field.
            pid_match = re.search(r"/publications?/(\d+)", url)
            paper_id  = pid_match.group(1) if pid_match else "unknown"

            print(f"  [{i:>3}/{total}]  {title[:70]}")
            print(f"           Label  : {label}")
            print(f"           URL    : {url[:80] or '(missing)'}")

            row: dict = {
                "index":    i,
                "label":    label,
                "paper_id": paper_id,
                "title":    title,
                "status":   "",
                "count":    "",
                "file":     "",
            }

            # ── Guard: need a valid Scopus URL to build the REFEID query ──
            if not url or "scopus.com" not in url:
                print("           SKIP   : no valid Scopus URL in UR field.\n")
                row["status"] = "skipped (no URL)"
                summary_rows.append(row)
                _write_summary(summary_rows)
                continue

            # ── Guard: resume support — skip if already downloaded ─────────
            dest_path = _cited_by_dest(label, paper_id)
            if dest_path.exists() and not force:
                print(f"           SKIP   : already downloaded -> {dest_path.name}\n")
                row["status"] = "already downloaded"
                row["file"]   = dest_path.name
                summary_rows.append(row)
                _write_summary(summary_rows)
                continue

            # ── Download cited-by papers ───────────────────────────────────
            # download_cited_by builds  REFEID(2-s2.0-{paper_id})  and runs
            # the full Feature 1 export pipeline (select-all -> export -> RIS).
            result = download_cited_by(
                driver, url, config, output_dir=CITED_DIR, force=force
            )

            ris_src  = result.get("cited_by_ris_file", "")
            n_papers = result.get("cited_by_result_count", 0)
            error    = result.get("cited_by_error", "")

            if ris_src and Path(ris_src).exists():
                src = Path(ris_src)
                # Rename from  {paper_id}_cited_by.ris  ->  {label}_child_cite.ris
                if src.resolve() != dest_path.resolve():
                    if dest_path.exists():
                        dest_path.unlink()
                    src.rename(dest_path)
                    log.info("Renamed %s -> %s", src.name, dest_path.name)

                print(f"           SAVED  : {dest_path.name}  ({n_papers} citing papers)\n")
                row["status"] = "ok"
                row["count"]  = n_papers
                row["file"]   = dest_path.name

            elif n_papers == 0:
                print("           INFO   : 0 citing papers found — nothing to save.\n")
                row["status"] = "0 citations"

            else:
                print(f"           ERROR  : {error}\n")
                row["status"] = f"error: {error}"

            summary_rows.append(row)
            _write_summary(summary_rows)   # incremental save after each paper

        # ── Final summary ─────────────────────────────────────────────────
        _write_summary(summary_rows)

        ok_count   = sum(1 for r in summary_rows if r["status"] == "ok")
        zero_count = sum(1 for r in summary_rows if r["status"] == "0 citations")
        skip_count = sum(1 for r in summary_rows
                         if "skip" in str(r["status"]).lower()
                         or "already" in str(r["status"]).lower())
        err_count  = sum(1 for r in summary_rows
                         if "error" in str(r["status"]).lower())

        print("=" * 66)
        print("  SUMMARY")
        print("=" * 66)
        print()
        for r in summary_rows:
            s = str(r["status"])
            if s == "ok":
                flag, note = "OK ", f"({r['count']} papers) -> {r['file']}"
            elif s == "0 citations":
                flag, note = "-- ", "0 citing papers"
            elif "already" in s:
                flag, note = "-- ", f"already downloaded -> {r['file']}"
            elif "skip" in s.lower():
                flag, note = "SK ", s
            else:
                flag, note = "ERR", s
            print(f"  [{flag}] {r['label']:<32}  {note}")

        print()
        print(f"  Parent papers processed : {total}")
        print(f"  Cited-by downloaded     : {ok_count}")
        print(f"  Zero citations          : {zero_count}")
        print(f"  Skipped / resumed       : {skip_count}")
        print(f"  Errors                  : {err_count}")
        print(f"\n  Output folder : {(PROJECT_ROOT / 'output' / 'run_tutorial').resolve()}")
        print(f"  Summary table : {SUMMARY_CSV}")
        print()

    finally:
        driver.quit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "EEG driver-fatigue Scopus pipeline.\n"
            "Stage 1: advanced search -> eeg_driver_fatigue_2026.ris\n"
            "Stage 2: cited-by harvest -> {author}_{year}_child_cite.ris per paper"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tutorial/run_tutorial.py\n"
            "  python tutorial/run_tutorial.py --verbose\n"
            "  python tutorial/run_tutorial.py --force\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "setting/scopus_setup/scopus_config.json"),
        metavar="PATH",
        help="Path to scopus_config.json  (default: setting/scopus_setup/scopus_config.json)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging to console and log file",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Re-download and overwrite existing output files",
    )
    args = parser.parse_args()

    setup_logging(
        LOGS_DIR,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    cfg = ScopusConfig.from_file(args.config)
    run_pipeline(cfg, force=args.force)
