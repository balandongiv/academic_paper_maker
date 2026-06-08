"""CSV inspection and validation helpers.

Provides a clean public API for examining the master CSV before it is
imported into the SQLite database via database.import_csv.

Typical usage:
    from apm.chatgpt_ui.csv_store import validate_csv, inspect_csv

    warnings = validate_csv(Path("complete_file_available_in_zotero.csv"))
    for w in warnings:
        log.warning(w)

    info = inspect_csv(csv_path)
    print(f"{info['row_count']} rows, DOI column: {info['doi_column']}")
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

_DOI_CANDIDATES      = ["DOI", "doi", "Doi"]
_TITLE_CANDIDATES    = ["Title", "title", "TITLE", "Article Title"]
_ABSTRACT_CANDIDATES = ["Abstract", "abstract", "ABSTRACT", "Abstract Note"]


def _find_col(headers: list[str], candidates: list[str]) -> Optional[str]:
    lower = {h.lower(): h for h in headers}
    for c in candidates:
        if c.lower() in lower:
            return lower[c.lower()]
    return None


def inspect_csv(csv_path: Path) -> dict:
    """Return metadata about *csv_path* without loading the full data into memory."""
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader   = csv.DictReader(fh)
        headers  = list(reader.fieldnames or [])
        row_count = sum(1 for _ in reader)

    return {
        "path":             str(csv_path),
        "row_count":        row_count,
        "column_count":     len(headers),
        "doi_column":       _find_col(headers, _DOI_CANDIDATES),
        "title_column":     _find_col(headers, _TITLE_CANDIDATES),
        "abstract_column":  _find_col(headers, _ABSTRACT_CANDIDATES),
        "all_columns":      headers,
    }


def read_csv_rows(csv_path: Path) -> list[dict]:
    """Read all rows from *csv_path* as a list of dicts."""
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def validate_csv(csv_path: Path) -> list[str]:
    """Return a list of human-readable warnings for missing recommended columns.

    An empty list means the CSV looks well-formed for import.
    """
    info     = inspect_csv(csv_path)
    warnings: list[str] = []

    if not info["doi_column"]:
        warnings.append(
            "No DOI column found — row identity will fall back to title hash. "
            f"Checked: {_DOI_CANDIDATES}"
        )
    if not info["title_column"]:
        warnings.append(
            "No Title column found — entries will have empty titles. "
            f"Checked: {_TITLE_CANDIDATES}"
        )
    if not info["abstract_column"]:
        warnings.append(
            "No Abstract column found — prompts will have no abstract body. "
            f"Checked: {_ABSTRACT_CANDIDATES}"
        )
    if info["row_count"] == 0:
        warnings.append("CSV file contains no data rows.")

    return warnings
