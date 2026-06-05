"""Citation-discovery workflow: find papers citing a set of parent references."""

from __future__ import annotations

import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import PipelineConfig
from .dedup_engine import deduplicate_references
from .input_loader import load_from_config
from .master_list import MasterList
from .models import Reference, RunSummary
from .ris_exporter import export_to_ris, generate_output_filename
from .run_history import append_run

log = logging.getLogger(__name__)

# Windows console encoding guard
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_citation_discovery(
    config: PipelineConfig,
    base_dir: Path = Path("."),
    dry_run: bool = False,
) -> RunSummary:
    """Execute the full citation-discovery pipeline.

    Parameters
    ----------
    config:
        Loaded PipelineConfig.
    base_dir:
        Project root for resolving relative paths.
    dry_run:
        If True, skip browser automation (no Scopus queries).  Useful for
        testing config and deduplication logic.
    """
    summary = RunSummary(
        run_mode="citation_discovery",
        started_at=datetime.now().isoformat(),
    )

    # Resolve output directory early so it's available at all exit points
    output_dir = Path(config.output.directory)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Step 1: Load master list
    # ------------------------------------------------------------------
    ml_path = Path(config.master_list.path)
    if not ml_path.is_absolute():
        ml_path = base_dir / ml_path

    print(f"\n[1/7] Loading master list: {ml_path}")
    ml = MasterList.load(ml_path, reuse_existing=config.master_list.reuse_existing)
    _ml_rows_at_load = ml.row_count  # guard: never save fewer rows than we loaded
    print(f"      {ml.summary()}")
    summary.master_list_path = str(ml_path)

    # ------------------------------------------------------------------
    # Step 2: Load parent references
    # ------------------------------------------------------------------
    print(f"\n[2/7] Loading parent references (mode={config.input.mode})...")
    try:
        parents = load_from_config(config.input, base_dir=base_dir)
    except Exception as exc:
        msg = f"Failed to load input references: {exc}"
        log.error(msg)
        summary.errors.append(msg)
        summary.completed_at = datetime.now().isoformat()
        return summary

    summary.total_parent_references = len(parents)
    print(f"      Loaded {len(parents)} parent references.")

    # ------------------------------------------------------------------
    # Step 3: Register parents in master list + determine what to process
    # ------------------------------------------------------------------
    print(f"\n[3/7] Checking which parents are already processed...")
    to_process: list[Reference] = []
    already_processed = 0

    for ref in parents:
        extra = ref._raw  # original Zotero CSV row for pass-through
        ml.add_or_update(ref, extra_zotero_row=extra)

        already_done = ml.get_parent_processed_status(ref)
        if already_done and not config.run.force_rerun:
            already_processed += 1
            log.info("Skipping (already processed): %s", ref.title[:60])
        else:
            to_process.append(ref)

    summary.parents_skipped_already_processed = already_processed
    summary.parents_processed = len(to_process)

    print(f"      Already processed (skipped): {already_processed}")
    print(f"      To process now:              {len(to_process)}")

    if not to_process:
        print("\n      All parents already processed.  Use force_rerun=true to rerun.")
        if ml.row_count >= _ml_rows_at_load:
            ml.save()
        summary.completed_at = datetime.now().isoformat()
        _write_summary(summary, base_dir, config)
        hist = append_run(summary, base_dir, output_dir,
                          _ml_rows_at_load, ml.row_count, status="completed")
        print(f"  Run history: {hist}")
        return summary

    # ------------------------------------------------------------------
    # Step 4: Scopus cited-by queries
    # ------------------------------------------------------------------
    print(f"\n[4/7] Querying Scopus for citing papers...")

    if dry_run:
        print("      DRY RUN — skipping browser automation.")
        print(f"      Would query Scopus for {len(to_process)} parent papers.")
        for ref in to_process:
            eid = ref.scopus_eid or f"2-s2.0-{ref.scopus_id}" if ref.scopus_id else "(no EID)"
            print(f"        REFEID({eid})  —  {ref.title[:60]}")
        summary.warnings.append("dry_run: no Scopus queries executed.")
        if ml.row_count >= _ml_rows_at_load:
            ml.save()
        summary.completed_at = datetime.now().isoformat()
        _write_summary(summary, base_dir, config)
        hist = append_run(summary, base_dir, output_dir,
                          _ml_rows_at_load, ml.row_count, status="dry_run")
        print(f"  Run history: {hist}")
        return summary

    # Real Scopus queries via browser automation
    from scopus_automation.browser import build_driver, set_download_dir
    from scopus_automation.cited_by import download_cited_by
    from scopus_automation.config import ScopusConfig
    from scopus_automation.ris import parse_ris_file

    scopus_cfg_path = Path(config.scopus_config_path)
    if not scopus_cfg_path.is_absolute():
        scopus_cfg_path = base_dir / scopus_cfg_path
    scopus_cfg = ScopusConfig.from_file(str(scopus_cfg_path))

    download_dir = output_dir / "cited_by_raw"
    download_dir.mkdir(parents=True, exist_ok=True)

    scopus_cfg.output_dir = str(download_dir)

    driver = build_driver(scopus_cfg, download_dir=download_dir)
    set_download_dir(driver, download_dir)

    all_children: list[Reference] = []
    per_paper_status: list[dict] = []
    total_results = 0

    try:
        for i, parent in enumerate(to_process, 1):
            url = (
                f"https://www.scopus.com/pages/publications/{parent.scopus_id}"
                if parent.scopus_id
                else ""
            )
            if not url:
                msg = f"Parent {parent.record_id} has no Scopus URL — skipping."
                log.warning(msg)
                summary.warnings.append(msg)
                per_paper_status.append({
                    "record_id": parent.record_id,
                    "title": parent.title[:60],
                    "status": "skipped_no_url",
                    "result_count": 0,
                    "error": "no_scopus_id",
                })
                continue

            print(f"\n      [{i}/{len(to_process)}] {parent.title[:65]}")
            print(f"        EID: {parent.scopus_eid or '—'}")

            result = download_cited_by(
                driver=driver,
                paper_link=url,
                config=scopus_cfg,
                output_dir=download_dir,
                force=config.run.force_rerun,
            )

            n = result.get("cited_by_result_count", 0)
            ris_path = result.get("cited_by_ris_file", "")
            err = result.get("cited_by_error", "")
            total_results += n

            if ris_path and Path(ris_path).exists():
                raw_entries = parse_ris_file(ris_path)
                children = [
                    Reference.from_ris_entry(
                        e,
                        source_file=ris_path,
                        parent=parent,
                        query=f"REFEID({parent.scopus_eid})",
                    )
                    for e in raw_entries
                ]
                all_children.extend(children)
                print(f"        → {n} citing papers found.")
                per_paper_status.append({
                    "record_id": parent.record_id,
                    "title": parent.title[:60],
                    "status": "ok",
                    "result_count": n,
                    "ris_file": ris_path,
                    "error": "",
                })
            else:
                print(f"        → {'ERROR: ' + err if err else '0 citing papers.'}")
                per_paper_status.append({
                    "record_id": parent.record_id,
                    "title": parent.title[:60],
                    "status": "error" if err else "no_results",
                    "result_count": 0,
                    "error": err,
                })

            ml.mark_parent_processed(
                parent,
                result_count=n,
                exported_count=0,
                timestamp=datetime.now().isoformat(),
            )

    finally:
        driver.quit()

    summary.total_scopus_results = total_results
    _write_per_paper_status(per_paper_status, output_dir)

    # ------------------------------------------------------------------
    # Step 5: Deduplicate children against master list
    # ------------------------------------------------------------------
    print(f"\n[5/7] Deduplicating {len(all_children)} child references...")
    dedup = deduplicate_references(all_children, ml)
    summary.duplicates_detected = dedup.duplicate_count
    print(f"      New (not in master list): {dedup.new_count}")
    print(f"      Duplicates skipped:       {dedup.duplicate_count}")

    _write_duplicates_report(dedup.duplicates, output_dir)

    # ------------------------------------------------------------------
    # Step 6: Export to RIS
    # ------------------------------------------------------------------
    filename = generate_output_filename("citation_discovery", config.run.output_filename)
    ris_path = output_dir / filename

    print(f"\n[6/7] Exporting {dedup.new_count} new references to RIS...")
    if dedup.new_references:
        export_to_ris(dedup.new_references, ris_path)
        summary.ris_output_path = str(ris_path)
        print(f"      Output: {ris_path}")
    else:
        print("      Nothing new to export.")
        summary.ris_output_path = ""

    summary.new_references_exported = dedup.new_count

    # ------------------------------------------------------------------
    # Step 7: Update master list with new children + export status
    # ------------------------------------------------------------------
    print(f"\n[7/7] Updating master list...")
    for ref in dedup.new_references:
        ml.add_or_update(ref)
        ml.mark_exported(ref)
    # Update children_exported_count on parents
    for parent in to_process:
        child_count = sum(
            1 for r in dedup.new_references
            if r.parent_record_id == parent.record_id
        )
        ml.mark_parent_processed(
            parent,
            result_count=sum(
                s.get("result_count", 0)
                for s in per_paper_status
                if s.get("record_id") == parent.record_id
            ),
            exported_count=child_count,
            timestamp=datetime.now().isoformat(),
        )
    ml.save()
    rows_added = ml.row_count - _ml_rows_at_load
    print(f"      Master list saved: {ml.path} ({ml.row_count} rows, +{rows_added} new)")

    summary.completed_at = datetime.now().isoformat()
    _write_summary(summary, base_dir, config)
    hist = append_run(summary, base_dir, output_dir,
                      _ml_rows_at_load, ml.row_count, status="completed")

    # ------------------------------------------------------------------
    # Final report
    # ------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("  CITATION DISCOVERY — COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Parent references loaded:    {summary.total_parent_references}")
    print(f"  Parents already processed:   {summary.parents_skipped_already_processed}")
    print(f"  Parents queried now:         {summary.parents_processed}")
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
# Helper writers
# ---------------------------------------------------------------------------

def _write_per_paper_status(rows: list[dict], output_dir: Path) -> None:
    if not rows:
        return
    path = output_dir / "cited_by_per_paper_status.csv"
    fields = ["record_id", "title", "status", "result_count", "ris_file", "error"]
    try:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        log.info("Per-paper status saved: %s", path)
    except Exception as exc:
        log.warning("Could not write per-paper status: %s", exc)


def _write_duplicates_report(duplicates: list[dict], output_dir: Path) -> None:
    if not duplicates:
        return
    path = output_dir / "duplicates_report.csv"
    fields = ["title", "year", "doi", "scopus_eid", "matched_rule", "matched_fingerprint", "duplicate_of"]
    try:
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(duplicates)
        log.info("Duplicates report saved: %s", path)
    except Exception as exc:
        log.warning("Could not write duplicates report: %s", exc)


def _write_summary(summary: RunSummary, base_dir: Path, config: PipelineConfig) -> None:
    output_dir = Path(config.output.directory)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "run_summary.json"
    try:
        path.write_text(
            json.dumps(summary.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info("Run summary saved: %s", path)
    except Exception as exc:
        log.warning("Could not write run summary: %s", exc)
