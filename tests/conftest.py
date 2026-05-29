"""pytest configuration: register custom markers and shared fixtures."""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end tests that require a live Scopus browser session",
    )


@pytest.fixture(scope="session")
def test_file_dir(tmp_path_factory):
    """Return the project test_file/ directory."""
    import pathlib
    return pathlib.Path(__file__).parent.parent / "test_file"
