"""Keyword-search workflow: search Scopus by query strings."""

from __future__ import annotations

import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from .config import PipelineConfig
from .dedup_engine import deduplicate_references
from .master_list import MasterList
from .models import Reference, RunSummary
from .ris_exporter import export_to_ris, generate_output_filename
from .run_history import append_run

log = logging.getLogger(__name__)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_keyword_search(
    config: PipelineConfig,
    base_dir: Path = Path("."),
    dry_run: bool = False,
) -> RunSummary:
    """Execute the keyword-search pipeline.

    For each keyword/query in config.keywords:
      1. Search Scopus.
      2. Retrieve matching references.
      3. Normalise metadata.
      4. Deduplicate against master list.
      5. Export only new references to RIS.
      6. Update master list.

    Parameters
    ----------
    config:
        Loaded PipelineConfig.  Must have config.run.mode == "keyword_search"
        and at least one entry in config.keywords.
    base_dir:
        Project root for resolving relative paths.
    dry_run:
        Skip browser automation; useful for testing.
    """
    summary = RunSummary(
        run_mode="keyword_search",
        started_at=datetime.now().isoformat(),
        input_source="keywords",
        total_parent_references=len(config.keywords),
    )

    if not config.keywords:
        msg = "No keywords defined in config.  Add at least one entry under 'keywords:'."
        log.error(msg)
        summary.errors.append(msg)
        summary.completed_at = datetime.now().isoformat()
        return summary

    # ------------------------------------------------------------------
    # Step 1: Load master list
    # ------------------------------------------------------------------
    ml_path = Path(config.master_list.path)
    if not ml_path.is_absolute():
        ml_path = base_dir / ml_path

    print(f"\n[1/6] Loading master list: {ml_path}")
    ml = MasterList.load(ml_path, reuse_existing=config.master_list.reuse_existing)
    _ml_rows_at_load = ml.row_count
    print(f"      {ml.summary()}")
    summary.master_list_path = str(ml_path)

    output_dir = Path(config.output.directory)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 2: Print keyword plan
    # ------------------------------------------------------------------
    print(f"\n[2/6] Keywords to search ({len(config.keywords)}):")
    for i, kw in enumerate(config.keywords, 1):
        print(f"      {i}. {kw[:80]}")

    if dry_run:
        print("\n      DRY RUN — skipping browser automation.")
        summary.warnings.append("dry_run: no Scopus queries executed.")
        summary.completed_at = datetime.now().isoformat()
        _write_summary(summary, output_dir)
        hist = append_run(summary, base_dir, output_dir,
                          _ml_rows_at_load, ml.row_count, status="dry_run")
        print(f"  Run history: {hist}")
        return summary

    # ------------------------------------------------------------------
    # Step 3: Run Scopus searches
    # ------------------------------------------------------------------
    from scopus_automation.browser import build_driver, set_download_dir
    from scopus_automation.config import ScopusConfig
    from scopus_automation.ris import parse_ris_file
    from scopus_automation.search_export import search_and_export

    scopus_cfg_path = Path(config.scopus_config_path)
    if not scopus_cfg_path.is_absolute():
        scopus_cfg_path = base_dir / scopus_cfg_path
    scopus_cfg = ScopusConfig.from_file(str(scopus_cfg_path))

    download_dir = output_dir / "keyword_raw"
    download_dir.mkdir(parents=True, exist_ok=True)
    scopus_cfg.output_dir = str(download_dir)

    driver = build_driver(scopus_cfg, download_dir=download_dir)
    set_download_dir(driver, download_dir)

    all_refs: list[Reference] = []
    per_keyword_status: list[dict] = []
    total_results = 0

    print(f"\n[3/6] Running Scopus searches...")

    try:
        for i, keyword in enumerate(config.keywords, 1):
            print(f"\n      [{i}/{len(config.keywords)}] {keyword[:70]}")

            meta = search_and_export(
                driver=driver,
                query=keyword,
                config=scopus_cfg,
                output_dir=download_dir,
            )

            n = meta.get("result_count", 0)
            ris_path = meta.get("ris_file", "")
            err = meta.get("error", "")
            total_results += n

            if ris_path and Path(ris_path).exists():
                raw_entries = parse_ris_file(ris_path)
                refs = [
                    Reference.from_ris_entry(
                        e,
                        source_file=ris_path,
                        query=keyword,
                        query_keyword=keyword,
                    )
                    for e in raw_entries
                ]
                all_refs.extend(refs)
                print(f"        → {n} results found.")
                per_keyword_status.append({
                    "keyword": keyword[:60],
                    "status": "ok",
                    "result_count": n,
                    "ris_file": ris_path,
                    "error": "",
                })
            else:
                print(f"        → {'ERROR: ' + err if err else '0 results.'}")
                per_keyword_status.append({
                    "keyword": keyword[:60],
                    "status": "error" if err else "no_results",
                    "result_count": 0,
                    "error": err,
                })

    finally:
        driver.quit()

    summary.total_scopus_results = total_results
    _write_per_keyword_status(per_keyword_status, output_dir)
    print(f"\n      Total collected (all keywords, before dedup): {len(all_refs)}")

    # ------------------------------------------------------------------
    # Step 4: Deduplicate
    # ------------------------------------------------------------------
    print(f"\n[4/6] Deduplicating {len(all_refs)} references...")
    dedup = deduplicate_references(all_refs, ml)
    summary.duplicates_detected = dedup.duplicate_count
    print(f"      New (not in master list): {dedup.new_count}")
    print(f"      Duplicates skipped:       {dedup.duplicate_count}")

    _write_duplicates_report(dedup.duplicates, output_dir)

    # ------------------------------------------------------------------
    # Step 5: Export to RIS
    # ------------------------------------------------------------------
    filename = generate_output_filename("keyword_search", config.run.output_filename)
    ris_path = output_dir / filename

    print(f"\n[5/6] Exporting {dedup.new_count} new references...")
    if dedup.new_references:
        export_to_ris(dedup.new_references, ris_path)
        summary.ris_output_path = str(ris_path)
        print(f"      Output: {ris_path}")
    else:
        print("      Nothing new to export.")
        summary.ris_output_path = ""

    summary.new_references_exported = dedup.new_count

    # ------------------------------------------------------------------
    # Step 6: Update master list
    # ------------------------------------------------------------------
    print(f"\n[6/6] Updating master list...")
    for ref in dedup.new_references:
        ml.add_or_update(ref)
        ml.mark_exported(ref)
    ml.save()
    rows_added = ml.row_count - _ml_rows_at_load
    print(f"      Master list saved: {ml.path} ({ml.row_count} rows, +{rows_added} new)")

    summary.completed_at = datetime.now().isoformat()
    _write_summary(summary, output_dir)
    hist = append_run(summary, base_dir, output_dir,
                      _ml_rows_at_load, ml.row_count, status="completed")

    # ------------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("  KEYWORD SEARCH — COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Keywords searched:           {len(config.keywords)}")
    print(f"  Total Scopus results:        {summary.total_scopus_results}")
    print(f"  Duplicates removed:          {summary.duplicates_detected}")
    print(f"  New references exported:     {summary.new_references_exported}")
    print(f"  Master list rows added:      {rows_added}")
    if summary.ris_output_path:
        print(f"\n  RIS file for Zotero import:")
        print(f"    {summary.ris_output_path}")
    print(f"\n  Master list: {summary.master_list_path}")
    print(f"  Run history: {hist}")
    print()

    return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_per_keyword_status(rows: list[dict], output_dir: Path) -> None:
    if not rows:
        return
    path = output_dir / "keyword_search_status.csv"
    fields = ["keyword", "status", "result_count", "ris_file", "error"]
    try:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        log.info("Per-keyword status saved: %s", path)
    except Exception as exc:
        log.warning("Could not write keyword status: %s", exc)


def _write_duplicates_report(duplicates: list[dict], output_dir: Path) -> None:
    if not duplicates:
        return
    path = output_dir / "keyword_duplicates_report.csv"
    fields = ["title", "year", "doi", "scopus_eid", "matched_rule",
              "matched_fingerprint", "duplicate_of"]
    try:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(duplicates)
        log.info("Duplicates report saved: %s", path)
    except Exception as exc:
        log.warning("Could not write duplicates report: %s", exc)


def _write_summary(summary: RunSummary, output_dir: Path) -> None:
    path = output_dir / "run_summary.json"
    try:
        path.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("Run summary saved: %s", path)
    except Exception as exc:
        log.warning("Could not write run summary: %s", exc)
