"""Export References to a RIS file."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Reference

log = logging.getLogger(__name__)

# Mapping from RIS type strings to Zotero item types (informational)
_TY_MAP = {
    "journalArticle": "JOUR",
    "book": "BOOK",
    "bookSection": "CHAP",
    "conferencePaper": "CONF",
    "thesis": "THES",
    "report": "RPRT",
    "webpage": "ELEC",
}


def _reference_to_ris_entry(ref: Reference) -> dict:
    """Convert a Reference to an RIS entry dict.

    If the Reference was created from a RIS entry (_raw is a RIS dict),
    the original entry is returned with tracking fields patched in.
    Otherwise, a new entry is built from Reference fields.
    """
    raw = ref._raw or {}

    # If the raw dict looks like a parsed RIS entry (has TY or TI tag), use it
    if raw.get("TY") or raw.get("TI"):
        entry = dict(raw)
        # Ensure TY is present
        if "TY" not in entry:
            entry["TY"] = _TY_MAP.get(ref.item_type, "JOUR")
        return entry

    # Build from Reference fields
    entry: dict = {}
    ty = _TY_MAP.get(ref.item_type, "JOUR")
    entry["TY"] = ty

    if ref.authors:
        entry["AU"] = list(ref.authors)
    if ref.title:
        entry["TI"] = ref.title
    if ref.year:
        entry["PY"] = ref.year
    if ref.doi:
        entry["DO"] = ref.doi
    if ref.publication_title:
        entry["JO"] = ref.publication_title
    if ref.issn:
        entry["SN"] = ref.issn
    if ref.abstract:
        entry["AB"] = ref.abstract
    if ref.scopus_eid:
        entry["C7"] = ref.scopus_eid
    if ref.scopus_id:
        entry["AN"] = f"2-s2.0-{ref.scopus_id}"

    return entry


def _ris_entries_to_text(entries: list[dict]) -> str:
    """Convert a list of RIS entry dicts to a RIS-format string."""
    lines: list[str] = []
    for entry in entries:
        for tag, value in entry.items():
            if isinstance(value, list):
                for v in value:
                    lines.append(f"{tag}  - {v}")
            elif value:
                lines.append(f"{tag}  - {value}")
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def export_to_ris(
    references: list[Reference],
    output_path: str | Path,
) -> str:
    """Write references to a RIS file.  Returns the absolute path string."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    entries = [_reference_to_ris_entry(r) for r in references]
    text = _ris_entries_to_text(entries)
    output_path.write_text(text, encoding="utf-8")

    log.info("Exported %d references to %s", len(references), output_path)
    return str(output_path.resolve())


def generate_output_filename(
    mode: str = "citation_discovery",
    override: Optional[str] = None,
) -> str:
    """Return a filename for the RIS output.

    Uses the override if provided, otherwise generates one with the current
    date and time.
    """
    if override:
        return override
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    prefix = "scopus_children" if mode == "citation_discovery" else "scopus_export"
    return f"{prefix}_{ts}.ris"
