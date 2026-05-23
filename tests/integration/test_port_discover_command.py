"""port discover tests — Playwright is bypassed via FakeXSearchClient injection."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.scoring import XSearchResult
from socialgraph.port.state import PortState
from socialgraph.port.x_search import FakeXSearchClient

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_li_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def _build_fake_with_alice() -> FakeXSearchClient:
    return FakeXSearchClient(
        responses={
            '"Alice Example" Acme Co': [
                XSearchResult(
                    handle="alice_example",
                    display_name="Alice Example",
                    bio_preview="Founder @ Acme Co",
                ),
            ],
        },
    )


def test_port_discover_writes_state(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    fake = _build_fake_with_alice()
    with patch("socialgraph.cli.port_discover_cmd._make_search_client", return_value=fake):
        result = runner.invoke(app, ["port", "discover", "--limit", "5"])
    assert result.exit_code == 0, result.stdout
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert len(state.list_needs_review()) >= 1


def test_port_discover_skips_already_processed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    fake = _build_fake_with_alice()
    with patch("socialgraph.cli.port_discover_cmd._make_search_client", return_value=fake):
        runner.invoke(app, ["port", "discover", "--limit", "5"])
        runner.invoke(app, ["port", "discover", "--limit", "5"])
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    seen_li = {
        e.linkedin_canonical_id
        for e in (
            state.list_needs_review() + state.list_resolved_not_queued() + state.list_followed()
        )
    }
    assert len(seen_li) <= 3


def test_port_discover_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["port", "discover", "--limit", "5"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()


def test_port_discover_limit_caps_results(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    fake = _build_fake_with_alice()
    with patch("socialgraph.cli.port_discover_cmd._make_search_client", return_value=fake):
        result = runner.invoke(app, ["port", "discover", "--limit", "1"])
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert state.counts()["needs_review"] + state.counts()["rejected"] <= 1
