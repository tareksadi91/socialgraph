from datetime import UTC, datetime

from socialgraph.identity.merge_fields import extract_company_name, merge_person_attrs
from socialgraph.schema.raw_contact import RawContact


def _contact(**kw) -> RawContact:
    base = {
        "raw_id": "r#slug",
        "platform": "linkedin",
        "source": "import",
        "platform_native_id": "slug",
        "profile_url": "https://linkedin.com/in/slug",
        "observed_at": datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC),
        "run_id": "run1",
        "full_name": "Test Person",
    }
    base.update(kw)
    return RawContact(**base)


def test_merge_single_contact():
    c = _contact(
        full_name="Alice Smith",
        first_name="Alice",
        last_name="Smith",
        current_company="Acme",
        current_title="Founder",
    )
    attrs = merge_person_attrs([c])
    assert attrs["full_name"] == "Alice Smith"
    assert attrs["current_company"] == "Acme"
    assert attrs["current_title"] == "Founder"
    assert attrs["platform_urls"] == {"linkedin": "https://linkedin.com/in/slug"}


def test_merge_prefers_scrape_over_import():
    import_ = _contact(full_name="A B", current_company="Old Co", source="import")
    scrape = _contact(full_name="A B", current_company="New Co", source="scrape")
    attrs = merge_person_attrs([import_, scrape])
    # scrape > import for company (spec §4.2 field priority)
    assert attrs["current_company"] == "New Co"


def test_merge_latest_non_null_wins_for_title():
    c1 = _contact(current_title=None, observed_at=datetime(2026, 1, 1, tzinfo=UTC))
    c2 = _contact(current_title="CEO", observed_at=datetime(2026, 5, 1, tzinfo=UTC))
    attrs = merge_person_attrs([c1, c2])
    assert attrs["current_title"] == "CEO"


def test_extract_company_name_returns_none_when_missing():
    c = _contact(current_company=None)
    assert extract_company_name([c]) is None


def test_extract_company_name_strips_whitespace():
    c = _contact(current_company="  Acme Corp  ")
    assert extract_company_name([c]) == "Acme Corp"
