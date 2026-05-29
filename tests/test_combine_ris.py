"""Unit tests for RIS deduplication — no Scopus login required."""

import textwrap
from pathlib import Path

import pytest

from scopus_automation.ris import _parse_ris_manual
from scopus_automation.dedupe import (
    deduplicate,
    combine_ris_directory,
    _normalise_doi,
    _normalise_title,
    _get_doi,
    _get_eid,
    _dedup_key,
)


ENTRY_A = {"TY": "JOUR", "TI": "Paper Alpha", "DO": "10.1111/alpha.001", "PY": "2024"}
ENTRY_B = {"TY": "JOUR", "TI": "Paper Beta", "DO": "10.2222/beta.002", "PY": "2024"}
ENTRY_A_DUP = {"TY": "JOUR", "TI": "Paper Alpha Again", "DO": "10.1111/alpha.001", "PY": "2024"}
ENTRY_C_NO_DOI = {"TY": "CONF", "TI": "Conference Paper Gamma", "PY": "2023"}
ENTRY_C_DUP_NO_DOI = {"TY": "CONF", "TI": "Conference Paper Gamma", "PY": "2023"}
ENTRY_EID = {"TY": "JOUR", "TI": "EID Paper", "N1": "2-s2.0-12345678", "PY": "2022"}
ENTRY_EID_DUP = {"TY": "JOUR", "TI": "EID Paper Dup", "N1": "2-s2.0-12345678", "PY": "2022"}


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def test_normalise_doi_strips_url():
    assert _normalise_doi("https://doi.org/10.1111/x") == "10.1111/x"
    assert _normalise_doi("http://dx.doi.org/10.1111/x") == "10.1111/x"


def test_normalise_doi_lowercase():
    assert _normalise_doi("10.1111/ABC") == "10.1111/abc"


def test_normalise_title_strips_punctuation():
    t = _normalise_title("EEG-based Fatigue Detection, A Study!")
    assert "!" not in t
    assert "-" not in t
    assert "eeg" in t


# ---------------------------------------------------------------------------
# Key extraction
# ---------------------------------------------------------------------------

def test_get_doi():
    assert _get_doi(ENTRY_A) == "10.1111/alpha.001"
    assert _get_doi(ENTRY_C_NO_DOI) == ""


def test_get_eid():
    assert _get_eid(ENTRY_EID) == "2-s2.0-12345678"
    assert _get_eid(ENTRY_A) == ""


def test_dedup_key_prefers_doi():
    key_type, key = _dedup_key(ENTRY_A)
    assert key_type == "doi"
    assert "alpha.001" in key


def test_dedup_key_uses_eid_fallback():
    key_type, key = _dedup_key(ENTRY_EID)
    assert key_type == "eid"


def test_dedup_key_uses_title_year():
    key_type, key = _dedup_key(ENTRY_C_NO_DOI)
    assert key_type == "title_year"
    assert "gamma" in key


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_no_duplicates():
    entries = [ENTRY_A, ENTRY_B]
    unique, report = deduplicate(entries)
    assert len(unique) == 2
    assert len(report) == 0


def test_doi_deduplication():
    entries = [ENTRY_A, ENTRY_A_DUP, ENTRY_B]
    unique, report = deduplicate(entries)
    assert len(unique) == 2
    assert len(report) == 1
    assert report[0]["reason"] == "doi"


def test_eid_deduplication():
    entries = [ENTRY_EID, ENTRY_EID_DUP]
    unique, report = deduplicate(entries)
    assert len(unique) == 1
    assert report[0]["reason"] == "eid"


def test_title_year_deduplication():
    entries = [ENTRY_C_NO_DOI, ENTRY_C_DUP_NO_DOI]
    unique, report = deduplicate(entries)
    assert len(unique) == 1
    assert report[0]["reason"] == "title_year"


def test_keeps_first_occurrence():
    entries = [ENTRY_A, ENTRY_A_DUP]
    unique, report = deduplicate(entries)
    assert unique[0]["TI"] == "Paper Alpha"


def test_report_has_source_files():
    entries = [ENTRY_A, ENTRY_A_DUP]
    sources = ["file1.ris", "file2.ris"]
    _, report = deduplicate(entries, source_files=sources)
    assert report[0]["kept_source_file"] == "file1.ris"
    assert report[0]["duplicate_source_file"] == "file2.ris"


def test_mixed_key_types():
    entries = [ENTRY_A, ENTRY_B, ENTRY_EID, ENTRY_C_NO_DOI, ENTRY_C_DUP_NO_DOI]
    unique, report = deduplicate(entries)
    assert len(unique) == 4
    assert len(report) == 1


# ---------------------------------------------------------------------------
# combine_ris_directory
# ---------------------------------------------------------------------------

SAMPLE_RIS_1 = textwrap.dedent("""\
    TY  - JOUR
    TI  - Paper One
    DO  - 10.9999/one
    PY  - 2024
    ER  -
""")

SAMPLE_RIS_2 = textwrap.dedent("""\
    TY  - JOUR
    TI  - Paper Two
    DO  - 10.9999/two
    PY  - 2024
    ER  -

    TY  - JOUR
    TI  - Paper One duplicate
    DO  - 10.9999/one
    PY  - 2024
    ER  -
""")


def test_combine_ris_directory(tmp_path):
    (tmp_path / "a.ris").write_text(SAMPLE_RIS_1, encoding="utf-8")
    (tmp_path / "b.ris").write_text(SAMPLE_RIS_2, encoding="utf-8")

    out = tmp_path / "out" / "combined.ris"
    report = tmp_path / "out" / "report.csv"

    unique_count, dup_count = combine_ris_directory(tmp_path, out, report)

    assert unique_count == 2
    assert dup_count == 1
    assert out.exists()
    assert report.exists()


def test_combine_ris_no_files_raises(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        combine_ris_directory(empty, tmp_path / "out.ris")


def test_combine_ris_output_parseable(tmp_path):
    from scopus_automation.ris import parse_ris_file

    (tmp_path / "x.ris").write_text(SAMPLE_RIS_1, encoding="utf-8")
    out = tmp_path / "combined.ris"
    combine_ris_directory(tmp_path, out)
    entries = parse_ris_file(out)
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# CSV reading / filename generation helpers
# ---------------------------------------------------------------------------

def test_query_to_filename():
    from scopus_automation.search_export import _query_to_filename
    name = _query_to_filename(
        'TITLE-ABS-KEY("machine learning" AND EEG AND fatigue AND driving) AND PUBYEAR = 2026'
    )
    assert name
    assert "/" not in name
    assert "\\" not in name
    assert len(name) <= 80


def test_extract_paper_id_from_link():
    from scopus_automation.cited_by import _extract_paper_id
    link = "https://www.scopus.com/pages/publications/105021869515?origin=resultslist"
    assert _extract_paper_id(link) == "105021869515"


def test_extract_paper_id_from_eid():
    from scopus_automation.cited_by import _extract_paper_id
    link = "https://www.scopus.com/record/display.uri?eid=2-s2.0-12345&origin=resultslist"
    assert _extract_paper_id(link) == "12345"
