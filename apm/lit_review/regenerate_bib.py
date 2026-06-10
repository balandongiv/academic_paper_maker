"""Regenerate writing/references.bib from all filtered_studies.json files found
across theme subfolders.

Usage:
    python -m apm.lit_review.regenerate_bib
    python -m apm.lit_review.regenerate_bib --config setting/lit_review/config.yaml

Behaviour:
  - Scans writing/ for all */filtered_studies.json files (one per theme run).
  - Merges all studies into a single references.bib at writing/references.bib.
  - Deduplicates by citation_key.
  - Always includes ALL studies from each filtered list (not just cited ones),
    so that bibtex has a complete pool for all themes.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger(__name__)


def _latex_escape(text: str) -> str:
    if not text:
        return ""
    for src, dst in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")]:
        text = text.replace(src, dst)
    return text


def _format_authors(author_str: str) -> str:
    if not author_str:
        return "Unknown Author"
    return " and ".join(a.strip() for a in author_str.split(";") if a.strip())


def _clean_doi(doi: str) -> str:
    return doi.strip().lstrip("https://doi.org/").lstrip("http://dx.doi.org/")


def build_entry(s: dict) -> str:
    key = s["citation_key"]
    title = _latex_escape(s.get("title", ""))
    author = _latex_escape(_format_authors(s.get("author", "")))
    year = s.get("year", "0000")
    journal = _latex_escape(s.get("journal", ""))
    doi = _clean_doi(s.get("doi", ""))

    lines = [
        f"@article{{{key},",
        f"  author  = {{{author}}},",
        f"  title   = {{{{{title}}}}},",
        f"  year    = {{{year}}},",
    ]
    if journal:
        lines.append(f"  journal = {{{journal}}},")
    if doi:
        lines.append(f"  doi     = {{{doi}}},")
        lines.append(f"  url     = {{https://doi.org/{doi}}},")
    lines.append("}")
    return "\n".join(lines)


def collect_all_studies(writing_root: Path) -> list[dict]:
    """Scan writing/ for all */filtered_studies.json and merge them."""
    all_studies: list[dict] = []
    seen_keys: set[str] = set()

    json_files = sorted(writing_root.glob("*/filtered_studies.json"))
    if not json_files:
        log.warning("No filtered_studies.json files found under %s", writing_root)
        return []

    for jf in json_files:
        studies = json.loads(jf.read_text(encoding="utf-8"))
        before = len(seen_keys)
        for s in studies:
            k = s["citation_key"]
            if k not in seen_keys:
                seen_keys.add(k)
                all_studies.append(s)
        added = len(seen_keys) - before
        log.info("  %s → %d studies (%d new)", jf.parent.name, len(studies), added)

    return all_studies


def regenerate(config_path: str) -> None:
    import yaml

    with open(config_path, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    writing_root = Path(raw["project_root"]) / raw["output"]["writing_folder"]

    if not writing_root.exists():
        log.error("Writing root not found: %s", writing_root)
        sys.exit(1)

    log.info("Scanning theme folders under: %s", writing_root)
    all_studies = collect_all_studies(writing_root)

    if not all_studies:
        log.error("No studies collected — check that pipeline has been run at least once.")
        sys.exit(1)

    log.info("Total unique studies: %d", len(all_studies))

    seen: set[str] = set()
    entries: list[str] = []
    for s in all_studies:
        k = s["citation_key"]
        if k in seen:
            continue
        seen.add(k)
        entries.append(build_entry(s))

    header = (
        "% BibTeX — EEG-based Driver Fatigue Detection Literature Review\n"
        "% Single combined bibliography for all themes.\n"
        f"% Generated from {len(entries)} unique studies across all theme folders.\n\n"
    )
    content = header + "\n\n".join(entries) + "\n"

    bib_path = writing_root / "references.bib"
    bib_path.write_text(content, encoding="utf-8")
    log.info("Saved %s  (%d entries, %d chars)", bib_path, len(entries), len(content))
    print(f"\nDone. BibTeX written to:\n  {bib_path}\n  Entries: {len(entries)}")


def main() -> None:
    p = argparse.ArgumentParser(description="Regenerate writing/references.bib from all theme filtered_studies.json files")
    p.add_argument("--config", default="setting/lit_review/config.yaml")
    args = p.parse_args()
    regenerate(args.config)


if __name__ == "__main__":
    main()
