"""End-to-end test of the full ingest pipeline: import → resolve → snapshot."""

from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def test_import_creates_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 0, result.stdout

    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3  # Alice, Bob, Carol


def test_import_creates_merge_decisions(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    assert paths.merge_decisions.is_file()
    lines = paths.merge_decisions.read_text().splitlines()
    # 3 contacts → 3 create events
    import json

    creates = [json.loads(line) for line in lines if '"event": "create"' in line]
    assert len(creates) == 3


def test_reimport_same_data_no_new_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_files_before = list((tmp_path / "data" / "snapshots").glob("*.jsonl"))
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_files_after = list((tmp_path / "data" / "snapshots").glob("*.jsonl"))
    # Same data → diff is empty → no new snapshot written
    assert len(snap_files_before) == len(snap_files_after)
