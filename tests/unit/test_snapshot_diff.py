from socialgraph.snapshot.diff import SnapshotDiff, snapshot_diff
from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def _person(cid: str, name: str = "Test", company: str = "Co") -> SnapshotPerson:
    return SnapshotPerson(
        canonical_id=cid, attrs={"full_name": name, "current_company": company}, observations=[]
    )


def _company(cid: str, name: str = "Co") -> SnapshotCompany:
    return SnapshotCompany(canonical_id=cid, name=name)


def _edge(src: str, dst: str, etype: str = "WORKS_AT") -> SnapshotEdge:
    return SnapshotEdge(edge_type=etype, src=src, dst=dst, attrs={})


def test_diff_empty_vs_empty():
    d = snapshot_diff(Snapshot([], [], []), Snapshot([], [], []))
    assert isinstance(d, SnapshotDiff)
    assert d.is_empty()


def test_diff_detects_added_person():
    a = Snapshot([], [], [])
    b = Snapshot([_person("p1", "Alice")], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.added_persons
    assert d.removed_persons == set()


def test_diff_detects_removed_person():
    a = Snapshot([_person("p1")], [], [])
    b = Snapshot([], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.removed_persons
    assert d.added_persons == set()


def test_diff_detects_changed_attr():
    a = Snapshot([_person("p1", company="Old Co")], [], [])
    b = Snapshot([_person("p1", company="New Co")], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.changed_persons
    change = d.changed_persons["p1"]
    assert change["current_company"] == ("Old Co", "New Co")


def test_diff_no_change_same_snapshot():
    snap = Snapshot([_person("p1")], [_company("co1")], [_edge("p1", "co1")])
    d = snapshot_diff(snap, snap)
    assert d.is_empty()
