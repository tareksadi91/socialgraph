"""Graph query functions over the NetworkX MultiDiGraph.

All functions accept the graph G produced by build_graph() and return
plain dicts — ready for JSON serialisation or CLI display.
"""

from __future__ import annotations

import networkx as nx


def at_company(G: nx.MultiDiGraph, company_name: str) -> list[dict]:
    """Return all Persons with a WORKS_AT edge to the named company.

    Match is case-insensitive on the Company node's 'name' attribute.
    """
    company_name_lower = company_name.lower()

    # Find matching company node(s)
    company_ids = {
        n
        for n, d in G.nodes(data=True)
        if d.get("node_type") == "Company" and d.get("name", "").lower() == company_name_lower
    }

    results: list[dict] = []
    for company_id in company_ids:
        # Find persons with WORKS_AT edge into this company
        for src, _dst, data in G.in_edges(company_id, data=True):
            if data.get("edge_type") == "WORKS_AT":
                node_data = dict(G.nodes[src])
                node_data["canonical_id"] = src
                results.append(node_data)

    return results


def neighbors_via_company(G: nx.MultiDiGraph, canonical_id: str, depth: int = 1) -> list[dict]:
    """Return Persons who share a company with the given Person.

    In M2, inter-person edges don't exist (no scrape data for mutual connections).
    The meaningful 1st-degree neighbors are colleagues at the same company,
    reachable via WORKS_AT edges through Company nodes.

    depth > 1 follows WORKS_AT chains: Person → Company → Person → Company → ...
    """
    if canonical_id not in G:
        return []

    visited_persons: set[str] = {canonical_id}
    result: list[dict] = []

    # Collect companies this person works at
    companies: set[str] = {
        dst
        for src, dst, data in G.out_edges(canonical_id, data=True)
        if data.get("edge_type") == "WORKS_AT"
    }

    for _ in range(depth):
        new_companies: set[str] = set()
        for co_id in companies:
            # All persons who also WORKS_AT this company
            for src, _dst, data in G.in_edges(co_id, data=True):
                if data.get("edge_type") == "WORKS_AT" and src not in visited_persons:
                    visited_persons.add(src)
                    node_data = dict(G.nodes[src])
                    node_data["canonical_id"] = src
                    result.append(node_data)
                    # For depth > 1: also traverse their companies
                    for _, co2, d2 in G.out_edges(src, data=True):
                        if d2.get("edge_type") == "WORKS_AT":
                            new_companies.add(co2)
        companies = new_companies

    return result
