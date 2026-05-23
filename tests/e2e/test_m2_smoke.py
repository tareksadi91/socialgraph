"""M2 smoke: import → resolve → graph → query → round-trip sovereignty."""

import json
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


def test_m2_full_pipeline(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)

    # 1. Import and pipeline
    r = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert r.exit_code == 0
    assert "graph updated" in r.stdout
    assert "3 persons" in r.stdout

    # 2. Snapshot exists
    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3
    assert len(snap.companies) >= 1  # Acme Co, Beta Corp

    # 3. merge_decisions.jsonl has 3 create events
    creates = [
        json.loads(line)
        for line in paths.merge_decisions.read_text().splitlines()
        if '"event": "create"' in line
    ]
    assert len(creates) == 3

    # 4. who-at works
    r = runner.invoke(app, ["who-at", "Acme Co"])
    assert r.exit_code == 0
    assert "Alice Example" in r.stdout
    assert "Carol Test" in r.stdout

    # 5. status shows graph counts
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert "3 persons" in r.stdout

    # 6. Re-import → no new snapshot (idempotent)
    snap_count_before = len(list(paths.snapshots.glob("*.jsonl")))
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_count_after = len(list(paths.snapshots.glob("*.jsonl")))
    assert snap_count_before == snap_count_after


def test_m2_round_trip_sovereignty(tmp_path: Path, monkeypatch):
    """Round-trip test: backup data/ → nuke → restore → rebuild → identical graph."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)

    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])

    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap_before = store.read_latest()
    assert snap_before is not None

    # Canonical state: sorted canonical_ids
    persons_before = sorted(p.canonical_id for p in snap_before.persons)
    companies_before = sorted(c.canonical_id for c in snap_before.companies)

    # Backup
    backup = tmp_path / "backup.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        tar.add(paths.root, arcname="data")

    # Nuke
    shutil.rmtree(paths.root)
    assert not paths.root.exists()

    # Restore
    with tarfile.open(backup, "r:gz") as tar:
        tar.extractall(tmp_path)

    assert paths.root.exists()

    # Rebuild from restored flat files
    r = runner.invoke(app, ["rebuild"])
    assert r.exit_code == 0

    # Verify identical state
    snap_after = store.read_latest()
    assert snap_after is not None
    persons_after = sorted(p.canonical_id for p in snap_after.persons)
    companies_after = sorted(c.canonical_id for c in snap_after.companies)
    assert persons_after == persons_before
    assert companies_after == companies_before
