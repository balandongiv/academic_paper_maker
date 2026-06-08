"""Per-row processing: build prompt → send to ChatGPT → save JSON output."""

from __future__ import annotations

import json
import logging
import sqlite3
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
    """Process a single article row. Returns True on success, False on failure."""
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

    prompt = _build_prompt(prompt_template, title, abstract)

    try:
        log.info("[%d] Sending to ChatGPT: %s", row_id, title[:70])
        navigate_to_new_chat(driver)

        response_text = send_prompt_and_wait(
            driver,
            prompt,
            wait_seconds=cfg.selenium.wait_seconds,
        )

        if not response_text:
            raise ValueError("ChatGPT returned an empty response.")

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
        log.info("[%d] Completed → %s", row_id, output_file.name)
        return True

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        log.error("[%d] Failed — %s", row_id, error_msg)
        update_status(
            conn,
            row_id,
            STATUS_FAILED,
            error_message=error_msg,
            increment_retry=True,
        )
        return False
