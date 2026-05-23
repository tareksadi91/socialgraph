"""Diff two snapshots to detect added/removed/changed nodes and edges."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from socialgraph.snapshot.models import Snapshot


@dataclass
class SnapshotDiff:
    added_persons: set[str] = field(default_factory=set)  # canonical_ids
    removed_persons: set[str] = field(default_factory=set)
    changed_persons: dict[str, dict[str, tuple[Any, Any]]] = field(default_factory=dict)
    added_companies: set[str] = field(default_factory=set)
    removed_companies: set[str] = field(default_factory=set)
    added_edges: list[tuple[str, str, str]] = field(default_factory=list)  # (type, src, dst)
    removed_edges: list[tuple[str, str, str]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return (
            not self.added_persons
            and not self.removed_persons
            and not self.changed_persons
            and not self.added_companies
            and not self.removed_companies
            and not self.added_edges
            and not self.removed_edges
        )


def snapshot_diff(a: Snapshot, b: Snapshot) -> SnapshotDiff:
    """Compute the diff between snapshot a (before) and snapshot b (after)."""
    d = SnapshotDiff()

    a_persons = {p.canonical_id: p for p in a.persons}
    b_persons = {p.canonical_id: p for p in b.persons}
    d.added_persons = set(b_persons) - set(a_persons)
    d.removed_persons = set(a_persons) - set(b_persons)
    for cid in set(a_persons) & set(b_persons):
        changes: dict[str, tuple[Any, Any]] = {}
        a_attrs = a_persons[cid].attrs
        b_attrs = b_persons[cid].attrs
        all_keys = set(a_attrs) | set(b_attrs)
        for key in all_keys:
            av, bv = a_attrs.get(key), b_attrs.get(key)
            if av != bv:
                changes[key] = (av, bv)
        if changes:
            d.changed_persons[cid] = changes

    a_companies = {c.canonical_id for c in a.companies}
    b_companies = {c.canonical_id for c in b.companies}
    d.added_companies = b_companies - a_companies
    d.removed_companies = a_companies - b_companies

    a_edges = {(e.edge_type, e.src, e.dst) for e in a.edges}
    b_edges = {(e.edge_type, e.src, e.dst) for e in b.edges}
    d.added_edges = list(b_edges - a_edges)
    d.removed_edges = list(a_edges - b_edges)

    return d
