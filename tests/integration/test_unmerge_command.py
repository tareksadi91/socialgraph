from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup_with_link(tmp_path: Path) -> tuple[str, str]:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    assert snap is not None
    alice_id = next(p.canonical_id for p in snap.persons if "Alice" in p.attrs.get("full_name", ""))
    bob_x_id = next(p.canonical_id for p in snap.persons if "bob_x" in p.attrs.get("full_name", ""))
    runner.invoke(app, ["link", alice_id, bob_x_id])
    return alice_id, bob_x_id


def test_unmerge_restores_separate_persons(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    alice_id, _ = _setup_with_link(tmp_path)
    paths = DataPaths(tmp_path / "data")
    count_after_link = len(SnapshotStore(paths.snapshots).read_latest().persons)
    result = runner.invoke(app, ["unmerge", alice_id])
    assert result.exit_code == 0, result.stdout
    new_count = len(SnapshotStore(paths.snapshots).read_latest().persons)
    assert new_count >= count_after_link


def test_unmerge_unknown_id_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["unmerge", "nonexistent-uuid"])
    assert result.exit_code != 0
