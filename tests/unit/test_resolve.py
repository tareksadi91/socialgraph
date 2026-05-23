from datetime import UTC, datetime
from pathlib import Path

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.identity.resolve import within_platform_resolve
from socialgraph.schema.raw_contact import RawContact


def _contact(slug: str, platform: str = "linkedin", **kw) -> RawContact:
    return RawContact(
        raw_id=f"run1#{slug}",
        platform=platform,
        source="import",
        platform_native_id=slug,
        profile_url=f"https://linkedin.com/in/{slug}",
        observed_at=datetime(2026, 5, 23, tzinfo=UTC),
        run_id="run1",
        full_name=slug.replace("-", " ").title(),
        **kw,
    )


def test_resolve_assigns_canonical_ids(tmp_path: Path):
    contacts = [_contact("alice"), _contact("bob"), _contact("carol")]
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve(contacts, log)
    assert len(result) == 3
    canonical_ids = {cid for cid, _ in result}
    assert len(canonical_ids) == 3  # one per unique slug


def test_resolve_same_slug_same_canonical_id(tmp_path: Path):
    # Two observations of the same person
    c1 = _contact("alice")
    c2 = RawContact(
        raw_id="run2#alice",
        platform="linkedin",
        source="scrape",
        platform_native_id="alice",
        profile_url="https://linkedin.com/in/alice",
        observed_at=datetime(2026, 5, 24, tzinfo=UTC),
        run_id="run2",
        full_name="Alice",
    )
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve([c1, c2], log)
    cids = [cid for cid, _ in result]
    assert cids[0] == cids[1]  # same person, same canonical_id


def test_resolve_stable_across_calls(tmp_path: Path):
    p = tmp_path / "merge_decisions.jsonl"
    contacts = [_contact("alice"), _contact("bob")]
    log1 = CanonicalLog(p)
    result1 = within_platform_resolve(contacts, log1)
    log2 = CanonicalLog(p)
    result2 = within_platform_resolve(contacts, log2)
    assert [cid for cid, _ in result1] == [cid for cid, _ in result2]


def test_resolve_returns_one_entry_per_contact(tmp_path: Path):
    contacts = [_contact("alice"), _contact("alice"), _contact("bob")]
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve(contacts, log)
    # returns one entry per input contact (not one per unique person)
    assert len(result) == 3
