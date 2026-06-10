"""CLI entry point for the literature-review writing pipeline.

Usage:
    python -m apm.lit_review.run_pipeline
    python -m apm.lit_review.run_pipeline --config setting/lit_review/config.yaml
    python -m apm.lit_review.run_pipeline --filter-only      # only filter studies, no ChatGPT
    python -m apm.lit_review.run_pipeline --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the fatigue-EEG literature-review writing pipeline."
    )
    p.add_argument(
        "--config",
        default="setting/lit_review/config.yaml",
        help="Path to the pipeline config YAML (default: setting/lit_review/config.yaml).",
    )
    p.add_argument(
        "--filter-only",
        action="store_true",
        help="Only filter and save the study list — do NOT run ChatGPT writing.",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Skip paragraphs whose .tex files already exist on disk.",
    )
    p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    return p.parse_args()


def main() -> None:
    args = _args()
    _setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    log.info("Loading pipeline config: %s", args.config)

    try:
        from apm.lit_review.pipeline import load_pipeline_config, run_pipeline
        from apm.lit_review.aggregator import load_filtered_studies
    except ImportError as exc:
        log.error("Import error: %s — ensure you are running from the project root.", exc)
        sys.exit(1)

    try:
        config = load_pipeline_config(args.config)
    except Exception as exc:
        log.error("Failed to load config: %s", exc)
        sys.exit(1)

    if args.filter_only:
        log.info("--filter-only mode: loading and filtering studies only.")
        outputs_folder = config.project_root / config.fatigue_eeg_outputs_folder
        studies = load_filtered_studies(
            outputs_folder, config.theme_code, config.subtheme
        )
        from apm.lit_review.pipeline import _make_subfolder_name
        subfolder = _make_subfolder_name(config.theme_code, config.subtheme)
        out = (
            config.project_root
            / config.writing_folder
            / subfolder
            / "filtered_studies.json"
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(studies, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        log.info("Filtered %d studies → %s", len(studies), out)
        print(f"\nFiltered {len(studies)} studies for Theme {config.theme_code} / '{config.subtheme}'.")
        print(f"Saved to: {out}")
        return

    if args.resume:
        config.resume = True
        log.info("--resume mode: existing paragraph .tex files will be skipped.")

    log.info("Starting full pipeline...")
    try:
        run_pipeline(config)
    except KeyboardInterrupt:
        log.warning("Pipeline interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        log.error("Pipeline failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
