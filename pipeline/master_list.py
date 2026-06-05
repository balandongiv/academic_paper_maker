"""Master reference list: load, query, update, and persist."""

from __future__ import annotations

import logging
import re
import string
from pathlib import Path
from typing import Optional

import pandas as pd

from .models import Reference, TRACKING_COLUMNS, _norm_doi, _norm_title

log = logging.getLogger(__name__)

# Zotero CSV columns we carry through in full (needed for Zotero re-import)
_ZOTERO_PASS_THROUGH = [
    "Key", "Item Type", "Publication Year", "Author", "Title",
    "Publication Title", "ISBN", "ISSN", "DOI", "Url", "Abstract Note",
    "Date", "Date Added", "Date Modified", "Access Date",
    "Pages", "Num Pages", "Issue", "Volume", "Number Of Volumes",
    "Journal Abbreviation", "Short Title", "Series", "Series Number",
    "Series Text", "Series Title", "Publisher", "Place", "Language",
    "Rights", "Type", "Archive", "Archive Location", "Library Catalog",
    "Call Number", "Extra", "Notes", "File Attachments", "Link Attachments",
    "Manual Tags", "Automatic Tags",
]

# All master-list columns (Zotero pass-through + tracking)
_ALL_COLUMNS = _ZOTERO_PASS_THROUGH + TRACKING_COLUMNS


# ---------------------------------------------------------------------------
# Fingerprint helpers
# ---------------------------------------------------------------------------

def _fp_doi(doi: str) -> str:
    d = _norm_doi(doi)
    return f"doi:{d}" if d else ""


def _fp_eid(eid: str) -> str:
    e = str(eid).strip()
    return f"eid:{e}" if e and "2-s2.0" in e else ""


def _fp_scopus_id(sid: str) -> str:
    s = str(sid).strip()
    return f"scopus_id:{s}" if s and s.isdigit() else ""


def _fp_pmid(pmid: str) -> str:
    p = str(pmid).strip()
    return f"pmid:{p}" if p and p.isdigit() else ""


def _fp_isbn(isbn: str) -> str:
    i = re.sub(r"[\s\-]", "", str(isbn)).strip()
    return f"isbn:{i}" if i else ""


def _fp_title_year(title: str, year: str) -> str:
    t = _norm_title(title)
    if not t:
        return ""
    y = re.search(r"\d{4}", str(year))
    year_s = y.group(0) if y else ""
    return f"title_year:{t}|{year_s}"


def _fp_title_author(title: str, author: str) -> str:
    t = _norm_title(title)
    if not t:
        return ""
    # Last name of first author (before first comma)
    a = str(author).split(",")[0].strip().lower()
    a = a.translate(str.maketrans("", "", string.punctuation))
    a = re.sub(r"\s+", " ", a).strip()
    return f"title_author:{t}|{a}" if a else ""


def _reference_fingerprints(ref: Reference) -> list[str]:
    fps: list[str] = []
    for f in [
        _fp_doi(ref.doi),
        _fp_eid(ref.scopus_eid),
        _fp_scopus_id(ref.scopus_id),
        _fp_pmid(ref.pmid),
        _fp_isbn(ref.isbn),
        _fp_title_year(ref.title, ref.year),
        _fp_title_author(ref.title, ref.authors[0] if ref.authors else ""),
    ]:
        if f:
            fps.append(f)
    return fps


def _row_fingerprints(row: pd.Series) -> list[str]:
    fps: list[str] = []
    for f in [
        _fp_doi(str(row.get("DOI", "") or "")),
        _fp_eid(str(row.get("scopus_eid", "") or "")),
        _fp_scopus_id(str(row.get("scopus_id", "") or "")),
        _fp_pmid(str(row.get("pmid", "") or "")),
        _fp_isbn(str(row.get("ISBN", "") or "")),
        _fp_title_year(
            str(row.get("Title", "") or ""),
            str(row.get("Publication Year", "") or ""),
        ),
        _fp_title_author(
            str(row.get("Title", "") or ""),
            str(row.get("Author", "") or ""),
        ),
    ]:
        if f:
            fps.append(f)
    return fps


# ---------------------------------------------------------------------------
# MasterList
# ---------------------------------------------------------------------------

