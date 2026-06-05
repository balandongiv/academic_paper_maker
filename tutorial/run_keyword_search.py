"""
Keyword Search Tutorial
========================

Runs the keyword-search pipeline using queries defined in
config_keyword_search.yaml.

USAGE
-----
    # Full run (requires Chrome + Scopus session):
    python tutorial/run_keyword_search.py

    # Dry run — validate config and master list, no browser:
    python tutorial/run_keyword_search.py --dry-run

    # Custom config:
    python tutorial/run_keyword_search.py --config config_keyword_search.yaml

    # Debug logging:
    python tutorial/run_keyword_search.py --verbose

OUTPUT (after a full run)
-------------------------
output/keyword_search/
    scopus_export_YYYY-MM-DD_HHMMSS.ris     <- import this into Zotero
    keyword_raw/
        {query_slug}.ris                    <- per-keyword raw RIS files
    keyword_search_status.csv
    keyword_duplicates_report.csv
    run_summary.json

complete_file_available_in_zotero.csv       <- updated master list
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scopus_automation.logging_setup import setup_logging
from pipeline import load_config, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Keyword search: discover papers matching your Scopus queries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tutorial/run_keyword_search.py --dry-run\n"
            "  python tutorial/run_keyword_search.py\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "setting/scopus_setup/config_keyword_search.yaml"),
        metavar="PATH",
        help="Pipeline YAML config  (default: config_keyword_search.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and master list without launching Chrome.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = parser.parse_args()

    logs_dir = PROJECT_ROOT / "output" / "keyword_search" / "logs"
    setup_logging(
        logs_dir,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    print("\n" + "=" * 60)
    print("  SCOPUS KEYWORD SEARCH PIPELINE")
    print("=" * 60)
    print(f"  Config : {args.config}")
    print(f"  Dry run: {args.dry_run}")

    summary = run_pipeline(
        config_path=args.config,
        base_dir=PROJECT_ROOT,
        dry_run=args.dry_run,
    )

    if summary.errors:
        print("\nErrors encountered:")
        for e in summary.errors:
            print(f"  ! {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
