"""RIS deduplication with priority: DOI > EID > title+year."""

from __future__ import annotations

import csv
import re
import string
from pathlib import Path
from typing import Any

from .ris import parse_ris_file, write_ris_file


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalise_doi(doi: str) -> str:
    doi = str(doi).strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def _normalise_title(title: str) -> str:
    title = str(title).lower()
    title = title.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", title).strip()


def _get_doi(entry: dict) -> str:
    for tag in ("DO", "doi"):
        val = entry.get(tag, "")
        if isinstance(val, list):
            val = val[0] if val else ""
        if val:
            return _normalise_doi(str(val))
    return ""


def _get_eid(entry: dict) -> str:
    for tag in ("C7", "M3", "AN", "ID", "SN"):  # Scopus EID often in C7 or AN
        val = entry.get(tag, "")
        if isinstance(val, list):
            val = val[0] if val else ""
        if val and val.startswith("2-s2.0"):
            return val.strip()
    # Also check N1 note field for Scopus EID pattern
    n1 = str(entry.get("N1", ""))
    m = re.search(r"2-s2\.0-\d+", n1)
    if m:
        return m.group(0)
    return ""


def _get_title(entry: dict) -> str:
    for tag in ("TI", "T1", "title"):
        val = entry.get(tag, "")
        if isinstance(val, list):
            val = " ".join(str(v) for v in val)
        if val:
            return _normalise_title(str(val))
    return ""


def _get_year(entry: dict) -> str:
    for tag in ("PY", "Y1", "year"):
        val = entry.get(tag, "")
        if isinstance(val, list):
            val = val[0] if val else ""
        val = str(val).strip()
        m = re.search(r"\d{4}", val)
        if m:
            return m.group(0)
    return ""


def _dedup_key(entry: dict) -> tuple[str, str]:
    """Return (key_type, key_value) using priority order."""
    doi = _get_doi(entry)
    if doi:
        return "doi", doi

    eid = _get_eid(entry)
    if eid:
        return "eid", eid

    title = _get_title(entry)
    year = _get_year(entry)
    if title:
        return "title_year", f"{title}|{year}"

    return "unknown", str(entry)


# ---------------------------------------------------------------------------
# Main deduplication function
# ---------------------------------------------------------------------------

def deduplicate(
    entries: list[dict],
    source_files: list[str] | None = None,
) -> tuple[list[dict], list[dict[str, str]]]:
    """
    Remove duplicate RIS entries using priority-based key matching.

    Returns:
        unique_entries: deduplicated list
        duplicates_report: list of dicts describing each duplicate found
    """
    seen: dict[str, tuple[int, str]] = {}  # key_value → (entry_index, source_file)
    unique: list[dict] = []
    report: list[dict[str, str]] = []

    if source_files is None:
        source_files = ["unknown"] * len(entries)

    for idx, entry in enumerate(entries):
        key_type, key_value = _dedup_key(entry)
        src = source_files[idx] if idx < len(source_files) else "unknown"

        if key_value in seen:
            kept_idx, kept_src = seen[key_value]
            kept_title = _get_title(unique[kept_idx]) or "(unknown)"
            dup_title = _get_title(entry) or "(unknown)"
            report.append(
                {
                    "duplicate_key": key_value,
                    "kept_title": kept_title,
                    "duplicate_title": dup_title,
                    "kept_source_file": kept_src,
                    "duplicate_source_file": src,
                    "reason": key_type,
                }
            )
        else:
            seen[key_value] = (len(unique), src)
            unique.append(entry)

    return unique, report


# ---------------------------------------------------------------------------
# Directory-level combine
# ---------------------------------------------------------------------------

def combine_ris_directory(
    input_dir: str | Path,
    output_file: str | Path,
    report_file: str | Path | None = None,
) -> tuple[int, int]:
    """
    Recursively find all .ris files under input_dir, parse them,
    deduplicate, write combined output, and optionally write a report.

    Returns (unique_count, duplicate_count).
    """
    input_dir = Path(input_dir)
    output_file = Path(output_file)

    ris_files = sorted(input_dir.rglob("*.ris"))
    if not ris_files:
        raise FileNotFoundError(f"No .ris files found under {input_dir}")

    all_entries: list[dict] = []
    all_sources: list[str] = []

    for ris_path in ris_files:
        entries = parse_ris_file(ris_path)
        all_entries.extend(entries)
        all_sources.extend([str(ris_path)] * len(entries))

    unique, report = deduplicate(all_entries, all_sources)
    write_ris_file(unique, output_file)

    if report_file is None:
        report_file = output_file.parent / "duplicates_report.csv"

    report_file = Path(report_file)
    report_file.parent.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w", newline="", encoding="utf-8") as fh:
        fieldnames = [
            "duplicate_key",
            "kept_title",
            "duplicate_title",
            "kept_source_file",
            "duplicate_source_file",
            "reason",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report)

    return len(unique), len(report)
