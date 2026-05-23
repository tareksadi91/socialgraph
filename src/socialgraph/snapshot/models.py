"""Snapshot data model — immutable JSONL records for Persons, Companies, Edges.

Each line in a snapshot file has a discriminator:
  {"type": "node", "node_type": "Person", "canonical_id": ..., "attrs": {...},
   "observations": [...]}
  {"type": "node", "node_type": "Company", "canonical_id": ..., "name": ...,
   "attrs": {...}}
  {"type": "edge", "edge_type": "WORKS_AT", "src": ..., "dst": ..., "attrs": {...}}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SnapshotPerson:
    canonical_id: str
    attrs: dict[str, Any]
    observations: list[str]  # raw_ids that contributed

    def to_jsonl_line(self) -> str:
        return json.dumps(
            {
                "type": "node",
                "node_type": "Person",
                "canonical_id": self.canonical_id,
                "attrs": self.attrs,
                "observations": self.observations,
            }
        )

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> SnapshotPerson:
        return cls(
            canonical_id=d["canonical_id"],
            attrs=d.get("attrs", {}),
            observations=d.get("observations", []),
        )


@dataclass
class SnapshotCompany:
    canonical_id: str
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_jsonl_line(self) -> str:
        return json.dumps(
            {
                "type": "node",
                "node_type": "Company",
                "canonical_id": self.canonical_id,
                "name": self.name,
                "attrs": self.attrs,
            }
        )

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> SnapshotCompany:
        return cls(
            canonical_id=d["canonical_id"],
            name=d.get("name", ""),
            attrs=d.get("attrs", {}),
        )


@dataclass
class SnapshotEdge:
    edge_type: str
    src: str
    dst: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_jsonl_line(self) -> str:
        return json.dumps(
            {
                "type": "edge",
                "edge_type": self.edge_type,
                "src": self.src,
                "dst": self.dst,
                "attrs": self.attrs,
            }
        )

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> SnapshotEdge:
        return cls(
            edge_type=d["edge_type"],
            src=d["src"],
            dst=d["dst"],
            attrs=d.get("attrs", {}),
        )


@dataclass
class Snapshot:
    persons: list[SnapshotPerson]
    companies: list[SnapshotCompany]
    edges: list[SnapshotEdge]

    def is_empty(self) -> bool:
        return not self.persons and not self.companies and not self.edges

    def to_jsonl_lines(self) -> list[str]:
        lines: list[str] = []
        lines.extend(p.to_jsonl_line() for p in self.persons)
        lines.extend(c.to_jsonl_line() for c in self.companies)
        lines.extend(e.to_jsonl_line() for e in self.edges)
        return lines

    @classmethod
    def from_jsonl_lines(cls, lines: list[str]) -> Snapshot:
        persons, companies, edges = [], [], []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") == "node":
                if d.get("node_type") == "Person":
                    persons.append(SnapshotPerson.from_jsonl_dict(d))
                elif d.get("node_type") == "Company":
                    companies.append(SnapshotCompany.from_jsonl_dict(d))
            elif d.get("type") == "edge":
                edges.append(SnapshotEdge.from_jsonl_dict(d))
        return cls(persons=persons, companies=companies, edges=edges)
