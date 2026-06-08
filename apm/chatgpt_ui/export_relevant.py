"""Export relevant papers from ChatGPT JSON outputs to a CSV file.

Usage
-----
# Export relevant papers (is_relevant=true) to a CSV
python -m apm.chatgpt_ui.export_relevant --config setting/chatgpt_ui/config_fatigue_eeg.yaml

# Custom output path
python -m apm.chatgpt_ui.export_relevant --config setting/chatgpt_ui/config_fatigue_eeg.yaml --output my_results.csv

# Export ALL processed papers (relevant and not relevant)
python -m apm.chatgpt_ui.export_relevant --config setting/chatgpt_ui/config_fatigue_eeg.yaml --all
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT   = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _PROJECT_ROOT / "setting" / "chatgpt_ui" / "config.yaml"

_CSV_COLUMNS = [
    "doi_hash",
    "doi",
    "title",
    "publication_year",
    "is_relevant",
    "relevance_reason",
    "data_source",
    "eeg_usage",
    "preprocessing",
    "feature_extraction",
    "machine_learning_method",
    "evaluation_method",
    "key_findings",
    "machine_id",
    "processed_at",
    "output_file",
]


def _flatten(record: dict) -> dict:
    """Flatten one JSON output file into a single CSV row dict."""
    raw        = record.get("chatgpt_response", {})
    parsed     = raw.get("parsed_json") or {}
    meta       = record.get("processing_metadata", {})
    src        = record.get("source_row", {})
    method     = parsed.get("methodology") or {}

    findings = parsed.get("key_findings") or []
    if isinstance(findings, list):
        findings_str = " | ".join(str(f) for f in findings)
    else:
        findings_str = str(findings)

    return {
        "doi_hash":               record.get("doi_hash", ""),
        "doi":                    record.get("doi", ""),
        "title":                  record.get("title", ""),
        "publication_year":       src.get("Publication Year", ""),
        "is_relevant":            parsed.get("is_relevant", ""),
        "relevance_reason":       parsed.get("relevance_reason", ""),
        "data_source":            method.get("data_source", ""),
        "eeg_usage":              method.get("eeg_usage", ""),
        "preprocessing":          method.get("preprocessing", ""),
        "feature_extraction":     method.get("feature_extraction", ""),
        "machine_learning_method": method.get("machine_learning_method", ""),
        "evaluation_method":      method.get("evaluation_method", ""),
        "key_findings":           findings_str,
        "machine_id":             meta.get("machine_id", ""),
        "processed_at":           meta.get("processed_at", ""),
        "output_file":            str(record.get("doi_hash", "")) + ".json",
    }


def export(output_folder: Path, out_csv: Path, include_all: bool = False) -> tuple[int, int]:
    """Read JSON outputs, filter relevant, write CSV.

    Returns (relevant_count, total_count).
    """
    json_files = sorted(output_folder.glob("*.json"))
    if not json_files:
        log.warning("No JSON files found in %s", output_folder)
        return 0, 0

    rows      = []
    total     = 0
    relevant  = 0

    for jf in json_files:
        try:
            record = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("Could not read %s: %s", jf.name, exc)
            continue

        total += 1
        is_rel = record.get("chatgpt_response", {}).get("parsed_json", {}) or {}
        is_rel = is_rel.get("is_relevant", False)

        if is_rel:
            relevant += 1

        if include_all or is_rel:
            rows.append(_flatten(record))

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    log.info(
        "Wrote %d rows to %s  (relevant=%d / total_processed=%d)",
        len(rows), out_csv, relevant, total,
    )
    return relevant, total


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Export relevant papers from ChatGPT JSON outputs to CSV.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", "-c",
        default=str(_DEFAULT_CONFIG),
        metavar="PATH",
        help="YAML configuration file (default: setting/chatgpt_ui/config.yaml).",
    )
    parser.add_argument(
        "--output", "-o",
        default="",
        metavar="CSV_PATH",
        help="Output CSV path. Defaults to <project_root>/relevant_papers.csv",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Export ALL processed papers, not just relevant ones.",
    )
    args = parser.parse_args(argv)

    from .config import load_config
    cfg = load_config(args.config)

    out_csv = Path(args.output) if args.output else cfg.project_path / "relevant_papers.csv"

    relevant, total = export(cfg.output_path, out_csv, include_all=args.all)

    print(f"\nProcessed : {total:,} papers")
    print(f"Relevant  : {relevant:,} papers")
    print(f"Exported  : {out_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
