"""Append-only run history log for the Scopus pipeline.

Every completed run (full or dry) appends one row to:
    setting/scopus_setup/run_history.csv

This gives a permanent audit trail showing:
- How many rows were added to complete_file_available_in_zotero.csv
- How many child RIS files were downloaded
- Full run summary for every invocation
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import RunSummary

log = logging.getLogger(__name__)

# Columns written to run_history.csv — order is fixed for readability
HISTORY_FIELDS = [
    "timestamp",
    "run_id",
    "run_mode",
    "status",                      # "completed" | "dry_run" | "error"
    "duration_sec",
    "input_source",
    "parent_references_loaded",
    "parents_processed",
    "parents_skipped_already_processed",
    "total_scopus_results",
    "duplicates_removed",
    "new_references_exported",
    "master_list_rows_before",
    "master_list_rows_after",
    "master_list_rows_added",      # = after - before
    "ris_files_downloaded",        # count of *_cited_by.ris or keyword .ris files
    "ris_output_file",
    "master_list_path",
    "errors",
    "warnings",
]


def _history_path(base_dir: Path) -> Path:
    return base_dir / "setting" / "scopus_setup" / "run_history.csv"


def _duration_sec(started_at: str, completed_at: str) -> float:
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        start = datetime.strptime(started_at[:26], fmt)
        end   = datetime.strptime(completed_at[:26], fmt)
        return round((end - start).total_seconds(), 1)
    except Exception:
        return 0.0


def _count_ris_downloads(output_dir: Path, run_mode: str) -> int:
    """Count per-parent or per-keyword RIS files actually downloaded this session."""
    if run_mode == "citation_discovery":
        raw_dir = output_dir / "cited_by_raw"
        if raw_dir.exists():
            return len(list(raw_dir.glob("*_cited_by.ris")))
    elif run_mode == "keyword_search":
        raw_dir = output_dir / "keyword_raw"
        if raw_dir.exists():
            return len([f for f in raw_dir.glob("*.ris")
                        if not f.name.startswith("scopus_export")])
    return 0


def append_run(
    summary: "RunSummary",
    base_dir: Path,
    output_dir: Path,
    master_list_rows_before: int,
    master_list_rows_after: int,
    status: str = "completed",
) -> Path:
    """Append one row to run_history.csv.  Creates the file + header if needed.

    Parameters
    ----------
    summary:
        The RunSummary produced by the pipeline.
    base_dir:
        Project root (used to locate run_history.csv).
    output_dir:
        Where the pipeline wrote its output (for counting downloaded RIS files).
    master_list_rows_before:
        Master list row count recorded at the start of the run.
    master_list_rows_after:
        Master list row count after the run (0 if not saved).
    status:
        "completed", "dry_run", or "error".
    """
    hist_path = _history_path(base_dir)
    hist_path.parent.mkdir(parents=True, exist_ok=True)

    rows_added = max(0, master_list_rows_after - master_list_rows_before)
    ris_dl     = _count_ris_downloads(output_dir, summary.run_mode)
    duration   = _duration_sec(summary.started_at, summary.completed_at or datetime.now().isoformat())

    row = {
        "timestamp":                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "run_id":                           summary.run_id,
        "run_mode":                         summary.run_mode,
        "status":                           status,
        "duration_sec":                     duration,
        "input_source":                     summary.input_source or "",
        "parent_references_loaded":         summary.total_parent_references,
        "parents_processed":                summary.parents_processed,
        "parents_skipped_already_processed": summary.parents_skipped_already_processed,
        "total_scopus_results":             summary.total_scopus_results,
        "duplicates_removed":               summary.duplicates_detected,
        "new_references_exported":          summary.new_references_exported,
        "master_list_rows_before":          master_list_rows_before,
        "master_list_rows_after":           master_list_rows_after,
        "master_list_rows_added":           rows_added,
        "ris_files_downloaded":             ris_dl,
        "ris_output_file":                  Path(summary.ris_output_path).name if summary.ris_output_path else "",
        "master_list_path":                 summary.master_list_path,
        "errors":                           "; ".join(summary.errors) if summary.errors else "",
        "warnings":                         "; ".join(summary.warnings) if summary.warnings else "",
    }

    write_header = not hist_path.exists()
    with hist_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=HISTORY_FIELDS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        writer.writerow(row)

    log.info(
        "Run history appended: %s | master_list +%d rows | %d RIS files downloaded | status=%s",
        hist_path.name, rows_added, ris_dl, status,
    )
    return hist_path
