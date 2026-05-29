"""
End-to-end tests for Feature 2: Cited-by paper download.

Run with:
    pytest -m e2e tests/test_feature_cited_by.py

Requires a valid Scopus browser session via Chrome user profile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scopus_automation.config import ScopusConfig
from scopus_automation.ris import parse_ris_file, compare_ris_sets

INPUT_CSV = Path(__file__).parent.parent / "test_file" / "jui2026.csv"
EXPECTED_CITE_RIS = Path(__file__).parent.parent / "test_file" / "jui2026_cite_paper.ris"
TEST_PAPER_LINK = (
    "https://www.scopus.com/pages/publications/105021869515?origin=resultslist"
)


@pytest.fixture(scope="module")
def scopus_driver(tmp_path_factory):
    from scopus_automation.browser import build_driver
    from scopus_automation.login import ensure_logged_in

    cfg = ScopusConfig.from_file()
    dl_dir = tmp_path_factory.mktemp("citedby_download")
    driver = build_driver(cfg, dl_dir)
    try:
        ok = ensure_logged_in(driver, cfg)
        if not ok:
            pytest.skip("Could not authenticate with Scopus — skipping e2e tests.")
        yield driver, cfg, dl_dir
    finally:
        driver.quit()


@pytest.mark.e2e
@pytest.mark.timeout(300)
def test_cited_by_download_single_paper(scopus_driver):
    """Download cited-by papers for the test paper and verify a RIS file is produced."""
    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.cited_by import download_cited_by

    result = download_cited_by(driver, TEST_PAPER_LINK, cfg, output_dir=dl_dir)

    assert result.get("cited_by_downloaded") or result.get("cited_by_result_count") == 0, (
        f"Download failed: {result.get('cited_by_error')}"
    )


@pytest.mark.e2e
@pytest.mark.timeout(300)
def test_cited_by_ris_contains_expected_paper(scopus_driver):
    """
    Verify the cited-by RIS contains the expected citing paper from the fixture.
    """
    if not EXPECTED_CITE_RIS.exists():
        pytest.skip(f"Fixture not found: {EXPECTED_CITE_RIS}")

    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.cited_by import download_cited_by

    result = download_cited_by(driver, TEST_PAPER_LINK, cfg, output_dir=dl_dir)
    ris_path = result.get("cited_by_ris_file")

    if not ris_path or not Path(ris_path).exists():
        if result.get("cited_by_result_count") == 0:
            pytest.skip("Paper has zero citations — expected citing paper may not exist yet.")
        pytest.fail("No RIS file produced.")

    downloaded = parse_ris_file(ris_path)
    expected = parse_ris_file(EXPECTED_CITE_RIS)

    matched, missing, _ = compare_ris_sets(expected, downloaded)
    assert len(missing) == 0, (
        f"{len(missing)} expected cited-by papers missing:\n"
        + "\n".join(str(m.get("TI", m.get("DO", "?"))) for m in missing)
    )


@pytest.mark.e2e
@pytest.mark.timeout(600)
def test_process_csv_full(scopus_driver, tmp_path):
    """Process the full jui2026.csv input file."""
    if not INPUT_CSV.exists():
        pytest.skip(f"Input CSV not found: {INPUT_CSV}")

    driver, cfg, _ = scopus_driver
    from scopus_automation.cited_by import process_csv

    combined_ris = process_csv(driver, INPUT_CSV, cfg, output_dir=tmp_path)

    # process_csv returns the combined RIS path; the status CSV sits next to the input file
    status_file = INPUT_CSV.parent / f"{INPUT_CSV.stem}_cite_status.csv"
    assert status_file.exists(), f"Status CSV not created: {status_file}"

    import pandas as pd
    df = pd.read_csv(status_file)
    assert "cited_by_downloaded" in df.columns


@pytest.mark.e2e
@pytest.mark.timeout(300)
def test_skip_already_downloaded(scopus_driver, tmp_path):
    """Second call for the same paper should be skipped (not re-downloaded)."""
    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.cited_by import download_cited_by

    # First download
    r1 = download_cited_by(driver, TEST_PAPER_LINK, cfg, output_dir=dl_dir)

    # Second download without force — should be skipped
    r2 = download_cited_by(driver, TEST_PAPER_LINK, cfg, output_dir=dl_dir, force=False)
    assert r2.get("skipped") is True, "Expected second call to be skipped."
