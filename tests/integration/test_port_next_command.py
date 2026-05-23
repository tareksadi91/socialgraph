from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.state import PortCandidate, PortState

runner = CliRunner()


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def _seed_queued(tmp_path: Path) -> str:
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    cid = state.record_discovered(
        linkedin_canonical_id="li-1",
        candidates=[
            PortCandidate(
                handle="alice_x", display_name="Alice", bio_preview="", score=0.9, rationale=""
            )
        ],
    )
    state.resolve(cid, selected_handle="alice_x")
    state.queue(cid, x_profile_url="https://x.com/alice_x")
    return cid


def test_port_next_empty(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["port", "next"])
    assert result.exit_code == 0
    assert "no" in result.stdout.lower() or "empty" in result.stdout.lower()


def test_port_next_followed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_queued(tmp_path)
    with patch("socialgraph.cli.port_next_cmd._open_url"):
        result = runner.invoke(app, ["port", "next"], input="f\nq\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert len(state.list_followed()) == 1


def test_port_next_skipped(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_queued(tmp_path)
    with patch("socialgraph.cli.port_next_cmd._open_url"):
        result = runner.invoke(app, ["port", "next"], input="s\nq\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert len(state.list_queued()) == 0
