"""Core data models for the Scopus pipeline."""

from __future__ import annotations

import re
import string
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Tracking columns appended to the master list CSV
# ---------------------------------------------------------------------------

TRACKING_COLUMNS = [
    "record_id",
    "reference_role",
    "scopus_eid",
    "scopus_id",
    "pmid",
    "source_input_file",
    "source_input_mode",
    "parent_record_id",
    "parent_doi",
    "parent_scopus_eid",
    "parent_title",
    "query",
    "query_keyword",
    "has_been_processed_for_children",
    "children_last_run_at",
    "children_result_count",
    "children_exported_count",
    "already_in_zotero",
    "already_exported",
    "result_count",
]


# ---------------------------------------------------------------------------
# Normalisation helpers (module-level so models.py is self-contained)
# ---------------------------------------------------------------------------

def _norm_doi(doi: str) -> str:
    doi = str(doi).strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def _norm_title(title: str) -> str:
    t = str(title).lower()
    t = t.translate(str.maketrans("", "", string.punctuation))
    return re.sub(r"\s+", " ", t).strip()


def _extract_scopus_id_from_url(url: str) -> str:
    m = re.search(r"scopus\.com/pages/publications/(\d+)", str(url))
    return m.group(1) if m else ""


def _extract_pmid_from_extra(extra: str) -> str:
    m = re.search(r"PMID:\s*(\d+)", str(extra), re.IGNORECASE)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

