"""
End-to-end tests for Feature 1: Search Scopus and export RIS.

Run with:
    pytest -m e2e tests/test_feature_search_export.py

Requires a valid Scopus browser session via Chrome user profile.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scopus_automation.config import ScopusConfig
from scopus_automation.ris import parse_ris_file, compare_ris_sets

TEST_QUERY = (
    'TITLE-ABS-KEY("machine learning" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026'
)
EXPECTED_RIS = Path(__file__).parent.parent / "test_file" / "ml_eeg_fatigue_driving_2026.ris"
MIN_EXPECTED_RESULTS = 1


@pytest.fixture(scope="module")
def scopus_driver(tmp_path_factory):
    """Provide a logged-in Chrome driver for e2e tests."""
    from scopus_automation.browser import build_driver
    from scopus_automation.login import ensure_logged_in

    cfg = ScopusConfig.from_file()
    dl_dir = tmp_path_factory.mktemp("search_download")
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
def test_search_returns_results(scopus_driver):
    """Search with the test query and verify at least one result is found."""
    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.search_export import search_and_export

    meta = search_and_export(driver, TEST_QUERY, cfg, output_dir=dl_dir)

    assert meta.get("result_count", 0) >= MIN_EXPECTED_RESULTS, (
        f"Expected >= {MIN_EXPECTED_RESULTS} results, got {meta.get('result_count')}"
    )


@pytest.mark.e2e
@pytest.mark.timeout(300)
def test_search_produces_ris_file(scopus_driver):
    """Verify that a non-empty RIS file is downloaded."""
    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.search_export import search_and_export

    meta = search_and_export(driver, TEST_QUERY, cfg, output_dir=dl_dir)
    ris_path = meta.get("ris_file")

    assert ris_path, "No ris_file in metadata — export may have failed."
    assert Path(ris_path).exists(), f"RIS file does not exist: {ris_path}"
    assert Path(ris_path).stat().st_size > 0, "RIS file is empty."


@pytest.mark.e2e
@pytest.mark.timeout(300)
def test_search_ris_contains_expected_papers(scopus_driver):
    """
    Compare the exported RIS against the fixture file.
    All papers in the fixture must be present in the exported file.
    """
    if not EXPECTED_RIS.exists():
        pytest.skip(f"Fixture file not found: {EXPECTED_RIS}")

    driver, cfg, dl_dir = scopus_driver
    from scopus_automation.search_export import search_and_export

    meta = search_and_export(driver, TEST_QUERY, cfg, output_dir=dl_dir)
    ris_path = meta.get("ris_file")
    if not ris_path or not Path(ris_path).exists():
        pytest.fail("Export did not produce a RIS file.")

    exported = parse_ris_file(ris_path)
    expected = parse_ris_file(EXPECTED_RIS)

    matched, missing, _ = compare_ris_sets(expected, exported)

    assert len(missing) == 0, (
        f"{len(missing)} expected papers missing from export:\n"
        + "\n".join(str(m.get("TI", m.get("DO", "?"))) for m in missing)
    )
