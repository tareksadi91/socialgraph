from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.state import PortCandidate, PortState

runner = CliRunner()


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def _seed_review(tmp_path: Path, num_candidates: int = 2) -> str:
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    candidates = [
        PortCandidate(
            handle=f"alice_{i}",
            display_name="Alice",
            bio_preview="",
            score=0.9 - i * 0.1,
            rationale="",
        )
        for i in range(num_candidates)
    ]
    return state.record_discovered(linkedin_canonical_id="li-1", candidates=candidates)


def test_port_review_no_pending(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["port", "review"])
    assert result.exit_code == 0
    assert "no" in result.stdout.lower()


def test_port_review_picks_candidate(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_review(tmp_path, num_candidates=2)
    # Pick option 1 (input "1")
    result = runner.invoke(app, ["port", "review"], input="1\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    # After picking, entry moves to queued (review → resolve → queue in one step)
    queued = state.list_queued()
    assert len(queued) == 1
    assert queued[0].selected_handle == "alice_0"


def test_port_review_reject_none(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_review(tmp_path)
    result = runner.invoke(app, ["port", "review"], input="n\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert state.list_needs_review() == []
    assert state.list_resolved_not_queued() == []


def test_port_review_quit_immediately(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_review(tmp_path)
    result = runner.invoke(app, ["port", "review"], input="q\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert len(state.list_needs_review()) == 1  # untouched
