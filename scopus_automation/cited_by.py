"""Feature 2: Download cited-by papers for parent Scopus papers.

Flow for each parent paper:
  1. Extract the numeric paper ID from the Scopus publications URL.
  2. Build query  REFEID(2-s2.0-{paper_id})  — identical to an advanced search.
  3. Run search_and_export (the fully-working Feature 1 pipeline).
  4. Rename the downloaded RIS to  {paper_id}_cited_by.ris.
  5. After all papers are processed, combine into  {input_stem}_cite_paper.ris.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ScopusConfig
from .login import ensure_logged_in
from .search_export import search_and_export

log = logging.getLogger(__name__)

STATUS_COLUMNS = [
    "cited_by_downloaded",
    "cited_by_downloaded_at",
    "cited_by_ris_file",
    "cited_by_result_count",
    "cited_by_error",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_paper_id(link: str) -> str:
    """Extract the numeric Scopus paper ID from a publications URL."""
    m = re.search(r"/publications?/(\d+)", str(link))
    if m:
        return m.group(1)
    m = re.search(r"eid=2-s2\.0-(\d+)", str(link))
    if m:
        return m.group(1)
    parts = re.findall(r"\d+", str(link))
    return parts[-1] if parts else "unknown"


def _combine_ris_files(ris_files: list[Path], output_path: Path) -> int:
    """Concatenate multiple RIS files into one. Returns total entry count."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with output_path.open("w", encoding="utf-8") as out:
        for ris in ris_files:
            if not ris.exists():
                log.warning("RIS file not found, skipping: %s", ris)
                continue
            content = ris.read_text(encoding="utf-8", errors="replace")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")
            total += content.count("\nER  -")
    log.info("Combined %d entries into %s", total, output_path)
    return total


def _load_input_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    return pd.read_csv(path)


def _save_status(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in (".xlsx", ".xls"):
        df.to_excel(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)
    log.info("Status saved -> %s", output_path)


# ---------------------------------------------------------------------------
# Single-paper download
# ---------------------------------------------------------------------------

def download_cited_by(
    driver,
    paper_link: str,
    config: ScopusConfig,
    output_dir: Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Download RIS for all papers that cite the given Scopus paper.

    Uses REFEID() advanced search so the full Feature 1 pipeline
    (modal handling, select-all, export) is reused unchanged.
    """
    if output_dir is None:
        output_dir = config.cited_by_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    paper_id = _extract_paper_id(paper_link)
    dest_ris  = output_dir / f"{paper_id}_cited_by.ris"

    if dest_ris.exists() and not force:
        log.info("Already downloaded: %s — skipping.", dest_ris)
        return {
            "paper_id": paper_id,
            "cited_by_downloaded": True,
            "cited_by_downloaded_at": datetime.fromtimestamp(
                dest_ris.stat().st_mtime).isoformat(),
            "cited_by_ris_file": str(dest_ris),
            "cited_by_result_count": -1,
            "cited_by_error": "",
            "skipped": True,
        }

    # REFEID query finds all papers that reference this EID
    eid   = f"2-s2.0-{paper_id}"
    query = f"REFEID({eid})"
    log.info("Cited-by query for paper %s: %s", paper_id, query)
    print(f"\n  [cited-by] Paper {paper_id}")
    print(f"  Query: {query}")

    try:
        meta = search_and_export(driver, query, config, output_dir=output_dir)

        if meta.get("error") or not meta.get("ris_file"):
            err = meta.get("error", "No RIS file produced")
            log.warning("Paper %s: %s", paper_id, err)
            return {
                "paper_id": paper_id,
                "cited_by_downloaded": False,
                "cited_by_downloaded_at": "",
                "cited_by_ris_file": "",
                "cited_by_result_count": meta.get("result_count", 0),
                "cited_by_error": err,
                "skipped": False,
            }

        # Rename from the query-slug name to our expected name
        downloaded = Path(meta["ris_file"])
        if downloaded.resolve() != dest_ris.resolve():
            if dest_ris.exists():
                dest_ris.unlink()
            downloaded.rename(dest_ris)
            log.info("Saved -> %s", dest_ris)

        return {
            "paper_id": paper_id,
            "cited_by_downloaded": True,
            "cited_by_downloaded_at": datetime.now().isoformat(),
            "cited_by_ris_file": str(dest_ris),
            "cited_by_result_count": meta.get("result_count", 0),
            "cited_by_error": "",
            "skipped": False,
        }

    except Exception as exc:
        log.error("Error processing paper %s: %s", paper_id, exc)
        return {
            "paper_id": paper_id,
            "cited_by_downloaded": False,
            "cited_by_downloaded_at": "",
            "cited_by_ris_file": "",
            "cited_by_result_count": 0,
            "cited_by_error": str(exc),
            "skipped": False,
        }


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def process_csv(
    driver,
    input_file: str | Path,
    config: ScopusConfig,
    output_dir: Path | None = None,
    force: bool = False,
    link_column: str = "Link",
) -> Path:
    """
    Read parent paper links from a CSV/Excel file, download cited-by RIS for
    each paper, then combine all into  {input_stem}_cite_paper.ris.

    Returns the path to the combined RIS file.
    A per-paper status CSV is also written next to the input file.
    """
    input_file = Path(input_file)
    if output_dir is None:
        output_dir = config.cited_by_output_dir()

    df = _load_input_file(input_file)

    if link_column not in df.columns:
        raise ValueError(
            f"Column '{link_column}' not found in {input_file}. "
            f"Available: {list(df.columns)}"
        )

    for col in STATUS_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    status_path      = input_file.parent / f"{input_file.stem}_cite_status.csv"
    combined_ris_path = input_file.parent / f"{input_file.stem}_cite_paper.ris"

    ensure_logged_in(driver, config)

    collected_ris: list[Path] = []

    for idx, row in df.iterrows():
        link = str(row[link_column]).strip()
        if not link or link.lower() in ("nan", ""):
            log.debug("Row %d: empty link — skipping.", idx)
            continue

        paper_id = _extract_paper_id(link)

        already_done = (
            str(row.get("cited_by_downloaded", "")).lower() == "true"
            and str(row.get("cited_by_ris_file", "")).strip()
        )
        if already_done and not force:
            log.info("Row %d (paper %s) already processed — skipping.", idx, paper_id)
            existing = Path(str(row.get("cited_by_ris_file", "")))
            if existing.exists():
                collected_ris.append(existing)
            continue

        log.info("Processing row %d: paper %s", idx, paper_id)
        result = download_cited_by(driver, link, config, output_dir, force=force)

        df.at[idx, "cited_by_downloaded"]    = result.get("cited_by_downloaded", "")
        df.at[idx, "cited_by_downloaded_at"] = result.get("cited_by_downloaded_at", "")
        df.at[idx, "cited_by_ris_file"]      = result.get("cited_by_ris_file", "")
        df.at[idx, "cited_by_result_count"]  = result.get("cited_by_result_count", "")
        df.at[idx, "cited_by_error"]         = result.get("cited_by_error", "")

        if result.get("cited_by_ris_file"):
            p = Path(result["cited_by_ris_file"])
            if p.exists():
                collected_ris.append(p)

        _save_status(df, status_path)

    _save_status(df, status_path)

    if collected_ris:
        count = _combine_ris_files(collected_ris, combined_ris_path)
        print(f"\n  Combined {count} entries from {len(collected_ris)} paper(s)")
        print(f"  Output: {combined_ris_path}")
    else:
        print("\n  No RIS files collected — combined output not written.")

    return combined_ris_path