class MasterList:
    """Pandas-backed master reference list.

    Preserves all existing Zotero CSV columns and appends tracking columns.
    """

    def __init__(self, df: pd.DataFrame, path: Path) -> None:
        self._df = df
        self._path = path
        self._fp_cache: dict[str, int] | None = None  # fingerprint → row index

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path, reuse_existing: bool = True) -> "MasterList":
        path = Path(path)
        if path.exists() and reuse_existing:
            try:
                df = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
                log.info("Loaded master list: %s (%d rows)", path, len(df))
            except Exception as exc:
                log.warning("Could not read %s: %s — starting fresh.", path, exc)
                df = pd.DataFrame()
        else:
            df = pd.DataFrame()
            log.info("Initialising new master list at %s", path)

        # Add missing tracking columns
        for col in TRACKING_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        ml = cls(df, path)
        ml._invalidate_cache()
        return ml

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _invalidate_cache(self) -> None:
        self._fp_cache = None

    def _build_cache(self) -> None:
        cache: dict[str, int] = {}
        for idx, row in self._df.iterrows():
            for fp in _row_fingerprints(row):
                if fp not in cache:
                    cache[fp] = int(idx)
        self._fp_cache = cache
        log.debug("Fingerprint cache built: %d fingerprints from %d rows.", len(cache), len(self._df))

    def _get_cache(self) -> dict[str, int]:
        if self._fp_cache is None:
            self._build_cache()
        return self._fp_cache

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def find_row_index(self, ref: Reference) -> Optional[int]:
        """Return the DataFrame row index of the matching record, or None."""
        cache = self._get_cache()
        for fp in _reference_fingerprints(ref):
            if fp in cache:
                return cache[fp]
        return None

    def find_row_index_by_fingerprints(self, fps: list[str]) -> Optional[int]:
        cache = self._get_cache()
        for fp in fps:
            if fp in cache:
                return cache[fp]
        return None

    def is_duplicate(self, ref: Reference) -> tuple[bool, str]:
        """Return (is_dup, matched_fingerprint)."""
        cache = self._get_cache()
        for fp in _reference_fingerprints(ref):
            if fp in cache:
                return True, fp
        return False, ""

    def get_parent_processed_status(self, ref: Reference) -> bool:
        idx = self.find_row_index(ref)
        if idx is None:
            return False
        val = str(self._df.at[idx, "has_been_processed_for_children"]).lower()
        return val in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_or_update(self, ref: Reference, extra_zotero_row: Optional[dict] = None) -> int:
        """Add a new row or update an existing matching row.

        Returns the row index.
        """
        idx = self.find_row_index(ref)
        row_data = ref.to_master_list_row()

        if extra_zotero_row:
            # Preserve all original Zotero CSV columns not in our row_data
            for col, val in extra_zotero_row.items():
                if col not in row_data or not row_data[col]:
                    row_data[col] = val

        if idx is not None:
            for col, val in row_data.items():
                if col in self._df.columns:
                    # Only update tracking columns; preserve Zotero cols if present
                    if col in TRACKING_COLUMNS or not self._df.at[idx, col]:
                        self._df.at[idx, col] = val
                else:
                    self._df.at[idx, col] = val
            # Updating an existing row doesn't add new fingerprints — no cache rebuild
            return int(idx)
        else:
            # Ensure all columns exist
            for col in list(row_data.keys()) + list(self._df.columns):
                if col not in row_data:
                    row_data[col] = ""
                if col not in self._df.columns:
                    self._df[col] = ""

            new_row = pd.Series({c: row_data.get(c, "") for c in self._df.columns})
            self._df = pd.concat(
                [self._df, new_row.to_frame().T], ignore_index=True
            )
            new_idx = len(self._df) - 1
            # Incrementally add new fingerprints to the cache rather than full rebuild
            if self._fp_cache is not None:
                for fp in _reference_fingerprints(ref):
                    if fp not in self._fp_cache:
                        self._fp_cache[fp] = new_idx
            log.debug("Added new record at row %d: %s", new_idx, ref.title[:60])
            return new_idx

    def mark_parent_processed(
        self,
        ref: Reference,
        result_count: int,
        exported_count: int,
        timestamp: str,
    ) -> None:
        idx = self.find_row_index(ref)
        if idx is None:
            idx = self.add_or_update(ref)

        self._df.at[idx, "has_been_processed_for_children"] = True
        self._df.at[idx, "children_last_run_at"] = timestamp
        self._df.at[idx, "children_result_count"] = result_count
        self._df.at[idx, "children_exported_count"] = exported_count

    def mark_exported(self, ref: Reference) -> None:
        idx = self.find_row_index(ref)
        if idx is not None:
            self._df.at[idx, "already_exported"] = True

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._df.to_csv(self._path, index=False, encoding="utf-8-sig")
        log.info("Master list saved: %s (%d rows)", self._path, len(self._df))

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    @property
    def row_count(self) -> int:
        return len(self._df)

    @property
    def path(self) -> Path:
        return self._path

    def get_fingerprint_count(self) -> int:
        return len(self._get_cache())

    def summary(self) -> str:
        return (
            f"MasterList({self._path.name}: {len(self._df)} rows, "
            f"{self.get_fingerprint_count()} fingerprints)"
        )
