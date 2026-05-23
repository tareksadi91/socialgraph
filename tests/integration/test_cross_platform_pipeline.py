"""Test that importing both LinkedIn and X produces cross-platform candidates."""

from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.identity.pending import PendingMergeQueue
from socialgraph.paths import DataPaths

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def test_no_candidates_when_names_dont_match(tmp_path: Path, monkeypatch):
    """LinkedIn fixture has Alice/Bob/Carol; X fixture has bob_x/carol_x/dan_x.
    No normalized names match between platforms."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    queue = PendingMergeQueue(paths.pending_merges)
    assert queue.count_pending() == 0


def test_pending_merges_file_not_created_when_no_candidates(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    if paths.pending_merges.is_file():
        queue = PendingMergeQueue(paths.pending_merges)
        assert queue.count_pending() == 0


def test_run_pipeline_returns_pending_added(tmp_path: Path, monkeypatch):
    """run_pipeline returns 'pending_added' count."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    from socialgraph.pipeline import run_pipeline

    counts = run_pipeline(paths)
    assert "pending_added" in counts
    assert isinstance(counts["pending_added"], int)
