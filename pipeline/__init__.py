"""Scopus Citation & Keyword Search Pipeline."""

from .run_history import append_run
from .api import (
    run_pipeline,
    load_config,
    load_references_from_csv,
    load_references_from_zotero,
    get_scopus_citing_children,
    search_scopus_by_keyword,
    load_master_list,
    update_master_list,
    deduplicate_references,
    export_to_ris,
)

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
