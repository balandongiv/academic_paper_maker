"""Load and filter fatigue EEG output JSON files for a target theme/subtheme.

Usage:
    from apm.lit_review.aggregator import load_filtered_studies
    studies = load_filtered_studies(folder, theme_code="A", subtheme="single-channel EEG")
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON loading
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        log.debug("Skipping %s: %s", path.name, exc)
        return None


def _get_parsed(record: dict) -> dict | None:
    resp = record.get("chatgpt_response", {})
    parsed = resp.get("parsed_json")
    if parsed is not None:
        return parsed
    raw = resp.get("raw_text", "")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        # try to extract the JSON block from potentially wrapped text
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


# ---------------------------------------------------------------------------
# Theme / subtheme matching
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return text.lower().strip()


def _matches_subtheme(subthemes: list[str], target: str) -> bool:
    t = _normalise(target)
    for s in subthemes:
        if t in _normalise(s) or _normalise(s) in t:
            return True
    return False


def _find_target_theme(parsed: dict, theme_code: str, subtheme: str) -> dict | None:
    for t in parsed.get("themes", []):
        if t.get("theme_code", "").upper() == theme_code.upper():
            if _matches_subtheme(t.get("subthemes", []), subtheme):
                return t
    return None


# ---------------------------------------------------------------------------
# Study metadata extraction
# ---------------------------------------------------------------------------

def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _extract_author_year_key(source_row: dict, doi_hash: str) -> str:
    """Generate a BibTeX-safe citation key: firstauthor_year_hash4."""
    author_raw = _safe_str(source_row.get("Author") or source_row.get("author", ""))
    year_raw = _safe_str(
        source_row.get("Publication Year") or source_row.get("publication_year", "")
    )

    # First author last name
    first_author = author_raw.split(";")[0].split(",")[0].strip() if author_raw else "unknown"
    first_author = re.sub(r"[^a-zA-Z]", "", first_author).lower()[:12] or "unknown"

    year = re.sub(r"[^0-9]", "", year_raw)[:4] or "0000"
    short_hash = doi_hash[:6] if doi_hash else "000000"
    return f"{first_author}_{year}_{short_hash}"


def _build_study_record(record: dict, parsed: dict, theme_entry: dict) -> dict:
    """Build a standardised study dict for use in prompts and LaTeX."""
    source = record.get("source_row", {})
    meth = parsed.get("methodology", {})
    doi_hash = record.get("doi_hash", "")

    title = _safe_str(
        record.get("title") or source.get("Title") or source.get("title")
    )
    author = _safe_str(
        source.get("Author") or source.get("author") or record.get("author", "")
    )
    year = _safe_str(
        source.get("Publication Year") or source.get("publication_year", "")
    )
    journal = _safe_str(
        source.get("Publication Title") or source.get("publication_title", "")
    )
    doi = _safe_str(record.get("doi", ""))
    abstract = _safe_str(
        source.get("Abstract Note") or source.get("abstract", "")
    )

    eeg_channels = _safe_str(meth.get("eeg_channels_or_electrodes") or meth.get("eeg_channels"))
    dataset = _safe_str(meth.get("data_source") or meth.get("dataset"))
    method = _safe_str(
        meth.get("classification_model")
        or meth.get("model")
        or meth.get("classification_method")
        or meth.get("ml_model")
    )
    preprocessing = _safe_str(meth.get("preprocessing"))
    feature_extraction = _safe_str(meth.get("feature_extraction"))
    participants = _safe_str(meth.get("participants"))

    key_finding = _safe_str(
        parsed.get("relevance_reason") or theme_entry.get("evidence_from_abstract")
    )
    limitation = _safe_str(parsed.get("limitation") or parsed.get("limitations"))

    citation_key = _extract_author_year_key(source, doi_hash)

    subthemes = theme_entry.get("subthemes", [])

    return {
        "doi_hash": doi_hash,
        "citation_key": citation_key,
        "title": title,
        "author": author,
        "year": year,
        "journal": journal,
        "doi": doi,
        "abstract": abstract,
        "eeg_channels": eeg_channels,
        "dataset": dataset,
        "method": method,
        "preprocessing": preprocessing,
        "feature_extraction": feature_extraction,
        "participants": participants,
        "key_finding": key_finding,
        "limitation": limitation,
        "subthemes": subthemes,
        "theme_evidence": theme_entry.get("evidence_from_abstract", ""),
        "theme_confidence": theme_entry.get("confidence", ""),
        "chatgpt_raw_summary": json.dumps(parsed, ensure_ascii=False),
        "relevance_confidence": _safe_str(parsed.get("relevance_confidence")),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_filtered_studies(
    folder: str | Path,
    theme_code: str = "A",
    subtheme: str = "single-channel EEG",
) -> list[dict]:
    """Return a list of study dicts matching *theme_code* + *subtheme*.

    Only studies whose ``chatgpt_response`` could be parsed are included.
    """
    folder = Path(folder)
    json_files = sorted(folder.glob("*.json"))
    log.info("Scanning %d JSON files in %s", len(json_files), folder)

    studies: list[dict] = []
    skipped = 0

    for path in json_files:
        record = _load_json(path)
        if record is None:
            skipped += 1
            continue

        parsed = _get_parsed(record)
        if parsed is None:
            skipped += 1
            continue

        if not parsed.get("is_relevant", False):
            continue

        theme_entry = _find_target_theme(parsed, theme_code, subtheme)
        if theme_entry is None:
            continue

        study = _build_study_record(record, parsed, theme_entry)
        studies.append(study)

    log.info(
        "Found %d studies for Theme %s / '%s' (skipped %d unparseable files)",
        len(studies), theme_code, subtheme, skipped,
    )
    return studies


def select_relevant_for_paragraph(
    studies: list[dict],
    keyword_filter: list[str],
    max_count: int = 15,
) -> list[dict]:
    """Select up to *max_count* studies most relevant to a paragraph.

    If *keyword_filter* is empty, all studies are returned (up to max_count).
    Otherwise, studies whose text matches any keyword are prioritised.
    """
    if not keyword_filter:
        return studies[:max_count]

    scored: list[tuple[int, dict]] = []
    for s in studies:
        searchable = " ".join([
            s["title"], s["eeg_channels"], s["method"],
            s["key_finding"], s["feature_extraction"], " ".join(s["subthemes"]),
        ]).lower()
        score = sum(1 for kw in keyword_filter if kw.lower() in searchable)
        scored.append((score, s))

    scored.sort(key=lambda x: -x[0])
    # always include at least some studies even if no keyword match
    result = [s for _, s in scored if _ > 0][:max_count]
    if len(result) < 5:
        result = [s for _, s in scored][:max_count]
    return result
