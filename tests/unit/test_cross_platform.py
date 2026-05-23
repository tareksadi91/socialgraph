from datetime import UTC, datetime

from socialgraph.identity.cross_platform import cross_platform_candidates
from socialgraph.schema.raw_contact import RawContact


def _li(slug: str, name: str, **kw) -> tuple[str, RawContact]:
    return (
        f"cid-li-{slug}",
        RawContact(
            raw_id=f"linkedin#{slug}",
            platform="linkedin",
            source="import",
            platform_native_id=slug,
            profile_url=f"https://linkedin.com/in/{slug}",
            observed_at=datetime(2026, 5, 23, tzinfo=UTC),
            run_id="r1",
            full_name=name,
            **kw,
        ),
    )


def _x(handle: str) -> tuple[str, RawContact]:
    return (
        f"cid-x-{handle}",
        RawContact(
            raw_id=f"x#{handle}",
            platform="x",
            source="import",
            platform_native_id=handle,
            profile_url=f"https://x.com/{handle}",
            observed_at=datetime(2026, 5, 23, tzinfo=UTC),
            run_id="r2",
            full_name=handle,
        ),
    )


def test_finds_exact_normalized_match():
    resolved = [
        _li("alice-example", "Alice Example"),
        _x("alice_example"),
        _x("bob_x"),
    ]
    pairs = cross_platform_candidates(resolved, already_paired=set())
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.linkedin_raw_id == "linkedin#alice-example"
    assert pair.x_raw_id == "x#alice_example"
    assert "name_exact" in " ".join(pair.signals)


def test_no_match_when_names_differ():
    resolved = [
        _li("carol-test", "Carol Test"),
        _x("zoran_xyz"),
    ]
    pairs = cross_platform_candidates(resolved, already_paired=set())
    assert len(pairs) == 0


def test_skips_already_paired():
    resolved = [
        _li("alice-example", "Alice Example"),
        _x("alice_example"),
    ]
    already = {("linkedin#alice-example", "x#alice_example")}
    pairs = cross_platform_candidates(resolved, already_paired=already)
    assert len(pairs) == 0


def test_skips_same_platform_comparison():
    resolved = [
        _li("alice", "Alice"),
        _li("alice2", "Alice"),
        _x("alice_x"),
    ]
    pairs = cross_platform_candidates(resolved, already_paired=set())
    for pair in pairs:
        assert pair.linkedin_raw_id.startswith("linkedin#")
        assert pair.x_raw_id.startswith("x#")
