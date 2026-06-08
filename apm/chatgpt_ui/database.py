"""SQLite-backed store for article processing state.

Uses WAL mode and BEGIN IMMEDIATE to safely handle concurrent writes
from multiple machines sharing the same database file over a network drive.
"""

from __future__ import annotations

import csv
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

STATUS_PENDING = "Yet To Process"
STATUS_CLAIMED = "Already Processing"
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETED = "Completed"
STATUS_FAILED = "Failed"

_DDL = """
CREATE TABLE IF NOT EXISTS articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    doi             TEXT,
    doi_hash        TEXT NOT NULL,
    title           TEXT,
    abstract        TEXT,
    raw_data        TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'Yet To Process',
    machine_id      TEXT,
    locked_at       TEXT,
    processed_at    TEXT,
    output_file     TEXT,
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_doi_hash ON articles(doi_hash);
CREATE INDEX IF NOT EXISTS idx_status       ON articles(status);
"""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def open_db(db_path: Path, timeout: float = 30.0) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=timeout, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_DDL)
    conn.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doi_hash(doi: Optional[str], title: Optional[str] = None) -> str:
    import hashlib
    key = (doi or title or "unknown").strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _find_col(headers: list[str], candidates: list[str]) -> Optional[str]:
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

def import_csv(conn: sqlite3.Connection, csv_path: Path) -> int:
    """Import new rows from a CSV file. Skips rows whose doi_hash already exists.

    Rows where every field is blank (common Excel export artifact) are silently
    dropped before deduplication so they do not consume the 'unknown' hash slot.
    """
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = list(reader.fieldnames or [])
        all_rows = list(reader)

    doi_col      = _find_col(headers, ["DOI", "doi", "Doi"])
    title_col    = _find_col(headers, ["Title", "title", "TITLE", "Article Title"])
    abstract_col = _find_col(headers, ["Abstract", "abstract", "ABSTRACT", "Abstract Note"])

    # Drop blank rows produced by Excel when saving CSV
    rows = [r for r in all_rows if any(v.strip() for v in r.values())]
    blank_skipped = len(all_rows) - len(rows)
    if blank_skipped:
        log.info("Skipped %d blank rows in %s.", blank_skipped, csv_path.name)

    existing: set[str] = {
        row[0] for row in conn.execute("SELECT doi_hash FROM articles")
    }

    inserted = 0
    with conn:
        for row in rows:
            doi      = (row.get(doi_col, "")      if doi_col      else "").strip()
            title    = (row.get(title_col, "")    if title_col    else "").strip()
            abstract = (row.get(abstract_col, "") if abstract_col else "").strip()

            if not doi and not title:
                log.debug("Skipping row with no DOI and no Title.")
                continue

            dh = _doi_hash(doi or None, title or None)

            if dh in existing:
                continue

            conn.execute(
                """
                INSERT INTO articles (doi, doi_hash, title, abstract, raw_data, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doi, dh, title, abstract, json.dumps(dict(row)), STATUS_PENDING),
            )
            existing.add(dh)
            inserted += 1

    if inserted:
        log.info("Imported %d new rows from %s.", inserted, csv_path.name)
    else:
        log.info("No new rows to import from %s.", csv_path.name)
    return inserted


# ---------------------------------------------------------------------------
# Row claiming (concurrent-safe via BEGIN IMMEDIATE)
# ---------------------------------------------------------------------------

def claim_rows(
    conn: sqlite3.Connection,
    machine_id: str,
    batch_size: int,
    max_retries: int,
    stale_lock_hours: float,
) -> list[sqlite3.Row]:
    """Atomically claim up to *batch_size* rows for this machine.

    Rows eligible for claiming:
    - status = 'Yet To Process'
    - status = 'Failed' and retry_count < max_retries
    - status = 'Already Processing' or 'In Progress' and locked_at is stale
    """
    now          = datetime.utcnow().isoformat()
    stale_cutoff = (datetime.utcnow() - timedelta(hours=stale_lock_hours)).isoformat()

    original_isolation = conn.isolation_level
    conn.isolation_level = None          # switch to manual transaction control
    conn.execute("BEGIN IMMEDIATE")
    try:
        rows = conn.execute(
            """
            SELECT id, doi, doi_hash, title, abstract, raw_data, retry_count
            FROM articles
            WHERE
                status = 'Yet To Process'
                OR (status = 'Failed'                               AND retry_count < ?)
                OR (status IN ('Already Processing','In Progress')  AND locked_at < ?)
            ORDER BY id
            LIMIT ?
            """,
            (max_retries, stale_cutoff, batch_size),
        ).fetchall()

        if rows:
            ids   = [r["id"] for r in rows]
            ph    = ",".join("?" * len(ids))
            conn.execute(
                f"""
                UPDATE articles
                SET status = 'Already Processing', machine_id = ?, locked_at = ?,
                    error_message = NULL
                WHERE id IN ({ph})
                """,
                [machine_id, now] + ids,
            )
            log.info("Claimed %d rows: %s", len(ids), ids)

        conn.execute("COMMIT")
        return list(rows)
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        conn.isolation_level = original_isolation


# ---------------------------------------------------------------------------
# Status updates
# ---------------------------------------------------------------------------

def update_status(
    conn: sqlite3.Connection,
    row_id: int,
    status: str,
    *,
    output_file: Optional[str] = None,
    error_message: Optional[str] = None,
    increment_retry: bool = False,
) -> None:
    now    = datetime.utcnow().isoformat()
    fields = ["status = ?"]
    values: list = [status]

    if status in (STATUS_COMPLETED, STATUS_FAILED):
        fields.append("processed_at = ?")
        values.append(now)

    if output_file is not None:
        fields.append("output_file = ?")
        values.append(output_file)

    fields.append("error_message = ?")
    values.append(error_message)

    if increment_retry:
        fields.append("retry_count = retry_count + 1")

    values.append(row_id)
    sql = f"UPDATE articles SET {', '.join(fields)} WHERE id = ?"
    with conn:
        conn.execute(sql, values)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def get_stats(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        r["status"]: r["cnt"]
        for r in conn.execute("SELECT status, COUNT(*) AS cnt FROM articles GROUP BY status")
    }
