"""
Unit tests for Feature 1 (search export) and Feature 2 (cited-by) helpers.

No Scopus browser session required — all tests run offline against the
fixture files in test_file/.

Run:
    pytest tests/test_unit_features.py
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Shared paths that mirror exactly what was used in code development
# ---------------------------------------------------------------------------

TEST_FILE_DIR   = Path(__file__).parent.parent / "test_file"
SEARCH_RIS      = TEST_FILE_DIR / "ml_eeg_fatigue_driving_2026.ris"   # Feature 1 output
CITE_CSV        = TEST_FILE_DIR / "jui2026.csv"                        # Feature 2 input
CITE_RIS        = TEST_FILE_DIR / "jui2026_cite_paper.ris"            # Feature 2 output
CITE_STATUS_CSV = TEST_FILE_DIR / "jui2026_cite_status.csv"

CITE_PAPER_LINK = (
    "https://www.scopus.com/pages/publications/105021869515?origin=resultslist"
)
SEARCH_QUERY = (
    'TITLE-ABS-KEY("machine learning" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026'
)
EXPECTED_PAPER_ID = "105021869515"


# ===========================================================================
# Feature 1 — search_export helpers
# ===========================================================================

class TestQueryFilename:
    def test_produces_output(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename(SEARCH_QUERY)
        assert name, "Filename must not be empty"

    def test_no_path_separators(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename(SEARCH_QUERY)
        assert "/" not in name
        assert "\\" not in name

    def test_no_quotes_or_brackets(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename(SEARCH_QUERY)
        for ch in ('"', "'", "(", ")", "[", "]"):
            assert ch not in name, f"Illegal character '{ch}' in filename"

    def test_max_length(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename(SEARCH_QUERY)
        assert len(name) <= 80

    def test_empty_query_fallback(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename("")
        assert name == "scopus_export"

    def test_short_query(self):
        from scopus_automation.search_export import _query_to_filename
        name = _query_to_filename("EEG fatigue")
        assert "eeg" in name
        assert "fatigue" in name


class TestSearchRisFixture:
    """Validate the fixture file produced during Feature 1 development."""

    def test_fixture_exists(self):
        if not SEARCH_RIS.exists():
            pytest.skip(f"Fixture not found: {SEARCH_RIS}")
        assert SEARCH_RIS.stat().st_size > 0

    def test_parseable(self):
        if not SEARCH_RIS.exists():
            pytest.skip(f"Fixture not found: {SEARCH_RIS}")
        from scopus_automation.ris import parse_ris_file
        entries = parse_ris_file(SEARCH_RIS)
        assert len(entries) >= 1, "Fixture must contain at least one RIS entry"

    def test_required_fields_present(self):
        if not SEARCH_RIS.exists():
            pytest.skip(f"Fixture not found: {SEARCH_RIS}")
        from scopus_automation.ris import parse_ris_file
        for entry in parse_ris_file(SEARCH_RIS):
            assert "TY" in entry, f"Missing TY in entry: {entry}"
            assert "TI" in entry, f"Missing TI in entry: {entry}"
            assert "PY" in entry, f"Missing PY in entry: {entry}"

    def test_all_entries_year_2026(self):
        if not SEARCH_RIS.exists():
            pytest.skip(f"Fixture not found: {SEARCH_RIS}")
        from scopus_automation.ris import parse_ris_file
        for entry in parse_ris_file(SEARCH_RIS):
            assert str(entry.get("PY", "")) == "2026", (
                f"Expected PUBYEAR=2026, got {entry.get('PY')} in '{entry.get('TI')}'"
            )

    def test_each_entry_has_doi_or_url(self):
        if not SEARCH_RIS.exists():
            pytest.skip(f"Fixture not found: {SEARCH_RIS}")
        from scopus_automation.ris import parse_ris_file
        for entry in parse_ris_file(SEARCH_RIS):
            has_doi = bool(entry.get("DO"))
            has_url = bool(entry.get("UR"))
            assert has_doi or has_url, (
                f"Entry '{entry.get('TI')}' has neither DOI nor URL"
            )


# ===========================================================================
# Feature 2 — cited_by helpers
# ===========================================================================

class TestExtractPaperId:
    def test_publications_url(self):
        from scopus_automation.cited_by import _extract_paper_id
        assert _extract_paper_id(CITE_PAPER_LINK) == EXPECTED_PAPER_ID

    def test_eid_url(self):
        from scopus_automation.cited_by import _extract_paper_id
        link = "https://www.scopus.com/record/display.uri?eid=2-s2.0-12345&origin=resultslist"
        assert _extract_paper_id(link) == "12345"

    def test_plain_numeric_url(self):
        from scopus_automation.cited_by import _extract_paper_id
        link = "https://www.scopus.com/publications/99887766"
        assert _extract_paper_id(link) == "99887766"

    def test_unknown_url_returns_something(self):
        from scopus_automation.cited_by import _extract_paper_id
        result = _extract_paper_id("https://example.com/no-numbers-here-abc")
        assert result == "unknown"


class TestRefeidQueryConstruction:
    def test_query_format(self):
        from scopus_automation.cited_by import _extract_paper_id
        pid = _extract_paper_id(CITE_PAPER_LINK)
        query = f"REFEID(2-s2.0-{pid})"
        assert query == f"REFEID(2-s2.0-{EXPECTED_PAPER_ID})"

    def test_query_used_in_search_export(self):
        """Verify the REFEID query passes through _query_to_filename cleanly."""
        from scopus_automation.cited_by import _extract_paper_id
        from scopus_automation.search_export import _query_to_filename
        pid = _extract_paper_id(CITE_PAPER_LINK)
        query = f"REFEID(2-s2.0-{pid})"
        name = _query_to_filename(query)
        assert name
        assert "/" not in name
        assert len(name) <= 80


class TestInputCsvFixture:
    """Validate the input CSV used during Feature 2 development."""

    def test_csv_exists(self):
        if not CITE_CSV.exists():
            pytest.skip(f"CSV not found: {CITE_CSV}")
        assert CITE_CSV.stat().st_size > 0

    def test_link_column_present(self):
        if not CITE_CSV.exists():
            pytest.skip(f"CSV not found: {CITE_CSV}")
        from scopus_automation.cited_by import _load_input_file
        df = _load_input_file(CITE_CSV)
        assert "Link" in df.columns, f"'Link' column missing. Got: {list(df.columns)}"

    def test_at_least_one_row(self):
        if not CITE_CSV.exists():
            pytest.skip(f"CSV not found: {CITE_CSV}")
        from scopus_automation.cited_by import _load_input_file
        df = _load_input_file(CITE_CSV)
        assert len(df) >= 1

    def test_links_are_scopus_urls(self):
        if not CITE_CSV.exists():
            pytest.skip(f"CSV not found: {CITE_CSV}")
        from scopus_automation.cited_by import _load_input_file
        df = _load_input_file(CITE_CSV)
        for link in df["Link"].dropna():
            assert "scopus.com" in str(link), f"Not a Scopus URL: {link}"

    def test_second_row_link_matches_expected(self):
        """The paper used in development is in the second data row (index 0)."""
        if not CITE_CSV.exists():
            pytest.skip(f"CSV not found: {CITE_CSV}")
        from scopus_automation.cited_by import _extract_paper_id, _load_input_file
        df = _load_input_file(CITE_CSV)
        link = str(df["Link"].iloc[0]).strip()
        pid = _extract_paper_id(link)
        assert pid == EXPECTED_PAPER_ID, (
            f"Expected paper ID {EXPECTED_PAPER_ID}, got {pid} from link {link}"
        )


class TestCiteRisFixture:
    """Validate the cited-by RIS output produced during Feature 2 development."""

    def test_fixture_exists(self):
        if not CITE_RIS.exists():
            pytest.skip(f"Fixture not found: {CITE_RIS}")
        assert CITE_RIS.stat().st_size > 0

    def test_parseable(self):
        if not CITE_RIS.exists():
            pytest.skip(f"Fixture not found: {CITE_RIS}")
        from scopus_automation.ris import parse_ris_file
        entries = parse_ris_file(CITE_RIS)
        assert len(entries) >= 1

    def test_required_fields(self):
        if not CITE_RIS.exists():
            pytest.skip(f"Fixture not found: {CITE_RIS}")
        from scopus_automation.ris import parse_ris_file
        for entry in parse_ris_file(CITE_RIS):
            assert "TY" in entry
            assert "TI" in entry

    def test_does_not_contain_parent_paper(self):
        """The cited-by file must contain citing papers, not the parent itself."""
        if not CITE_RIS.exists():
            pytest.skip(f"Fixture not found: {CITE_RIS}")
        from scopus_automation.ris import parse_ris_file
        entries = parse_ris_file(CITE_RIS)
        urls = [str(e.get("UR", "")) for e in entries]
        for url in urls:
            assert EXPECTED_PAPER_ID not in url, (
                "Parent paper's own URL should not appear in cited-by output"
            )


class TestCombineRisFiles:
    def test_single_file_output(self, tmp_path):
        if not CITE_RIS.exists():
            pytest.skip(f"Fixture not found: {CITE_RIS}")
        from scopus_automation.cited_by import _combine_ris_files
        out = tmp_path / "combined.ris"
        count = _combine_ris_files([CITE_RIS], out)
        assert out.exists()
        assert out.stat().st_size > 0
        assert count >= 1

    def test_two_files_concatenated(self, tmp_path):
        from scopus_automation.cited_by import _combine_ris_files
        ris1 = tmp_path / "a.ris"
        ris2 = tmp_path / "b.ris"
        ris1.write_text(
            "TY  - JOUR\nTI  - Paper One\nPY  - 2025\nER  -\n", encoding="utf-8"
        )
        ris2.write_text(
            "TY  - JOUR\nTI  - Paper Two\nPY  - 2026\nER  -\n", encoding="utf-8"
        )
        out = tmp_path / "combined.ris"
        _combine_ris_files([ris1, ris2], out)
        content = out.read_text(encoding="utf-8")
        assert "Paper One" in content
        assert "Paper Two" in content

    def test_missing_file_skipped_no_crash(self, tmp_path):
        from scopus_automation.cited_by import _combine_ris_files
        real = tmp_path / "real.ris"
        real.write_text(
            "TY  - JOUR\nTI  - Real\nPY  - 2025\nER  -\n", encoding="utf-8"
        )
        ghost = tmp_path / "ghost.ris"  # does not exist
        out = tmp_path / "out.ris"
        _combine_ris_files([real, ghost], out)  # must not raise
        assert out.exists()
        assert "Real" in out.read_text(encoding="utf-8")

    def test_output_parseable_after_combine(self, tmp_path):
        from scopus_automation.cited_by import _combine_ris_files
        from scopus_automation.ris import parse_ris_file
        ris = tmp_path / "src.ris"
        ris.write_text(
            "TY  - JOUR\nTI  - Test Paper\nDO  - 10.0/test\nPY  - 2025\nER  -\n",
            encoding="utf-8",
        )
        out = tmp_path / "combined.ris"
        _combine_ris_files([ris], out)
        entries = parse_ris_file(out)
        assert len(entries) == 1
        assert entries[0]["TI"] == "Test Paper"

    def test_creates_parent_directories(self, tmp_path):
        from scopus_automation.cited_by import _combine_ris_files
        ris = tmp_path / "src.ris"
        ris.write_text(
            "TY  - JOUR\nTI  - X\nPY  - 2025\nER  -\n", encoding="utf-8"
        )
        nested_out = tmp_path / "deep" / "nested" / "combined.ris"
        _combine_ris_files([ris], nested_out)
        assert nested_out.exists()


class TestStatusCsvFixture:
    """Validate the status CSV written by process_csv."""

    def test_status_csv_exists(self):
        if not CITE_STATUS_CSV.exists():
            pytest.skip(f"Status CSV not found: {CITE_STATUS_CSV}")
        assert CITE_STATUS_CSV.stat().st_size > 0

    def test_status_csv_has_required_columns(self):
        if not CITE_STATUS_CSV.exists():
            pytest.skip(f"Status CSV not found: {CITE_STATUS_CSV}")
        import pandas as pd
        df = pd.read_csv(CITE_STATUS_CSV)
        for col in ("cited_by_downloaded", "cited_by_ris_file", "cited_by_result_count"):
            assert col in df.columns, f"Missing column: {col}"

    def test_status_csv_paper_downloaded(self):
        if not CITE_STATUS_CSV.exists():
            pytest.skip(f"Status CSV not found: {CITE_STATUS_CSV}")
        import pandas as pd
        df = pd.read_csv(CITE_STATUS_CSV)
        assert df["cited_by_downloaded"].iloc[0] == True
