from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup_with_both_imports(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])


def _get_cid(tmp_path: Path, name_fragment: str) -> str:
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    assert snap is not None
    for p in snap.persons:
        if name_fragment.lower() in p.attrs.get("full_name", "").lower():
            return p.canonical_id
    raise AssertionError(f"person {name_fragment!r} not found")


def test_link_merges_two_persons(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_both_imports(tmp_path)
    alice_id = _get_cid(tmp_path, "Alice")
    bob_x_id = _get_cid(tmp_path, "bob_x")
    paths = DataPaths(tmp_path / "data")
    count_before = len(SnapshotStore(paths.snapshots).read_latest().persons)
    result = runner.invoke(app, ["link", alice_id, bob_x_id])
    assert result.exit_code == 0, result.stdout
    assert "linked" in result.stdout.lower() or "merged" in result.stdout.lower()
    new_snap = SnapshotStore(paths.snapshots).read_latest()
    assert len(new_snap.persons) == count_before - 1


def test_link_unknown_id_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_both_imports(tmp_path)
    result = runner.invoke(app, ["link", "nonexistent-a", "nonexistent-b"])
    assert result.exit_code != 0


def test_link_same_id_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_both_imports(tmp_path)
    alice_id = _get_cid(tmp_path, "Alice")
    result = runner.invoke(app, ["link", alice_id, alice_id])
    assert result.exit_code != 0
