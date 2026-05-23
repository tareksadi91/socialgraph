import json

from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def test_snapshot_person_round_trip():
    p = SnapshotPerson(
        canonical_id="uuid-1",
        attrs={"full_name": "Alice", "current_company": "Acme"},
        observations=["run1#alice"],
    )
    line = p.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "node"
    assert parsed["node_type"] == "Person"
    p2 = SnapshotPerson.from_jsonl_dict(parsed)
    assert p2.canonical_id == "uuid-1"
    assert p2.attrs["full_name"] == "Alice"


def test_snapshot_company_round_trip():
    c = SnapshotCompany(canonical_id="co-1", name="Acme Corp")
    line = c.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "node"
    assert parsed["node_type"] == "Company"
    c2 = SnapshotCompany.from_jsonl_dict(parsed)
    assert c2.name == "Acme Corp"


def test_snapshot_edge_round_trip():
    e = SnapshotEdge(
        edge_type="WORKS_AT",
        src="uuid-1",
        dst="co-1",
        attrs={"title": "Founder"},
    )
    line = e.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "edge"
    assert parsed["edge_type"] == "WORKS_AT"
    e2 = SnapshotEdge.from_jsonl_dict(parsed)
    assert e2.src == "uuid-1"
    assert e2.dst == "co-1"


def test_snapshot_is_empty():
    s = Snapshot(persons=[], companies=[], edges=[])
    assert s.is_empty()
    s2 = Snapshot(
        persons=[SnapshotPerson(canonical_id="x", attrs={}, observations=[])],
        companies=[],
        edges=[],
    )
    assert not s2.is_empty()
