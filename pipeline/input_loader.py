"""Load parent references from CSV or Zotero API."""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from .config import InputConfig, ZoteroApiConfig
from .models import Reference

log = logging.getLogger(__name__)


def load_references_from_csv(csv_path: str | Path) -> list[Reference]:
    """Load parent references from a Zotero CSV export.

    Returns a list of Reference objects with reference_role='parent'.
    Rows without a usable title are skipped.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    refs: list[Reference] = []
    skipped = 0

    with path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            title = (row.get("Title") or "").strip()
            if not title:
                skipped += 1
                log.debug("Skipped row with no title.")
                continue
            ref = Reference.from_zotero_row(row, source_file=str(path))
            refs.append(ref)

    log.info(
        "Loaded %d references from %s (skipped %d empty).",
        len(refs), path.name, skipped,
    )
    return refs


def load_references_from_zotero(config: ZoteroApiConfig) -> list[Reference]:
    """Load references from a Zotero library or collection via the Zotero API.

    Requires the `pyzotero` package:  pip install pyzotero
    """
    try:
        from pyzotero import zotero as pz  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "pyzotero is required for Zotero API input.  "
            "Install it with:  pip install pyzotero"
        ) from exc

    if not config.api_key:
        raise ValueError(
            "Zotero API key is required.  "
            "Set input.zotero.api_key in your config YAML or set "
            "the ZOTERO_API_KEY environment variable."
        )
    if not config.library_id:
        raise ValueError("input.zotero.library_id is required.")

    zot = pz.Zotero(config.library_id, config.library_type, config.api_key)

    if config.collection_key:
        log.info(
            "Fetching items from Zotero collection %s (library %s/%s)...",
            config.collection_key, config.library_type, config.library_id,
        )
        items = zot.everything(zot.collection_items(config.collection_key))
        if config.include_subcollections:
            sub_collections = zot.collections_sub(config.collection_key)
            for sub in sub_collections:
                sub_key = sub["key"]
                log.info("  Including subcollection: %s", sub_key)
                items += zot.everything(zot.collection_items(sub_key))
    else:
        log.info(
            "Fetching all items from Zotero library %s/%s...",
            config.library_type, config.library_id,
        )
        items = zot.everything(zot.items())

    refs: list[Reference] = []
    for item in items:
        data = item.get("data", {})
        item_type = data.get("itemType", "")
        if item_type in ("note", "attachment"):
            continue

        authors = []
        for creator in data.get("creators", []):
            last = creator.get("lastName", "")
            first = creator.get("firstName", "")
            name = f"{last}, {first}".strip(", ")
            if name:
                authors.append(name)

        doi = (data.get("DOI") or "").strip()
        url = (data.get("url") or "").strip()

        import re
        scopus_m = re.search(r"scopus\.com/pages/publications/(\d+)", url)
        scopus_id = scopus_m.group(1) if scopus_m else ""

        pmid_m = re.search(r"PMID:\s*(\d+)", data.get("extra", "") or "", re.IGNORECASE)
        pmid = pmid_m.group(1) if pmid_m else ""

        ref = Reference(
            reference_role="parent",
            title=(data.get("title") or "").strip(),
            authors=authors,
            year=str(data.get("date", "") or "")[:4],
            doi=doi,
            pmid=pmid,
            scopus_id=scopus_id,
            isbn=(data.get("ISBN") or "").strip(),
            issn=(data.get("ISSN") or "").strip(),
            zotero_item_key=item.get("key", ""),
            zotero_collection_key=config.collection_key,
            source_input_file=f"zotero:{config.library_id}/{config.collection_key}",
            source_input_mode="zotero_api",
            abstract=(data.get("abstractNote") or "").strip(),
            publication_title=(data.get("publicationTitle") or data.get("bookTitle") or "").strip(),
            item_type=item_type,
            already_in_zotero=True,
            _raw=data,
        )
        refs.append(ref)

    log.info("Loaded %d references from Zotero API.", len(refs))
    return refs


def load_from_config(config: InputConfig, base_dir: Path = Path(".")) -> list[Reference]:
    """Dispatch to the appropriate loader based on config.mode."""
    if config.mode == "csv":
        if not config.csv_path:
            raise ValueError("input.csv_path is required when input.mode = 'csv'.")
        csv_path = Path(config.csv_path)
        if not csv_path.is_absolute():
            csv_path = base_dir / csv_path
        return load_references_from_csv(csv_path)

    if config.mode == "zotero_api":
        if config.zotero is None:
            raise ValueError("input.zotero settings are required when input.mode = 'zotero_api'.")
        return load_references_from_zotero(config.zotero)

    raise ValueError(f"Unknown input mode: {config.mode!r}.  Use 'csv' or 'zotero_api'.")
