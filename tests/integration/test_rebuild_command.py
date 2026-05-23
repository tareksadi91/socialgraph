from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def test_rebuild_rebuilds_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    # Delete snapshot to simulate corruption
    paths = DataPaths(tmp_path / "data")
    for f in paths.snapshots.glob("*.jsonl"):
        f.unlink()
    # Rebuild from parsed JSONL
    result = runner.invoke(app, ["rebuild"])
    assert result.exit_code == 0, result.stdout
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3


def test_rebuild_with_no_parsed_data(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["rebuild"])
    assert result.exit_code == 0
    assert "no parsed" in result.stdout.lower() or "nothing" in result.stdout.lower()
