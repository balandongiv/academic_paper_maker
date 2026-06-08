"""CLI entry point for batch-processing literature entries through ChatGPT.

Usage examples
--------------
# First run: import CSV and check stats
python -m apm.chatgpt_ui.run_batch --import-only
python -m apm.chatgpt_ui.run_batch --stats

# Normal batch run (uses hostname as machine_id by default)
python -m apm.chatgpt_ui.run_batch

# Override settings
python -m apm.chatgpt_ui.run_batch --config setting/chatgpt_ui/config.yaml --machine-id computer_2
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

from .config import load_config
from .database import (
    open_db,
    init_db,
    import_csv,
    claim_rows,
    get_stats,
)
from .processor import process_row, ChatGPTServerError
from .selenium_client import build_driver, ensure_logged_in, navigate_to_new_chat

log = logging.getLogger(__name__)

_PROJECT_ROOT       = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG     = _PROJECT_ROOT / "setting" / "chatgpt_ui" / "config.yaml"
_BUNDLED_CHROMEDRIVER = str(_PROJECT_ROOT / "apm" / "browser" / "chromedriver.exe")

# Seconds to pause between rows (reduce ChatGPT rate-limit risk)
_ROW_PAUSE = 3


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _print_stats(stats: dict) -> None:
    print("\n--- Processing stats ---")
    for status in [
        "Yet To Process",
        "Already Processing",
        "In Progress",
        "Completed",
        "Failed",
    ]:
        if status in stats:
            print(f"  {status:<25} {stats[status]:>7,}")
    extras = {k: v for k, v in stats.items()
              if k not in ("Yet To Process","Already Processing","In Progress","Completed","Failed")}
    for k, v in extras.items():
        print(f"  {k:<25} {v:>7,}")
    total = sum(stats.values())
    print(f"  {'TOTAL':<25} {total:>7,}")
    print()


def _claim_with_retry(conn, cfg, max_attempts: int = 5):
    """Wrap claim_rows with application-level retry for transient lock errors."""
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
                log.warning(
                    "Database locked (attempt %d/%d) — retrying in %ds.",
                    attempt, max_attempts, wait,
                )
                time.sleep(wait)
            else:
                raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Batch-process literature rows through ChatGPT via Selenium.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default=str(_DEFAULT_CONFIG),
        metavar="PATH",
        help="YAML configuration file (default: setting/chatgpt_ui/config.yaml).",
    )
    parser.add_argument(
        "--machine-id",
        default="",
        metavar="ID",
        help="Override machine_id from config (default: hostname).",
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Import the CSV into the database and exit without processing.",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print processing statistics and exit.",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------
    cfg = load_config(args.config)
    if args.machine_id:
        cfg.processing.machine_id = args.machine_id

    log.info("Machine ID : %s", cfg.processing.machine_id)
    log.info("Database   : %s", cfg.db_path)
    log.info("Output dir : %s", cfg.output_path)

    # ------------------------------------------------------------------
    # Database init + CSV import
    # ------------------------------------------------------------------
    conn = open_db(cfg.db_path)
    init_db(conn)

    if not cfg.master_csv_path.exists():
        log.error("Master CSV not found: %s", cfg.master_csv_path)
        return 1

    import_csv(conn, cfg.master_csv_path)

    if args.import_only or args.stats:
        _print_stats(get_stats(conn))
        conn.close()
        return 0

    # ------------------------------------------------------------------
    # Claim rows
    # ------------------------------------------------------------------
    rows = _claim_with_retry(conn, cfg)

    if not rows:
        log.info("No rows available for processing.")
        _print_stats(get_stats(conn))
        conn.close()
        return 0

    log.info("Claimed %d rows to process.", len(rows))

    # ------------------------------------------------------------------
    # Prompt template
    # ------------------------------------------------------------------
    if not cfg.prompt_path.exists():
        log.error("Prompt file not found: %s", cfg.prompt_path)
        conn.close()
        return 1

    prompt_template = cfg.prompt_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Selenium session
    # ------------------------------------------------------------------
    driver = build_driver(cfg.selenium, chromedriver_path=_BUNDLED_CHROMEDRIVER, detach=False)
    completed = 0
    failed    = 0

    try:
        driver.get("https://chatgpt.com/")
        time.sleep(3)
        ensure_logged_in(driver)

        for i, row in enumerate(rows, 1):
            log.info("--- Row %d / %d (id=%d) ---", i, len(rows), row["id"])
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
            driver.quit()   # closes browser window AND stops ChromeDriver service
        except Exception:
            pass
        conn.close()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print(f"Batch finished: {completed} completed, {failed} failed "
          f"(out of {len(rows)} claimed rows).")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
