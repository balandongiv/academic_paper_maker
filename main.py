#!/usr/bin/env python3
"""
Scopus Automation CLI

Commands:
  search       Search Scopus and export RIS files
  cited-by     Download cited-by papers for parent papers from a CSV/Excel file
  combine-ris  Combine multiple RIS files and remove duplicates
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from scopus_automation.config import ScopusConfig, DEFAULT_CONFIG_FILE
from scopus_automation.logging_setup import setup_logging

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

def _common_options(fn):
    fn = click.option(
        "--profile-path",
        default=None,
        help="Chrome user data directory (overrides config file).",
    )(fn)
    fn = click.option(
        "--profile-name",
        default=None,
        help="Chrome profile name, e.g. 'Default' (overrides config file).",
    )(fn)
    fn = click.option(
        "--chromedriver",
        default=None,
        help="Path to chromedriver.exe (overrides config file).",
    )(fn)
    fn = click.option(
        "--config",
        "config_file",
        default=DEFAULT_CONFIG_FILE,
        show_default=True,
        help="Path to JSON config file.",
    )(fn)
    fn = click.option(
        "--headless",
        is_flag=True,
        default=False,
        help="Run Chrome in headless mode (not recommended for login-sensitive workflows).",
    )(fn)
    return fn


def _build_config(config_file, profile_path, profile_name, chromedriver, headless) -> ScopusConfig:
    cfg = ScopusConfig.from_file(config_file)
    if profile_path:
        cfg.chrome_profile_path = profile_path
    if profile_name:
        cfg.chrome_profile_name = profile_name
    if chromedriver:
        cfg.chromedriver_path = chromedriver
    if headless:
        cfg.headless = True
    return cfg


def _make_driver(cfg: ScopusConfig, download_dir: Path):
    from scopus_automation.browser import build_driver, set_download_dir
    driver = build_driver(cfg, download_dir)
    # For remote-debug sessions, set download dir via CDP (prefs aren't applied at launch)
    set_download_dir(driver, download_dir)
    return driver


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.option("--verbose", "-v", is_flag=True, default=False, help="Enable debug logging.")
@click.pass_context
def cli(ctx, verbose):
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    level = logging.DEBUG if verbose else logging.INFO
    cfg = ScopusConfig.from_file(DEFAULT_CONFIG_FILE)
    cfg.ensure_dirs()
    setup_logging(cfg.logs_dir(), level=level)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@cli.command("search")
@click.option("--query", "-q", default=None, help="Single advanced search query string.")
@click.option(
    "--queries-file", "-f", default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="Text file with one query per line.",
)
@click.option(
    "--output-dir", "-o", default=None,
    help="Directory to save RIS files (default: output/search).",
)
@_common_options
@click.pass_context
def cmd_search(ctx, query, queries_file, output_dir, config_file, profile_path,
               profile_name, chromedriver, headless):
    """Search Scopus and export results as RIS files."""
    if not query and not queries_file:
        click.echo("Error: provide --query or --queries-file.", err=True)
        sys.exit(1)

    cfg = _build_config(config_file, profile_path, profile_name, chromedriver, headless)
    cfg.ensure_dirs()

    out = Path(output_dir) if output_dir else cfg.search_output_dir()
    out.mkdir(parents=True, exist_ok=True)

    driver = _make_driver(cfg, download_dir=out)
    try:
        from scopus_automation.search_export import search_and_export, search_from_file

        if query:
            meta = search_and_export(driver, query, cfg, output_dir=out)
            if meta.get("ris_file"):
                click.echo(f"Exported {meta['result_count']} documents -> {meta['ris_file']}")
            else:
                click.echo(f"No results or export failed: {meta.get('error', '')}", err=True)

        if queries_file:
            results = search_from_file(driver, queries_file, cfg, output_dir=out)
            for r in results:
                status = r.get("ris_file") or r.get("error", "unknown error")
                click.echo(f"  {r['query'][:60]}... -> {status}")
    finally:
        driver.quit()


# ---------------------------------------------------------------------------
# cited-by
# ---------------------------------------------------------------------------

@cli.command("cited-by")
@click.option(
    "--input", "-i", "input_file", required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="CSV or Excel file with a 'Link' column of Scopus paper URLs.",
)
@click.option(
    "--output-dir", "-o", default=None,
    help="Directory to save cited-by RIS files (default: output/cited_by).",
)
@click.option(
    "--link-column", default="Link", show_default=True,
    help="Column name containing the Scopus paper URLs.",
)
@click.option("--force", is_flag=True, default=False, help="Re-download already processed papers.")
@_common_options
@click.pass_context
def cmd_cited_by(ctx, input_file, output_dir, link_column, force,
                 config_file, profile_path, profile_name, chromedriver, headless):
    """Download cited-by papers for each paper in a CSV/Excel file."""
    cfg = _build_config(config_file, profile_path, profile_name, chromedriver, headless)
    cfg.ensure_dirs()

    out = Path(output_dir) if output_dir else cfg.cited_by_output_dir()
    out.mkdir(parents=True, exist_ok=True)

    driver = _make_driver(cfg, download_dir=out)
    try:
        from scopus_automation.cited_by import process_csv
        combined_ris = process_csv(
            driver, input_file, cfg,
            output_dir=out,
            force=force,
            link_column=link_column,
        )
        click.echo(f"Done. Combined RIS: {combined_ris}")
    finally:
        driver.quit()


# ---------------------------------------------------------------------------
# combine-ris
# ---------------------------------------------------------------------------

@cli.command("combine-ris")
@click.option(
    "--input-dir", "-i", required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Directory to search recursively for .ris files.",
)
@click.option(
    "--output", "-o", default=None,
    help="Output path for the combined unique RIS file.",
)
@click.option(
    "--report", default=None,
    help="Path for the duplicates report CSV (default: same dir as output).",
)
@click.pass_context
def cmd_combine_ris(ctx, input_dir, output, report):
    """Combine all .ris files in a directory and remove duplicates."""
    from scopus_automation.dedupe import combine_ris_directory

    cfg = ScopusConfig.from_file(DEFAULT_CONFIG_FILE)
    cfg.ensure_dirs()

    out_file = Path(output) if output else cfg.combined_output_dir() / "combined_unique.ris"
    report_file = Path(report) if report else out_file.parent / "duplicates_report.csv"

    unique_count, dup_count = combine_ris_directory(input_dir, out_file, report_file)
    click.echo(f"Combined: {unique_count} unique entries, {dup_count} duplicates removed.")
    click.echo(f"Output  : {out_file}")
    click.echo(f"Report  : {report_file}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
