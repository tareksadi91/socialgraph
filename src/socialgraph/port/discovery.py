"""Multi-tier handle discovery orchestration.

Each Tier is a data source tried in order. The first tier that returns a
handle with confidence >= auto_resolve_threshold resolves immediately (no
user review). Tiers returning candidates below threshold accumulate results
for the review queue. All tiers exhausted → DiscoveryResult with no handle
and all collected candidates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from socialgraph.port.state import PortCandidate


@dataclass
class DiscoveryResult:
    """Output of a single tier or the full tier cascade."""

    handle: str | None
    confidence: float
    source: str
    candidates: list[PortCandidate] = field(default_factory=list)


@runtime_checkable
class Tier(Protocol):
    """A single data source for handle discovery."""

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult: ...


def run_tiers(
    name: str,
    company: str | None,
    profile_url: str,
    tiers: list[Tier],
    auto_resolve_threshold: float = 1.0,
) -> DiscoveryResult:
    """Run tiers in order; stop and auto-resolve at first high-confidence hit.

    Returns the merged DiscoveryResult: auto-resolved handle if any tier hits
    the threshold, otherwise all collected candidates from lower-confidence tiers.
    """
    all_candidates: list[PortCandidate] = []

    for tier in tiers:
        try:
            result = tier.discover(name, company, profile_url)
        except Exception:
            continue  # tier failure = skip, don't abort cascade

        if result.handle is not None and result.confidence >= auto_resolve_threshold:
            return result  # auto-resolve, stop cascade

        # Below-threshold handles are intentionally dropped: tiers that want
        # results in the review queue must put them in candidates, not handle.
        all_candidates.extend(result.candidates)

    return DiscoveryResult(
        handle=None,
        confidence=0.0,
        source="unresolved",
        candidates=all_candidates,
    )
