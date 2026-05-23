"""M3 smoke: cross-platform import -> candidates -> link -> merged graph -> round-trip."""

import shutil
import tarfile
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def test_m3_both_platforms_in_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    assert snap is not None
    # 3 linkedin + 3 x = 6 persons (no names match in fixtures)
    assert len(snap.persons) == 6


def test_m3_link_reduces_person_count(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    alice_id = next(p.canonical_id for p in snap.persons if "Alice" in p.attrs.get("full_name", ""))
    dan_id = next(p.canonical_id for p in snap.persons if "dan_x" in p.attrs.get("full_name", ""))
    r = runner.invoke(app, ["link", alice_id, dan_id])
    assert r.exit_code == 0
    new_snap = SnapshotStore(paths.snapshots).read_latest()
    assert len(new_snap.persons) == 5  # 6 - 1 merged


def test_m3_unmerge_restores_count(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    alice_id = next(p.canonical_id for p in snap.persons if "Alice" in p.attrs.get("full_name", ""))
    dan_id = next(p.canonical_id for p in snap.persons if "dan_x" in p.attrs.get("full_name", ""))
    runner.invoke(app, ["link", alice_id, dan_id])
    runner.invoke(app, ["unmerge", alice_id])
    new_snap = SnapshotStore(paths.snapshots).read_latest()
    assert len(new_snap.persons) == 6  # back to original


def test_m3_round_trip_sovereignty(tmp_path: Path, monkeypatch):
    """Backup -> nuke -> restore -> rebuild -> identical graph with merged identities."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    snap = SnapshotStore(paths.snapshots).read_latest()
    alice_id = next(p.canonical_id for p in snap.persons if "Alice" in p.attrs.get("full_name", ""))
    carol_x_id = next(
        p.canonical_id for p in snap.persons if "carol_x" in p.attrs.get("full_name", "")
    )
    runner.invoke(app, ["link", alice_id, carol_x_id])
    snap_before = SnapshotStore(paths.snapshots).read_latest()
    persons_before = sorted(p.canonical_id for p in snap_before.persons)
    backup = tmp_path / "backup.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        tar.add(paths.root, arcname="data")
    shutil.rmtree(paths.root)
    with tarfile.open(backup, "r:gz") as tar:
        tar.extractall(tmp_path)
    r = runner.invoke(app, ["rebuild"])
    assert r.exit_code == 0
    snap_after = SnapshotStore(paths.snapshots).read_latest()
    persons_after = sorted(p.canonical_id for p in snap_after.persons)
    assert persons_after == persons_before
