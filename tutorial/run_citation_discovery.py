"""
Citation Discovery Tutorial
============================

Runs the citation-discovery pipeline on get_children_050626.csv.

USAGE
-----
    # Full run (requires Chrome + Scopus session):
    python tutorial/run_citation_discovery.py

    # Dry run — no browser, shows what would be processed:
    python tutorial/run_citation_discovery.py --dry-run

    # Force rerun of already-processed parents:
    python tutorial/run_citation_discovery.py --force

    # Custom config file:
    python tutorial/run_citation_discovery.py --config my_config.yaml

    # Debug logging:
    python tutorial/run_citation_discovery.py --verbose

OUTPUT (after a full run)
-------------------------
output/citation_discovery/
    scopus_children_YYYY-MM-DD_HHMMSS.ris   <- import this into Zotero
    cited_by_raw/
        {scopus_id}_cited_by.ris            <- per-parent raw RIS files
    cited_by_per_paper_status.csv
    duplicates_report.csv
    run_summary.json

complete_file_available_in_zotero.csv       <- updated master list
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Allow running from either project root or tutorial/ directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows console encoding fix
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scopus_automation.logging_setup import setup_logging
from pipeline import load_config, run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Citation discovery: find papers citing your Zotero references.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python tutorial/run_citation_discovery.py --dry-run\n"
            "  python tutorial/run_citation_discovery.py\n"
            "  python tutorial/run_citation_discovery.py --force\n"
        ),
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "setting/scopus_setup/config_citation_discovery.yaml"),
        metavar="PATH",
        help="Pipeline YAML config  (default: config_citation_discovery.yaml)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without launching Chrome.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-query Scopus for all parents, even those already processed.",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = parser.parse_args()

    logs_dir = PROJECT_ROOT / "output" / "citation_discovery" / "logs"
    setup_logging(
        logs_dir,
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    print("\n" + "=" * 60)
    print("  SCOPUS CITATION DISCOVERY PIPELINE")
    print("=" * 60)
    print(f"  Config : {args.config}")
    print(f"  Dry run: {args.dry_run}")
    print(f"  Force  : {args.force}")

    # Load config and apply --force flag
    cfg = load_config(args.config)
    if args.force:
        cfg.run.force_rerun = True

    # Run
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
