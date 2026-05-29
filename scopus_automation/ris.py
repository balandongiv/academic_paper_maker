"""RIS file parsing, writing, and comparison utilities.

Uses a manual parser that preserves the original two-letter uppercase RIS tags
(TY, TI, AU, DO, PY, etc.) throughout the codebase.  rispy is NOT used for
load/dump because it remaps tags to lowercase descriptive names, which would
break all downstream tag lookups.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_ris_manual(text: str) -> list[dict[str, Any]]:
    """
    Parse RIS text and return list of entry dicts with uppercase tag keys.
    Multi-valued tags (AU, KW, AD, …) are stored as lists.
    """
    entries: list[dict[str, Any]] = []
    current: dict[str, list[str]] = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        # Tag lines look like:  "TY  - value"  or  "AU  -value"
        m = re.match(r"^([A-Z][A-Z0-9]{1,3})\s{0,2}-\s{0,2}(.*)$", line)
        if m:
            tag, value = m.group(1), m.group(2).strip()
            if tag == "ER":
                if current:
                    # Flatten single-element lists to plain strings
                    flat: dict[str, Any] = {
                        k: (v[0] if len(v) == 1 else v)
                        for k, v in current.items()
                    }
                    entries.append(flat)
                    current = {}
            else:
                current.setdefault(tag, []).append(value)
        # Lines without a tag (continuation lines) are ignored — Scopus RIS
        # does not use continuation lines for fields we care about.

    # Handle file without trailing ER
    if current:
        flat = {k: (v[0] if len(v) == 1 else v) for k, v in current.items()}
        entries.append(flat)

    return entries


def parse_ris_file(path: str | Path) -> list[dict[str, Any]]:
    """Parse a RIS file and return a list of entry dicts (uppercase tags)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return _parse_ris_manual(text)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_ris_file(entries: list[dict[str, Any]], path: str | Path) -> None:
    """Write RIS entries to a file using uppercase tag format."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    for entry in entries:
        for tag, value in entry.items():
            if isinstance(value, list):
                for v in value:
                    lines.append(f"{tag}  - {v}")
            else:
                lines.append(f"{tag}  - {value}")
        lines.append("ER  - ")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _doi_from_entry(entry: dict) -> str | None:
    doi = entry.get("DO") or ""
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", str(doi).strip().lower())
    return doi if doi else None


def _title_from_entry(entry: dict) -> str:
    title = entry.get("TI") or entry.get("T1") or ""
    if isinstance(title, list):
        title = " ".join(title)
    return str(title).strip().lower()


def compare_ris_sets(
    expected: list[dict], actual: list[dict]
) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Compare two RIS entry sets by DOI (preferred) or normalised title.

    Returns (matched_expected, missing_from_actual, extra_in_actual).
    """

    def keyfn(e: dict) -> str:
        doi = _doi_from_entry(e)
        if doi:
            return f"doi:{doi}"
        return f"title:{_title_from_entry(e)}"

    expected_keys = {keyfn(e): e for e in expected}
    actual_keys = {keyfn(e): e for e in actual}

    matched = [e for k, e in expected_keys.items() if k in actual_keys]
    missing = [e for k, e in expected_keys.items() if k not in actual_keys]
    extra = [e for k, e in actual_keys.items() if k not in expected_keys]

    return matched, missing, extra
