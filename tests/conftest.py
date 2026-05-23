"""Shared pytest fixtures for the socialgraph test suite."""
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def linkedin_fixture_path() -> Path:
    return FIXTURES_ROOT / "linkedin" / "connections_small.csv"


@pytest.fixture
def x_fixture_path() -> Path:
    return FIXTURES_ROOT / "x" / "archive_v1.zip"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Isolated data/ dir per test."""
    d = tmp_path / "data"
    d.mkdir()
    return d
