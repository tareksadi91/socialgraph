"""Cross-platform identity candidate detection.

Compares LinkedIn contacts against X contacts by normalized name.
Produces CandidatePair objects for the PendingMergeQueue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from socialgraph.identity.fuzzy import name_similarity
from socialgraph.schema.raw_contact import RawContact

_EXACT_THRESHOLD = 0.99
_FUZZY_THRESHOLD = 0.88


@dataclass
class CandidatePair:
    """A candidate cross-platform identity match awaiting user confirmation."""

    linkedin_raw_id: str
    x_raw_id: str
    linkedin_canonical_id: str
    x_canonical_id: str
    signals: list[str]
    linkedin_attrs: dict[str, Any] = field(default_factory=dict)
    x_attrs: dict[str, Any] = field(default_factory=dict)


def cross_platform_candidates(
    resolved: list[tuple[str, RawContact]],
    already_paired: set[tuple[str, str]],
) -> list[CandidatePair]:
    """Find cross-platform candidate pairs by name similarity.

    resolved: output of within_platform_resolve() — (canonical_id, RawContact) pairs.
    already_paired: set of (linkedin_raw_id, x_raw_id) tuples already in the queue.
    """
    linkedin = [(cid, c) for cid, c in resolved if c.platform == "linkedin"]
    x_contacts = [(cid, c) for cid, c in resolved if c.platform == "x"]

    if not linkedin or not x_contacts:
        return []

    candidates: list[CandidatePair] = []
    for li_cid, li_contact in linkedin:
        for x_cid, x_contact in x_contacts:
            pair_key = (li_contact.raw_id, x_contact.raw_id)
            if pair_key in already_paired:
                continue
            score = name_similarity(li_contact.full_name, x_contact.full_name)
            if score >= _EXACT_THRESHOLD:
                signals = ["name_exact"]
            elif score >= _FUZZY_THRESHOLD:
                signals = [f"fuzzy_name={score:.2f}"]
            else:
                continue
            candidates.append(
                CandidatePair(
                    linkedin_raw_id=li_contact.raw_id,
                    x_raw_id=x_contact.raw_id,
                    linkedin_canonical_id=li_cid,
                    x_canonical_id=x_cid,
                    signals=signals,
                    linkedin_attrs={
                        "full_name": li_contact.full_name,
                        "current_company": li_contact.current_company,
                        "current_title": li_contact.current_title,
                    },
                    x_attrs={"full_name": x_contact.full_name, "handle": x_contact.handle},
                )
            )
    return candidates
