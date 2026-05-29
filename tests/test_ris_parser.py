"""Unit tests for RIS parsing and writing — no Scopus login required."""

import textwrap
from pathlib import Path

import pytest

from scopus_automation.ris import (
    parse_ris_file,
    write_ris_file,
    compare_ris_sets,
    _parse_ris_manual,
)


SAMPLE_RIS = textwrap.dedent("""\
    TY  - JOUR
    AU  - Smith, J.
    AU  - Doe, A.
    TI  - A study of EEG fatigue detection
    PY  - 2025
    T2  - Journal of Neural Engineering
    DO  - 10.1234/jne.2025.001
    AB  - Abstract text here.
    ER  -

    TY  - CONF
    AU  - Brown, K.
    TI  - Machine learning for driving safety
    PY  - 2024
    DO  - 10.5678/conf.2024.002
    ER  -
""")

SAMPLE_RIS_NO_DOI = textwrap.dedent("""\
    TY  - JOUR
    AU  - Jones, P.
    TI  - An untitled paper
    PY  - 2023
    ER  -
""")


# ---------------------------------------------------------------------------
# Manual parser tests
# ---------------------------------------------------------------------------

def test_manual_parser_returns_list():
    entries = _parse_ris_manual(SAMPLE_RIS)
    assert isinstance(entries, list)
    assert len(entries) == 2


def test_manual_parser_fields():
    entries = _parse_ris_manual(SAMPLE_RIS)
    first = entries[0]
    assert first["TY"] == "JOUR"
    assert first["PY"] == "2025"
    assert first["DO"] == "10.1234/jne.2025.001"


def test_manual_parser_multi_value_au():
    entries = _parse_ris_manual(SAMPLE_RIS)
    au = entries[0]["AU"]
    assert isinstance(au, list)
    assert "Smith, J." in au
    assert "Doe, A." in au


def test_manual_parser_no_doi():
    entries = _parse_ris_manual(SAMPLE_RIS_NO_DOI)
    assert len(entries) == 1
    assert "DO" not in entries[0]


# ---------------------------------------------------------------------------
# parse_ris_file tests
# ---------------------------------------------------------------------------

def test_parse_ris_file(tmp_path):
    ris_file = tmp_path / "sample.ris"
    ris_file.write_text(SAMPLE_RIS, encoding="utf-8")
    entries = parse_ris_file(ris_file)
    assert len(entries) == 2
    titles = [e.get("TI", "") for e in entries]
    assert any("EEG" in str(t) for t in titles)


def test_parse_real_test_file():
    test_ris = Path(__file__).parent.parent / "test_file" / "ml_eeg_fatigue_driving_2026.ris"
    if not test_ris.exists():
        pytest.skip("test_file/ml_eeg_fatigue_driving_2026.ris not found")
    entries = parse_ris_file(test_ris)
    assert len(entries) >= 1
    for e in entries:
        assert "TY" in e or "type_of_reference" in e


# ---------------------------------------------------------------------------
# write_ris_file tests
# ---------------------------------------------------------------------------

def test_write_and_reparse(tmp_path):
    entries = _parse_ris_manual(SAMPLE_RIS)
    out = tmp_path / "out.ris"
    write_ris_file(entries, out)
    assert out.exists()
    reparsed = parse_ris_file(out)
    assert len(reparsed) == len(entries)


def test_write_preserves_doi(tmp_path):
    entries = _parse_ris_manual(SAMPLE_RIS)
    out = tmp_path / "out.ris"
    write_ris_file(entries, out)
    reparsed = parse_ris_file(out)
    dois = [e.get("DO", "") for e in reparsed]
    assert any("10.1234" in str(d) for d in dois)


# ---------------------------------------------------------------------------
# compare_ris_sets tests
# ---------------------------------------------------------------------------

def test_compare_exact_match():
    entries = _parse_ris_manual(SAMPLE_RIS)
    matched, missing, extra = compare_ris_sets(entries, entries)
    assert len(matched) == 2
    assert len(missing) == 0
    assert len(extra) == 0


def test_compare_missing_entry():
    entries = _parse_ris_manual(SAMPLE_RIS)
    matched, missing, extra = compare_ris_sets(entries, [entries[0]])
    assert len(matched) == 1
    assert len(missing) == 1


def test_compare_extra_entry():
    entries = _parse_ris_manual(SAMPLE_RIS)
    extra_entries = _parse_ris_manual(SAMPLE_RIS + SAMPLE_RIS_NO_DOI)
    matched, missing, extra = compare_ris_sets(entries, extra_entries)
    assert len(matched) == 2
    assert len(extra) == 1


def test_compare_by_title_when_no_doi():
    a = [{"TY": "JOUR", "TI": "No Doi Paper", "PY": "2022"}]
    b = [{"TY": "JOUR", "TI": "No Doi Paper", "PY": "2022"}]
    matched, missing, extra = compare_ris_sets(a, b)
    assert len(matched) == 1