@dataclass
class Reference:
    """Internal representation of a single bibliographic reference."""

    record_id: str = ""
    reference_role: str = ""       # "parent" | "child"
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    doi: str = ""
    pmid: str = ""
    scopus_eid: str = ""           # "2-s2.0-XXXXXXXXXX"
    scopus_id: str = ""            # numeric only
    isbn: str = ""
    issn: str = ""
    zotero_item_key: str = ""
    zotero_collection_key: str = ""
    source_input_file: str = ""
    source_input_mode: str = ""
    parent_record_id: str = ""
    parent_doi: str = ""
    parent_scopus_eid: str = ""
    parent_title: str = ""
    query: str = ""
    query_keyword: str = ""
    has_been_processed_for_children: bool = False
    children_last_run_at: str = ""
    children_result_count: int = 0
    children_exported_count: int = 0
    already_in_zotero: bool = False
    already_exported: bool = False
    result_count: int = 0
    abstract: str = ""
    publication_title: str = ""
    item_type: str = ""
    # Original raw data (not written to master list CSV)
    _raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.record_id:
            self.record_id = self.zotero_item_key or str(uuid.uuid4())[:12]
        if self.scopus_id and not self.scopus_eid:
            self.scopus_eid = f"2-s2.0-{self.scopus_id}"
        if self.scopus_eid and not self.scopus_id:
            m = re.search(r"2-s2\.0-(\d+)", self.scopus_eid)
            if m:
                self.scopus_id = m.group(1)
        if self.doi:
            self.doi = _norm_doi(self.doi)

    # ------------------------------------------------------------------
    # Factory: from Zotero CSV row
    # ------------------------------------------------------------------

    @classmethod
    def from_zotero_row(cls, row: dict[str, str], source_file: str = "") -> "Reference":
        url = row.get("Url", "") or ""
        scopus_id = _extract_scopus_id_from_url(url)
        pmid = _extract_pmid_from_extra(row.get("Extra", "") or "")

        authors_raw = row.get("Author", "") or ""
        authors = [a.strip() for a in re.split(r";", authors_raw) if a.strip()]

        return cls(
            reference_role="parent",
            title=(row.get("Title") or "").strip(),
            authors=authors,
            year=str(row.get("Publication Year") or "").strip(),
            doi=(row.get("DOI") or "").strip(),
            pmid=pmid,
            scopus_id=scopus_id,
            isbn=(row.get("ISBN") or "").strip(),
            issn=(row.get("ISSN") or "").strip(),
            zotero_item_key=(row.get("Key") or "").strip(),
            source_input_file=source_file,
            source_input_mode="csv",
            abstract=(row.get("Abstract Note") or "").strip(),
            publication_title=(row.get("Publication Title") or "").strip(),
            item_type=(row.get("Item Type") or "").strip(),
            already_in_zotero=True,
            _raw=row,
        )

    # ------------------------------------------------------------------
    # Factory: from parsed RIS entry dict
    # ------------------------------------------------------------------

    @classmethod
    def from_ris_entry(
        cls,
        entry: dict[str, Any],
        source_file: str = "",
        parent: Optional["Reference"] = None,
        query: str = "",
        query_keyword: str = "",
    ) -> "Reference":
        def _first(v: Any, default: str = "") -> str:
            if isinstance(v, list):
                return str(v[0]).strip() if v else default
            return str(v).strip() if v else default

        title = _first(entry.get("TI") or entry.get("T1") or "")
        authors = entry.get("AU") or []
        if isinstance(authors, str):
            authors = [authors]

        year_raw = _first(entry.get("PY") or entry.get("Y1") or "")
        year_m = re.search(r"\d{4}", year_raw)
        year = year_m.group(0) if year_m else ""

        doi = _first(entry.get("DO") or "")

        # EID from C7, AN, or N1 note
        eid = ""
        for tag in ("C7", "AN", "M3"):
            v = _first(entry.get(tag) or "")
            if "2-s2.0" in v:
                eid = v
                break
        if not eid:
            n1 = _first(entry.get("N1") or "")
            m = re.search(r"2-s2\.0-\d+", n1)
            if m:
                eid = m.group(0)

        sn = entry.get("SN") or ""
        if isinstance(sn, list):
            sn = "; ".join(str(s) for s in sn)

        ab = _first(entry.get("AB") or "")
        jn = _first(entry.get("JO") or entry.get("T2") or entry.get("J2") or "")

        ref = cls(
            reference_role="child",
            title=title,
            authors=list(authors),
            year=year,
            doi=doi,
            scopus_eid=eid,
            issn=str(sn).strip(),
            source_input_file=source_file,
            source_input_mode="scopus_ris",
            abstract=ab,
            publication_title=jn,
            item_type="journalArticle",
            query=query,
            query_keyword=query_keyword,
            _raw=entry,
        )

        if parent:
            ref.parent_record_id = parent.record_id
            ref.parent_doi = parent.doi
            ref.parent_scopus_eid = parent.scopus_eid
            ref.parent_title = parent.title

        return ref

    # ------------------------------------------------------------------
    # Serialise to a flat dict for writing to the master list CSV
    # ------------------------------------------------------------------

    def to_master_list_row(self) -> dict[str, Any]:
        authors_str = "; ".join(self.authors) if self.authors else ""
        return {
            # Zotero-compatible columns
            "Key": self.zotero_item_key,
            "Item Type": self.item_type or "journalArticle",
            "Publication Year": self.year,
            "Author": authors_str,
            "Title": self.title,
            "Publication Title": self.publication_title,
            "ISBN": self.isbn,
            "ISSN": self.issn,
            "DOI": self.doi,
            "Url": f"https://www.scopus.com/pages/publications/{self.scopus_id}" if self.scopus_id else "",
            "Abstract Note": self.abstract,
            # Tracking columns
            "record_id": self.record_id,
            "reference_role": self.reference_role,
            "scopus_eid": self.scopus_eid,
            "scopus_id": self.scopus_id,
            "pmid": self.pmid,
            "source_input_file": self.source_input_file,
            "source_input_mode": self.source_input_mode,
            "parent_record_id": self.parent_record_id,
            "parent_doi": self.parent_doi,
            "parent_scopus_eid": self.parent_scopus_eid,
            "parent_title": self.parent_title,
            "query": self.query,
            "query_keyword": self.query_keyword,
            "has_been_processed_for_children": self.has_been_processed_for_children,
            "children_last_run_at": self.children_last_run_at,
            "children_result_count": self.children_result_count,
            "children_exported_count": self.children_exported_count,
            "already_in_zotero": self.already_in_zotero,
            "already_exported": self.already_exported,
            "result_count": self.result_count,
        }


# ---------------------------------------------------------------------------
# DeduplicationResult
# ---------------------------------------------------------------------------

@dataclass
class DeduplicationResult:
    new_references: list[Reference] = field(default_factory=list)
    duplicates: list[dict[str, str]] = field(default_factory=list)
    total_input: int = 0
    new_count: int = 0
    duplicate_count: int = 0


# ---------------------------------------------------------------------------
# RunSummary
# ---------------------------------------------------------------------------

@dataclass
class RunSummary:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    run_mode: str = ""
    started_at: str = ""
    completed_at: str = ""
    input_source: str = ""
    total_parent_references: int = 0
    parents_skipped_already_processed: int = 0
    parents_processed: int = 0
    total_scopus_results: int = 0
    duplicates_detected: int = 0
    new_references_exported: int = 0
    ris_output_path: str = ""
    master_list_path: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_mode": self.run_mode,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "input_source": self.input_source,
            "total_parent_references": self.total_parent_references,
            "parents_skipped_already_processed": self.parents_skipped_already_processed,
            "parents_processed": self.parents_processed,
            "total_scopus_results": self.total_scopus_results,
            "duplicates_detected": self.duplicates_detected,
            "new_references_exported": self.new_references_exported,
            "ris_output_path": self.ris_output_path,
            "master_list_path": self.master_list_path,
            "errors": self.errors,
            "warnings": self.warnings,
        }
