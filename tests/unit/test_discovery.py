from socialgraph.port.discovery import DiscoveryResult, run_tiers
from socialgraph.port.state import PortCandidate


def _candidate(handle: str, score: float = 0.9, source: str = "test") -> PortCandidate:
    return PortCandidate(
        handle=handle, display_name=handle, bio_preview="", score=score, rationale="", source=source
    )


class AlwaysHitTier:
    """Fake tier that always returns a resolved handle."""

    confidence = 1.0

    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(
            handle=f"@{name.lower().replace(' ', '_')}",
            confidence=1.0,
            source="always_hit",
            candidates=[],
        )


class AlwaysMissTier:
    confidence = 0.0

    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(handle=None, confidence=0.0, source="always_miss", candidates=[])


class CandidateTier:
    """Returns candidates but no definitive handle."""

    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(
            handle=None,
            confidence=0.7,
            source="candidate_tier",
            candidates=[_candidate("maybe_handle", score=0.7, source="candidate_tier")],
        )


def test_run_tiers_stops_at_first_auto_resolve():
    hit = AlwaysHitTier()
    miss = AlwaysMissTier()
    result = run_tiers(
        "Alice Example",
        "Acme",
        "https://linkedin.com/in/alice",
        tiers=[hit, miss],
        auto_resolve_threshold=1.0,
    )
    assert result.handle is not None
    assert result.source == "always_hit"


def test_run_tiers_falls_through_miss():
    miss = AlwaysMissTier()
    hit = AlwaysHitTier()
    result = run_tiers(
        "Alice",
        None,
        "https://linkedin.com/in/alice",
        tiers=[miss, hit],
        auto_resolve_threshold=1.0,
    )
    assert result.handle is not None
    assert result.source == "always_hit"


def test_run_tiers_returns_candidates_when_no_auto_resolve():
    miss = AlwaysMissTier()
    candidates_tier = CandidateTier()
    result = run_tiers(
        "Alice",
        None,
        "https://linkedin.com/in/alice",
        tiers=[miss, candidates_tier],
        auto_resolve_threshold=1.0,
    )
    assert result.handle is None
    assert len(result.candidates) == 1
    assert result.candidates[0].source == "candidate_tier"


def test_run_tiers_returns_empty_when_all_miss():
    result = run_tiers(
        "Alice",
        None,
        "https://linkedin.com/in/alice",
        tiers=[AlwaysMissTier()],
        auto_resolve_threshold=1.0,
    )
    assert result.handle is None
    assert result.candidates == []


def test_port_candidate_has_source_field():
    c = PortCandidate(handle="x", display_name="X", bio_preview="", score=0.9, rationale="")
    assert c.source == ""  # default
    c2 = PortCandidate(
        handle="x", display_name="X", bio_preview="", score=0.9, rationale="", source="google_cse"
    )
    assert c2.source == "google_cse"
