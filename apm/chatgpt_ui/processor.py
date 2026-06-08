"""Per-row processing: build prompt → send to ChatGPT → save JSON output."""

from __future__ import annotations

import json
import logging
import sqlite3
import time
from pathlib import Path

from selenium import webdriver

from .config import Config
from .database import (
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    update_status,
)
from .output_writer import build_output, save_output
from .selenium_client import navigate_to_new_chat, send_prompt_and_wait

log = logging.getLogger(__name__)

# Seconds to wait between per-row retry attempts
_RETRY_PAUSE = 10


class ChatGPTServerError(RuntimeError):
    """Raised when ChatGPT returns no response after all per-row retry attempts.

    Signals the batch runner to stop processing further rows — the server is
    likely rate-limited, down, or the session has expired.
    """


def _build_prompt(template: str, title: str, abstract: str) -> str:
    parts = [template.strip()]
    if title:
        parts.append(f"\nTitle: {title}")
    if abstract:
        parts.append(f"\nAbstract: {abstract}")
    return "\n".join(parts)


def process_row(
    conn: sqlite3.Connection,
    driver: webdriver.Chrome,
    cfg: Config,
    row: sqlite3.Row,
    prompt_template: str,
) -> bool:
    """Process a single article row.

    Retries up to ``cfg.selenium.per_row_retries`` times when ChatGPT returns
    an empty response (timeout or server issue).  If every attempt fails,
    marks the row Failed and raises ``ChatGPTServerError`` to terminate the
    batch — the caller should stop sending further rows.

    Returns True on success.
    """
    row_id   = row["id"]
    doi      = row["doi"] or ""
    doi_hash = row["doi_hash"]
    title    = row["title"] or ""
    abstract = row["abstract"] or ""

    output_dir  = cfg.output_path
    output_file = output_dir / f"{doi_hash}.json"

    if output_file.exists():
        log.info("[%d] Output already exists (%s) — marking Completed.", row_id, output_file.name)
        update_status(conn, row_id, STATUS_COMPLETED, output_file=str(output_file))
        return True

    update_status(conn, row_id, STATUS_IN_PROGRESS)

    try:
        raw_data = json.loads(row["raw_data"]) if isinstance(row["raw_data"], str) else {}
    except (json.JSONDecodeError, TypeError):
        raw_data = {}

    prompt       = _build_prompt(prompt_template, title, abstract)
    max_attempts = cfg.selenium.per_row_retries
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            log.info("[%d] Attempt %d/%d — sending to ChatGPT: %s",
                     row_id, attempt, max_attempts, title[:70])
            navigate_to_new_chat(driver)

            response_text = send_prompt_and_wait(
                driver,
                prompt,
                wait_seconds=cfg.selenium.wait_seconds,
            )

            if not response_text:
                raise ValueError("ChatGPT returned an empty response.")

            # ---- success ----
            output_data = build_output(
                row_id=row_id,
                doi=doi,
                doi_hash=doi_hash,
                title=title,
                raw_data=raw_data,
                response_text=response_text,
                machine_id=cfg.processing.machine_id,
            )
            save_output(output_file, output_data)
            update_status(conn, row_id, STATUS_COMPLETED, output_file=str(output_file))
            log.info("[%d] Completed -> %s", row_id, output_file.name)
            return True

        except Exception as exc:
            last_error = exc
            if attempt < max_attempts:
                log.warning(
                    "[%d] Attempt %d/%d failed (%s: %s) — retrying in %ds ...",
                    row_id, attempt, max_attempts, type(exc).__name__, exc, _RETRY_PAUSE,
                )
                time.sleep(_RETRY_PAUSE)
            else:
                log.error(
                    "[%d] All %d attempts failed. Last error: %s: %s",
                    row_id, max_attempts, type(exc).__name__, exc,
                )

    # All attempts exhausted — mark this row failed, then signal batch termination.
    error_msg = f"{type(last_error).__name__}: {last_error}"
    update_status(conn, row_id, STATUS_FAILED, error_message=error_msg, increment_retry=True)
    raise ChatGPTServerError(
        f"Row {row_id} ({title[:60]!r}): no response after {max_attempts} attempts. "
        "Server may be down or rate-limited. Terminating batch."
    )
