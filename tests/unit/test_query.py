from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import at_company, neighbors_via_company
from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def _snap() -> Snapshot:
    persons = [
        SnapshotPerson("p-alice", {"full_name": "Alice", "current_company": "Acme"}, []),
        SnapshotPerson("p-bob", {"full_name": "Bob", "current_company": "Acme"}, []),
        SnapshotPerson("p-carol", {"full_name": "Carol", "current_company": "Beta"}, []),
    ]
    companies = [
        SnapshotCompany("company-acme", "Acme Corp"),
        SnapshotCompany("company-beta", "Beta Inc"),
    ]
    edges = [
        SnapshotEdge("WORKS_AT", "p-alice", "company-acme"),
        SnapshotEdge("WORKS_AT", "p-bob", "company-acme"),
        SnapshotEdge("WORKS_AT", "p-carol", "company-beta"),
    ]
    return Snapshot(persons, companies, edges)


def test_at_company_exact_match():
    G = build_graph(_snap())
    results = at_company(G, "Acme Corp")
    names = [r["full_name"] for r in results]
    assert sorted(names) == ["Alice", "Bob"]


def test_at_company_case_insensitive():
    G = build_graph(_snap())
    results = at_company(G, "acme corp")
    assert len(results) == 2


def test_at_company_not_found():
    G = build_graph(_snap())
    results = at_company(G, "Nonexistent")
    assert results == []


def test_neighbors_via_company_finds_colleagues():
    G = build_graph(_snap())
    # Alice and Bob both work at Acme → neighbors of each other via company
    neighbors = neighbors_via_company(G, "p-alice")
    ids = [n["canonical_id"] for n in neighbors]
    assert "p-bob" in ids
    assert "p-alice" not in ids  # self excluded


def test_neighbors_via_company_no_company():
    # Person without WORKS_AT edge → no neighbors
    snap = Snapshot(
        persons=[SnapshotPerson("p-lone", {"full_name": "Lone"}, [])],
        companies=[],
        edges=[],
    )
    G = build_graph(snap)
    assert neighbors_via_company(G, "p-lone") == []


def test_neighbors_returns_attrs():
    G = build_graph(_snap())
    neighbors = neighbors_via_company(G, "p-alice")
    for n in neighbors:
        assert "canonical_id" in n
        assert "full_name" in n
