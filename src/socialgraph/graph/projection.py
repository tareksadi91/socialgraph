"""NetworkX graph projection from a Snapshot.

Builds an in-memory MultiDiGraph with Person and Company nodes and
WORKS_AT edges. All node/edge attributes from the snapshot are preserved
as node/edge data for query and analytics use.
"""

from __future__ import annotations

import networkx as nx

from socialgraph.snapshot.models import Snapshot


def build_graph(snapshot: Snapshot) -> nx.MultiDiGraph:
    """Return a MultiDiGraph from snapshot nodes and edges."""
    G: nx.MultiDiGraph = nx.MultiDiGraph()

    for person in snapshot.persons:
        G.add_node(
            person.canonical_id,
            node_type="Person",
            **person.attrs,
        )

    for company in snapshot.companies:
        G.add_node(
            company.canonical_id,
            node_type="Company",
            name=company.name,
            **company.attrs,
        )

    for edge in snapshot.edges:
        G.add_edge(
            edge.src,
            edge.dst,
            edge_type=edge.edge_type,
            **edge.attrs,
        )

    return G
