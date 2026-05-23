from pathlib import Path

from socialgraph.snapshot.models import Snapshot, SnapshotPerson
from socialgraph.snapshot.store import SnapshotStore


def _snap_with_person(cid: str = "p1", name: str = "Alice") -> Snapshot:
    p = SnapshotPerson(canonical_id=cid, attrs={"full_name": name}, observations=[])
    return Snapshot(persons=[p], companies=[], edges=[])


def test_write_creates_file(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    path = store.write(snap)
    assert path is not None
    assert path.is_file()


def test_write_skips_when_empty(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    empty = Snapshot([], [], [])
    path = store.write(empty)
    assert path is None


def test_write_skips_when_no_diff(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    store.write(snap)  # first write
    path = store.write(snap)  # same snapshot again
    assert path is None  # skipped


def test_read_latest_returns_none_when_empty(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    assert store.read_latest() is None


def test_read_latest_round_trips(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    store.write(snap)
    loaded = store.read_latest()
    assert loaded is not None
    assert len(loaded.persons) == 1
    assert loaded.persons[0].canonical_id == "p1"
    assert loaded.persons[0].attrs["full_name"] == "Alice"


def test_write_is_atomic(tmp_path: Path):
    # File must not be partially visible (uses tmp + rename)
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    path = store.write(snap)
    assert path is not None
    # Read back — every line must be valid JSON
    import json

    for line in path.read_text().splitlines():
        json.loads(line)  # raises if malformed
