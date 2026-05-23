"""Within-platform identity resolution.

Groups RawContact records by platform_native_id and assigns stable
canonical_ids via CanonicalLog. Same platform_native_id = same person.
Cross-platform merge is handled in M3 (conservative + review queue).
"""

from __future__ import annotations

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.schema.raw_contact import RawContact


def within_platform_resolve(
    contacts: list[RawContact],
    log: CanonicalLog,
) -> list[tuple[str, RawContact]]:
    """Assign canonical_ids to a flat list of RawContacts.

    Returns one (canonical_id, contact) tuple per input contact, in the
    same order. Contacts sharing a platform_native_id get the same
    canonical_id (they are the same person observed multiple times).
    """
    result: list[tuple[str, RawContact]] = []
    for contact in contacts:
        # raw_id key: {platform}#{platform_native_id} — unique across platforms
        raw_key = f"{contact.platform}#{contact.platform_native_id}"
        cid = log.get_or_create(raw_key)
        result.append((cid, contact))
    return result
