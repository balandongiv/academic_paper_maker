"""Export keyword-filtered candidate papers from the SQLite database to CSV.

Applies AND-combined keyword groups against title + abstract so you can
review what the SQL pre-filter is catching before committing ChatGPT calls.

Usage
-----
# Export with default EEG-fatigue-driver filter
python -m apm.chatgpt_ui.export_candidates --config setting/chatgpt_ui/config_fatigue_eeg.yaml

# Custom output path
python -m apm.chatgpt_ui.export_candidates --config setting/chatgpt_ui/config_fatigue_eeg.yaml --output my_candidates.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT   = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PROJECT_ROOT / "setting" / "chatgpt_ui" / "config.yaml"

# ---------------------------------------------------------------------------
# Keyword groups — a row must match at least one term from EACH group (AND)
# ---------------------------------------------------------------------------
KEYWORD_GROUPS: list[tuple[str, list[str]]] = [
    ("EEG", [
        "eeg", "electroencephalog",
    ]),
    ("Fatigue/Drowsiness", [
        "fatigue", "drowsiness", "drowsy", "sleepiness", "vigilance",
        "alertness", "inattention",
    ]),
    ("Driver/Driving", [
        "driver", "driving",
    ]),
]


def _build_filter_sql() -> str:
    """Return the WHERE clause that AND-combines all keyword groups."""
    group_clauses = []
    for _label, terms in KEYWORD_GROUPS:
        term_clauses = []
        for t in terms:
            term_clauses.append(f'LOWER(title) LIKE "%{t}%"')
            term_clauses.append(f'LOWER(abstract) LIKE "%{t}%"')
        group_clauses.append("(" + " OR ".join(term_clauses) + ")")
    return "\nAND ".join(group_clauses)


_CSV_COLUMNS = [
    "id", "doi_hash", "doi", "title", "publication_year", "abstract",
    "author", "publication_title", "status",
]


def export(conn: sqlite3.Connection, out_csv: Path) -> int:
    where = _build_filter_sql()
    sql   = f"SELECT id, doi_hash, doi, title, abstract, raw_data, status FROM articles WHERE {where} ORDER BY id"
    rows  = conn.execute(sql).fetchall()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            raw = json.loads(r["raw_data"]) if r["raw_data"] else {}
            writer.writerow({
                "id":               r["id"],
                "doi_hash":         r["doi_hash"],
                "doi":              r["doi"] or "",
                "title":            r["title"] or "",
                "publication_year": raw.get("Publication Year", ""),
                "abstract":         r["abstract"] or "",
                "author":           raw.get("Author", ""),
                "publication_title": raw.get("Publication Title", ""),
                "status":           r["status"],
            })

    log.info("Exported %d keyword-filtered candidates to %s", len(rows), out_csv)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Export keyword-filtered candidate papers to CSV for manual review.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", "-c", default=str(_DEFAULT_CONFIG), metavar="PATH")
    parser.add_argument("--output", "-o", default="", metavar="CSV_PATH",
                        help="Output CSV path. Defaults to <project_root>/candidates_eeg_fatigue_driver.csv")
    args = parser.parse_args(argv)

    from .config import load_config
    from .database import open_db, init_db

    cfg     = load_config(args.config)
    out_csv = Path(args.output) if args.output else cfg.project_path / "candidates_eeg_fatigue_driver.csv"

    conn = open_db(cfg.db_path)
    init_db(conn)

    total_in_db = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    n = export(conn, out_csv)
    conn.close()

    print(f"\nTotal papers in DB : {total_in_db:,}")
    print(f"Keyword-filtered   : {n:,}")
    print(f"Exported to        : {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
