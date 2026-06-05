"""Top-level public API for the Scopus pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .citation_discovery import run_citation_discovery
from .config import PipelineConfig, ZoteroApiConfig, load_config
from .dedup_engine import deduplicate_references
from .input_loader import load_references_from_csv, load_references_from_zotero
from .keyword_search import run_keyword_search
from .master_list import MasterList
from .models import DeduplicationResult, Reference, RunSummary
from .ris_exporter import export_to_ris


def run_pipeline(
    config_path: str,
    base_dir: str | Path | None = None,
    dry_run: bool = False,
) -> RunSummary:
    """Load config and run the appropriate pipeline workflow.

    Parameters
    ----------
    config_path:
        Path to the pipeline YAML config file.
    base_dir:
        Project root for resolving relative paths in the config.
        Defaults to the directory containing the config file.
    dry_run:
        Skip browser/Scopus automation.
    """
    cfg = load_config(config_path)

    if base_dir is None:
        base_dir = Path(config_path).resolve().parent
    base_dir = Path(base_dir)

    if cfg.run.mode == "citation_discovery":
        return run_citation_discovery(cfg, base_dir=base_dir, dry_run=dry_run)
    elif cfg.run.mode == "keyword_search":
        return run_keyword_search(cfg, base_dir=base_dir, dry_run=dry_run)
    else:
        raise ValueError(
            f"Unknown run.mode: {cfg.run.mode!r}.  "
            "Use 'citation_discovery' or 'keyword_search'."
        )


def load_master_list(path: str) -> MasterList:
    """Load (or initialise) the master reference list from a CSV file."""
    return MasterList.load(path, reuse_existing=True)


def update_master_list(
    master_list: MasterList,
    records: list[Reference],
) -> None:
    """Add or update records in the master list and save."""
    for ref in records:
        master_list.add_or_update(ref)
    master_list.save()


def get_scopus_citing_children(
    parent_reference: Reference,
    driver,
    scopus_config,
    output_dir: str | Path,
    force: bool = False,
) -> list[Reference]:
    """Download citing papers for one parent reference and return as References.

    Parameters
    ----------
    parent_reference:
        The parent paper to search for.
    driver:
        Active Selenium WebDriver.
    scopus_config:
        ScopusConfig instance.
    output_dir:
        Directory to save the raw RIS download.
    force:
        Re-download even if the RIS file already exists.
    """
    from scopus_automation.cited_by import download_cited_by
    from scopus_automation.ris import parse_ris_file

    url = (
        f"https://www.scopus.com/pages/publications/{parent_reference.scopus_id}"
        if parent_reference.scopus_id
        else ""
    )
    if not url:
        return []

    result = download_cited_by(
        driver=driver,
        paper_link=url,
        config=scopus_config,
        output_dir=Path(output_dir),
        force=force,
    )

    ris_path = result.get("cited_by_ris_file", "")
    if not ris_path or not Path(ris_path).exists():
        return []

    raw_entries = parse_ris_file(ris_path)
    return [
        Reference.from_ris_entry(
            e,
            source_file=ris_path,
            parent=parent_reference,
            query=f"REFEID({parent_reference.scopus_eid})",
        )
        for e in raw_entries
    ]


def search_scopus_by_keyword(
    keyword: str,
    driver,
    scopus_config,
    output_dir: str | Path,
) -> list[Reference]:
    """Search Scopus by a keyword/query and return results as References.

    Parameters
    ----------
    keyword:
        Scopus advanced search query string.
    driver:
        Active Selenium WebDriver.
    scopus_config:
        ScopusConfig instance.
    output_dir:
        Directory to save the raw RIS download.
    """
    from scopus_automation.ris import parse_ris_file
    from scopus_automation.search_export import search_and_export

    meta = search_and_export(
        driver=driver,
        query=keyword,
        config=scopus_config,
        output_dir=Path(output_dir),
    )

    ris_path = meta.get("ris_file", "")
    if not ris_path or not Path(ris_path).exists():
        return []

    raw_entries = parse_ris_file(ris_path)
    return [
        Reference.from_ris_entry(
            e,
            source_file=ris_path,
            query=keyword,
            query_keyword=keyword,
        )
        for e in raw_entries
    ]


__all__ = [
    "run_pipeline",
    "load_config",
    "load_references_from_csv",
    "load_references_from_zotero",
    "get_scopus_citing_children",
    "search_scopus_by_keyword",
    "load_master_list",
    "update_master_list",
    "deduplicate_references",
    "export_to_ris",
]
