"""Per-field merge rules for combining multiple RawContact observations.

When a Person is observed more than once (e.g., import + scrape), fields are
merged by priority (spec §4.2):

    scrape > import   for company, title, location, headline, bio
    latest non-null   as the tiebreaker
    union             for list fields (topics)

Only fields present in the first milestone import are implemented here.
Scrape-only fields (headline, bio, location_*, photo_url) are carried through
verbatim from whichever observation has them.
"""

from __future__ import annotations

from typing import Any

from socialgraph.schema.raw_contact import RawContact

# Higher = higher priority. "scrape" > "import" per spec.
_SOURCE_PRIORITY = {"import": 0, "scrape": 1}


def merge_person_attrs(contacts: list[RawContact]) -> dict[str, Any]:
    """Merge multiple observations of the same person into one attrs dict.

    Returns a plain dict suitable for SnapshotPerson.attrs.
    """
    # Sort by (source_priority asc, observed_at asc) so highest-priority
    # and most-recent value wins when we overwrite.
    sorted_contacts = sorted(
        contacts,
        key=lambda c: (_SOURCE_PRIORITY.get(c.source, 0), c.observed_at),
    )

    attrs: dict[str, Any] = {}

    scalar_fields = [
        "full_name",
        "first_name",
        "last_name",
        "display_name",
        "handle",
        "email",
        "headline",
        "bio",
        "location_raw",
        "location_city",
        "location_country",
        "photo_url",
        "language",
        "current_company",
        "current_company_url",
        "current_title",
        "industry",
        "seniority",
        "function",
        "follower_count",
        "following_count",
        "mutual_count",
    ]
    list_fields = ["topics", "mutual_names_sample"]

    for contact in sorted_contacts:
        for field in scalar_fields:
            val = getattr(contact, field, None)
            if val is not None:
                attrs[field] = val
        for field in list_fields:
            val = getattr(contact, field, None) or []
            existing = attrs.get(field, [])
            attrs[field] = list(dict.fromkeys(existing + val))  # union, order-preserving

    # connected_on = earliest observed (first time you connected)
    dates = [c.connected_on for c in contacts if c.connected_on]
    if dates:
        attrs["connected_on"] = min(dates).isoformat()

    # platform_urls: aggregated per-platform profile URLs
    urls: dict[str, str] = attrs.get("platform_urls", {})
    for c in contacts:
        if c.profile_url:
            urls[c.platform] = c.profile_url
    attrs["platform_urls"] = urls

    return attrs


def extract_company_name(contacts: list[RawContact]) -> str | None:
    """Return the most recent non-null current_company across contacts."""
    sorted_contacts = sorted(
        contacts,
        key=lambda c: (_SOURCE_PRIORITY.get(c.source, 0), c.observed_at),
        reverse=True,
    )
    for c in sorted_contacts:
        if c.current_company and c.current_company.strip():
            return c.current_company.strip()
    return None
