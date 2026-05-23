from datetime import UTC, datetime

from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.build import build_snapshot


def _contact(slug: str, company: str | None = None, title: str | None = None) -> RawContact:
    return RawContact(
        raw_id=f"r#{slug}",
        platform="linkedin",
        source="import",
        platform_native_id=slug,
        profile_url=f"https://linkedin.com/in/{slug}",
        observed_at=datetime(2026, 5, 23, tzinfo=UTC),
        run_id="run1",
        full_name=slug.title(),
        current_company=company,
        current_title=title,
    )


def test_build_creates_person_nodes():
    contacts = [
        ("cid-1", _contact("alice", company="Acme")),
        ("cid-2", _contact("bob", company="Beta")),
    ]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 2
    assert {p.canonical_id for p in snap.persons} == {"cid-1", "cid-2"}


def test_build_creates_company_nodes():
    contacts = [
        ("cid-1", _contact("alice", company="Acme")),
        ("cid-2", _contact("bob", company="Acme")),  # same company
        ("cid-3", _contact("carol", company="Beta")),
    ]
    snap = build_snapshot(contacts)
    company_names = {c.name for c in snap.companies}
    assert company_names == {"Acme", "Beta"}


def test_build_deduplicates_companies():
    contacts = [
        ("cid-1", _contact("alice", company="Acme")),
        ("cid-2", _contact("bob", company="Acme")),
    ]
    snap = build_snapshot(contacts)
    assert len(snap.companies) == 1


def test_build_creates_works_at_edges():
    contacts = [("cid-1", _contact("alice", company="Acme", title="Founder"))]
    snap = build_snapshot(contacts)
    works_at = [e for e in snap.edges if e.edge_type == "WORKS_AT"]
    assert len(works_at) == 1
    assert works_at[0].src == "cid-1"
    assert works_at[0].attrs.get("title") == "Founder"


def test_build_skips_persons_without_company():
    contacts = [("cid-1", _contact("alice", company=None))]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 1
    assert len(snap.companies) == 0
    assert len(snap.edges) == 0


def test_build_groups_multiple_observations():
    # same canonical_id, two observations → one merged person
    c1 = _contact("alice", company="OldCo")
    c2 = RawContact(
        raw_id="r2#alice",
        platform="linkedin",
        source="scrape",
        platform_native_id="alice",
        profile_url="https://linkedin.com/in/alice",
        observed_at=datetime(2026, 5, 24, tzinfo=UTC),
        run_id="run2",
        full_name="Alice",
        current_company="NewCo",
    )
    contacts = [("cid-1", c1), ("cid-1", c2)]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 1  # merged, not duplicated
    person = snap.persons[0]
    assert person.attrs["current_company"] == "NewCo"  # scrape > import
