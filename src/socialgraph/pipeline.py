"""Full ingest pipeline: resolve identity + build + write snapshot.

Called by import_cmd after writing JSONL. Reads ALL parsed JSONL for
the platform (not just the current run) to build a complete picture.
"""

from __future__ import annotations

import json

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.identity.resolve import within_platform_resolve
from socialgraph.paths import DataPaths
from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.build import build_snapshot
from socialgraph.snapshot.store import SnapshotStore


def _load_all_contacts(paths: DataPaths) -> list[RawContact]:
    """Load all RawContact records from all parsed JSONL files."""
    contacts: list[RawContact] = []
    if not paths.parsed.is_dir():
        return contacts
    for jsonl_file in sorted(paths.parsed.glob("*.jsonl")):
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                contacts.append(RawContact.model_validate(json.loads(line)))
            except Exception:
                continue
    return contacts


def run_pipeline(paths: DataPaths) -> dict[str, int]:
    """Resolve identity, build snapshot, write if changed.

    Returns counts: {persons, companies, edges, snapshot_written}.
    """
    contacts = _load_all_contacts(paths)
    if not contacts:
        return {"persons": 0, "companies": 0, "edges": 0, "snapshot_written": 0}

    log = CanonicalLog(paths.merge_decisions)
    resolved = within_platform_resolve(contacts, log)

    snapshot = build_snapshot(resolved)
    store = SnapshotStore(paths.snapshots)
    written_path = store.write(snapshot)

    return {
        "persons": len(snapshot.persons),
        "companies": len(snapshot.companies),
        "edges": len(snapshot.edges),
        "snapshot_written": 1 if written_path else 0,
    }
