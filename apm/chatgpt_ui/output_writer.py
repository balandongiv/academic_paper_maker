"""Build and save JSON output files for processed rows."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


def _try_parse_json(text: str) -> tuple[Optional[Any], Optional[str]]:
    """Attempt to parse *text* as JSON. Returns (parsed_value, error_string)."""
    stripped = text.strip()

    # Strip markdown code fences  ```json ... ```
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        inner = "\n".join(lines[1:-1]) if len(lines) > 2 else stripped
        stripped = inner.strip()

    try:
        return json.loads(stripped), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def build_output(
    *,
    row_id: int,
    doi: str,
    doi_hash: str,
    title: str,
    raw_data: dict,
    response_text: str,
    machine_id: str,
    status: str = "Completed",
    error: Optional[str] = None,
) -> dict:
    parsed_json, parse_error = _try_parse_json(response_text)

    return {
        "title": title,
        "doi": doi,
        "doi_hash": doi_hash,
        "source_row": {
            "row_index": row_id,
            **raw_data,
        },
        "chatgpt_response": {
            "raw_text": response_text,
            "parsed_json": parsed_json,
            "parse_error": parse_error,
        },
        "processing_metadata": {
            "machine_id": machine_id,
            "processed_at": datetime.utcnow().isoformat(),
            "status": status,
            "error": error,
        },
    }


def save_output(output_file: Path, data: dict) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    log.debug("Saved: %s", output_file.name)
