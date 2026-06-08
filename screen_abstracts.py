"""Abstract screening pipeline — EEG-based driver fatigue papers.

Orchestrates the full workflow in one command:
  1. Import master CSV → SQLite database
  2. Export keyword-filtered candidates to CSV (for manual review)
  3. Claim a batch of candidates and screen each abstract through ChatGPT
  4. Export papers marked relevant to a final CSV

All settings come from the YAML config file.

Usage
-----
  # Full run (import → screen → export)
  python screen_abstracts.py

  # Use a specific config
  python screen_abstracts.py --config setting/chatgpt_ui/config_fatigue_eeg.yaml

  # Only import the CSV and show stats (no ChatGPT)
  python screen_abstracts.py --import-only

  # Only refresh the candidates CSV (no ChatGPT)
  python screen_abstracts.py --export-candidates

  # Only refresh the relevant-papers CSV from existing JSON outputs
  python screen_abstracts.py --export-relevant

  # Show database stats and exit
  python screen_abstracts.py --stats

  # Override batch size for this run
  python screen_abstracts.py --batch-size 20

  # Re-screen papers that were already completed (e.g. after changing the prompt)
  python screen_abstracts.py --rescreen

  # Verbose (DEBUG) logging
  python screen_abstracts.py --verbose
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE           = Path(__file__).resolve().parent
_DEFAULT_CONFIG = _HERE / "setting" / "chatgpt_ui" / "config_fatigue_eeg.yaml"
_LOG_DIR        = _HERE / "logs"
_BUNDLED_CHROMEDRIVER = _HERE / "apm" / "browser" / "chromedriver.exe"

# Seconds to pause between rows (reduce ChatGPT rate-limit risk)
_ROW_PAUSE = 3


def _delete_json_outputs(cfg, log) -> int:
    """Delete all JSON output files so --rescreen starts with a clean slate."""
    deleted = 0
    if cfg.output_path.exists():
        for jf in cfg.output_path.glob("*.json"):
            try:
                jf.unlink()
                deleted += 1
            except OSError as exc:
                log.warning("Could not delete %s: %s", jf.name, exc)
    log.info("Deleted %d existing JSON output files from %s.", deleted, cfg.output_path)
    return deleted


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool, log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"screen_abstracts_{stamp}.log"

    level = logging.DEBUG if verbose else logging.INFO
    fmt   = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    return log_file


# ---------------------------------------------------------------------------
# Stats printer
# ---------------------------------------------------------------------------

def _print_stats(stats: dict, label: str = "Stats") -> None:
    order = ["Yet To Process", "Already Processing", "In Progress", "Completed", "Failed"]
    print(f"\n--- {label} ---")
    for status in order:
        if status in stats:
            print(f"  {status:<25} {stats[status]:>7,}")
    for k, v in stats.items():
        if k not in order:
            print(f"  {k:<25} {v:>7,}")
    print(f"  {'TOTAL':<25} {sum(stats.values()):>7,}")
    print()


# ---------------------------------------------------------------------------
# Claim helper (with application-level retry for transient locks)
# ---------------------------------------------------------------------------

def _claim_with_retry(conn, cfg, max_attempts: int = 5):
    from apm.chatgpt_ui.database import claim_rows

    for attempt in range(1, max_attempts + 1):
        try:
            return claim_rows(
                conn,
                machine_id=cfg.processing.machine_id,
                batch_size=cfg.processing.batch_size,
                max_retries=cfg.processing.max_retries,
                stale_lock_hours=cfg.processing.stale_lock_hours,
                keyword_filter=cfg.processing.keyword_filter or None,
            )
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower() and attempt < max_attempts:
                wait = attempt * 5
                logging.getLogger(__name__).warning(
                    "Database locked (attempt %d/%d) — retrying in %ds.",
                    attempt, max_attempts, wait,
                )
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def step_import(conn, cfg, log) -> int:
    from apm.chatgpt_ui.database import import_csv

    log.info("=== STEP 1: Import CSV ===")
    if not cfg.master_csv_path.exists():
        log.error("Master CSV not found: %s", cfg.master_csv_path)
        raise FileNotFoundError(cfg.master_csv_path)

    n = import_csv(conn, cfg.master_csv_path)
    log.info("Import done — %d new rows added.", n)
    return n


def step_export_candidates(cfg, log) -> int:
    from apm.chatgpt_ui.export_candidates import export, KEYWORD_GROUPS
    from apm.chatgpt_ui.database import open_db

    log.info("=== STEP 2: Export keyword-filtered candidates CSV ===")
    groups = [label for label, _ in KEYWORD_GROUPS]
    log.info("Keyword groups: %s", " AND ".join(groups))

    out_csv = cfg.project_path / "candidates_eeg_fatigue_driver.csv"
    conn2   = open_db(cfg.db_path)
    n       = export(conn2, out_csv)
    conn2.close()

    log.info("Candidates CSV: %s  (%d papers)", out_csv, n)
    return n


def step_screen(conn, cfg, log, rescreen: bool = False) -> tuple[int, int]:
    from apm.chatgpt_ui.processor import process_row, ChatGPTServerError
    from apm.chatgpt_ui.selenium_client import build_driver, ensure_logged_in
    from apm.chatgpt_ui.database import get_stats, reset_completed

    log.info("=== STEP 3: Screen abstracts via ChatGPT ===")

    if rescreen:
        n_reset = reset_completed(conn, keyword_filter=cfg.processing.keyword_filter or None)
        log.info("--rescreen: reset %d previously completed rows for re-screening.", n_reset)
        if n_reset:
            _delete_json_outputs(cfg, log)

    # Log how many completed rows are being skipped in this run
    stats = get_stats(conn)
    n_completed = stats.get("Completed", 0)
    n_pending   = stats.get("Yet To Process", 0) + stats.get("Failed", 0)
    if n_completed:
        log.info("Skipping %d already-completed rows. Use --rescreen to re-screen them.", n_completed)
    log.info("%d rows eligible for this batch.", n_pending)

    if not cfg.prompt_path.exists():
        log.error("Prompt file not found: %s", cfg.prompt_path)
        raise FileNotFoundError(cfg.prompt_path)

    prompt_template = cfg.prompt_path.read_text(encoding="utf-8")
    log.info("Prompt file: %s", cfg.prompt_path)

    cfg.output_path.mkdir(parents=True, exist_ok=True)

    rows = _claim_with_retry(conn, cfg)
    if not rows:
        log.info("No rows available — all candidates are processed or in progress.")
        _print_stats(get_stats(conn), "Current stats")
        return 0, 0

    log.info("Claimed %d rows to process.", len(rows))

    driver    = build_driver(cfg.selenium, chromedriver_path=str(_BUNDLED_CHROMEDRIVER), detach=False)
    completed = 0
    failed    = 0

    try:
        driver.get("https://chatgpt.com/")
        time.sleep(3)
        ensure_logged_in(driver)

        for i, row in enumerate(rows, 1):
            log.info("  Row %d/%d — %s", i, len(rows), (row["title"] or "")[:70])
            try:
                success = process_row(conn, driver, cfg, row, prompt_template)
            except ChatGPTServerError as exc:
                log.error("ChatGPT server unreachable — terminating batch early: %s", exc)
                failed += 1
                break
            if success:
                completed += 1
            else:
                failed += 1
            if i < len(rows):
                time.sleep(_ROW_PAUSE)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    log.info("Batch done — %d completed, %d failed.", completed, failed)
    return completed, failed


def step_export_relevant(cfg, log) -> tuple[int, int]:
    from apm.chatgpt_ui.export_relevant import export

    log.info("=== STEP 4: Export relevant papers CSV ===")
    out_csv = cfg.project_path / "relevant_fatigue_eeg.csv"
    relevant, total = export(cfg.output_path, out_csv)
    log.info(
        "Relevant CSV: %s  (%d relevant / %d processed)",
        out_csv, relevant, total,
    )
    return relevant, total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="screen_abstracts.py",
        description="EEG driver-fatigue abstract screening pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", "-c",
        default=str(_DEFAULT_CONFIG),
        metavar="PATH",
        help=f"YAML config file (default: {_DEFAULT_CONFIG.name}).",
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Import CSV → DB, export candidates CSV, then exit (no ChatGPT).",
    )
    parser.add_argument(
        "--export-candidates",
        action="store_true",
        help="Refresh the keyword-filtered candidates CSV and exit.",
    )
    parser.add_argument(
        "--export-relevant",
        action="store_true",
        help="Refresh the relevant-papers CSV from existing JSON outputs and exit.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print database stats and exit.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=0,
        metavar="N",
        help="Override batch_size from config for this run.",
    )
    parser.add_argument(
        "--rescreen",
        action="store_true",
        help=(
            "Reset all previously Completed rows back to 'Yet To Process' "
            "and delete their JSON outputs, then re-screen from scratch. "
            "Use this after changing the prompt template."
        ),
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    # ------------------------------------------------------------------
    # Config + logging
    # ------------------------------------------------------------------
    from apm.chatgpt_ui.config import load_config
    from apm.chatgpt_ui.database import open_db, init_db, get_stats

    cfg = load_config(args.config)
    if args.batch_size > 0:
        cfg.processing.batch_size = args.batch_size

    log_file = _setup_logging(args.verbose, _LOG_DIR)
    log      = logging.getLogger(__name__)

    log.info("=" * 60)
    log.info("screen_abstracts.py  —  EEG driver-fatigue screening")
    log.info("=" * 60)
    log.info("Config      : %s", args.config)
    log.info("Database    : %s", cfg.db_path)
    log.info("Output dir  : %s", cfg.output_path)
    log.info("Machine ID  : %s", cfg.processing.machine_id)
    log.info("Batch size  : %s", cfg.processing.batch_size)
    log.info("Log file    : %s", log_file)

    # ------------------------------------------------------------------
    # Short-circuit modes
    # ------------------------------------------------------------------
    if args.export_candidates:
        conn = open_db(cfg.db_path)
        init_db(conn)
        conn.close()
        step_export_candidates(cfg, log)
        return 0

    if args.export_relevant:
        step_export_relevant(cfg, log)
        return 0

    # ------------------------------------------------------------------
    # DB init + CSV import (always runs)
    # ------------------------------------------------------------------
    conn = open_db(cfg.db_path)
    init_db(conn)

    step_import(conn, cfg, log)
    n_candidates = step_export_candidates(cfg, log)

    stats = get_stats(conn)
    _print_stats(stats, "Stats after import")

    if args.import_only or args.stats:
        print(f"Keyword-filtered candidates : {n_candidates:,}")
        conn.close()
        return 0

    # ------------------------------------------------------------------
    # Screen abstracts via ChatGPT
    # ------------------------------------------------------------------
    completed, failed = step_screen(conn, cfg, log, rescreen=args.rescreen)
    conn.close()

    # ------------------------------------------------------------------
    # Export relevant papers
    # ------------------------------------------------------------------
    relevant, total_processed = step_export_relevant(cfg, log)

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    conn2 = open_db(cfg.db_path)
    _print_stats(get_stats(conn2), "Final stats")
    conn2.close()

    print(f"Batch          : {completed} completed, {failed} failed")
    print(f"Total screened : {total_processed:,} papers")
    print(f"Relevant found : {relevant:,} papers")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
