from socialgraph.graph.projection import build_graph
from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def _snap() -> Snapshot:
    alice = SnapshotPerson(
        canonical_id="p-alice",
        attrs={"full_name": "Alice", "current_company": "Acme"},
        observations=[],
    )
    bob = SnapshotPerson(
        canonical_id="p-bob",
        attrs={"full_name": "Bob", "current_company": "Acme"},
        observations=[],
    )
    acme = SnapshotCompany(canonical_id="company-acme", name="Acme Corp")
    e1 = SnapshotEdge(
        edge_type="WORKS_AT", src="p-alice", dst="company-acme", attrs={"title": "CEO"}
    )
    e2 = SnapshotEdge(edge_type="WORKS_AT", src="p-bob", dst="company-acme", attrs={"title": "Eng"})
    return Snapshot(persons=[alice, bob], companies=[acme], edges=[e1, e2])


def test_build_graph_has_person_nodes():
    G = build_graph(_snap())
    assert "p-alice" in G
    assert G.nodes["p-alice"]["node_type"] == "Person"
    assert G.nodes["p-alice"]["full_name"] == "Alice"


def test_build_graph_has_company_nodes():
    G = build_graph(_snap())
    assert "company-acme" in G
    assert G.nodes["company-acme"]["node_type"] == "Company"
    assert G.nodes["company-acme"]["name"] == "Acme Corp"


def test_build_graph_has_works_at_edges():
    G = build_graph(_snap())
    edges = list(G.edges("p-alice", data=True))
    assert any(d.get("edge_type") == "WORKS_AT" and v == "company-acme" for u, v, d in edges)


def test_build_graph_empty_snapshot():
    G = build_graph(Snapshot([], [], []))
    assert len(G.nodes) == 0
    assert len(G.edges) == 0
