"""Build a Snapshot from a resolved (canonical_id, RawContact) list.

Groups contacts by canonical_id, merges attributes via field-priority rules,
derives Company nodes from current_company, and creates WORKS_AT edges.
"""

from __future__ import annotations

import re
from collections import defaultdict

from socialgraph.identity.merge_fields import extract_company_name, merge_person_attrs
from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def _company_slug(name: str) -> str:
    """Derive a stable canonical_id for a company from its name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    return f"company-{slug}"


def build_snapshot(resolved: list[tuple[str, RawContact]]) -> Snapshot:
    """Build a Snapshot from resolved (canonical_id, RawContact) pairs.

    resolved: output of within_platform_resolve() — one pair per raw observation.
    """
    # Group observations by canonical_id
    by_cid: dict[str, list[RawContact]] = defaultdict(list)
    for cid, contact in resolved:
        by_cid[cid].append(contact)

    persons: list[SnapshotPerson] = []
    companies: dict[str, SnapshotCompany] = {}  # slug → SnapshotCompany
    edges: list[SnapshotEdge] = []

    for cid, contacts in by_cid.items():
        attrs = merge_person_attrs(contacts)
        observations = [c.raw_id for c in contacts]
        persons.append(SnapshotPerson(canonical_id=cid, attrs=attrs, observations=observations))

        company_name = extract_company_name(contacts)
        if company_name:
            slug = _company_slug(company_name)
            if slug not in companies:
                companies[slug] = SnapshotCompany(canonical_id=slug, name=company_name)
            edge_attrs: dict[str, object] = {}
            title = attrs.get("current_title")
            if title:
                edge_attrs["title"] = title
            edges.append(
                SnapshotEdge(
                    edge_type="WORKS_AT",
                    src=cid,
                    dst=slug,
                    attrs=edge_attrs,
                )
            )

    return Snapshot(
        persons=persons,
        companies=list(companies.values()),
        edges=edges,
    )
