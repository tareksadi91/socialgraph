"""Canonical ID assignment and merge_decisions.jsonl log.

Every RawContact gets a stable UUID canonical_id on first observation.
All assignments are written as append-only events to merge_decisions.jsonl
so canonical_ids are reproducible via log replay (sovereignty guarantee).
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path


class CanonicalLog:
    """Wraps merge_decisions.jsonl: assigns canonical_ids and replays history.

    The log is append-only. On construction, existing entries are replayed
    into an in-memory cache so every get_or_create() call is O(1) after init.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._cache: dict[str, str] = {}  # raw_id → canonical_id
        self._replay()

    def _replay(self) -> None:
        if not self.path.is_file():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event = entry.get("event")
                if event == "create":
                    self._cache[entry["raw_id"]] = entry["canonical_id"]
                elif event == "merge":
                    for rid in entry.get("raw_ids", []):
                        self._cache[rid] = entry["canonical_id"]
                elif event == "unmerge":
                    for rid, cid in entry.get("reassignments", {}).items():
                        self._cache[rid] = cid

    def get_or_create(self, raw_id: str) -> str:
        """Return existing canonical_id or assign a new UUID and persist it."""
        if raw_id in self._cache:
            return self._cache[raw_id]
        cid = str(uuid.uuid4())
        self._cache[raw_id] = cid
        self._append({"event": "create", "canonical_id": cid, "raw_id": raw_id})
        return cid

    def get_all(self) -> dict[str, str]:
        """Return snapshot of current raw_id → canonical_id mapping."""
        return dict(self._cache)

    def merge(self, raw_ids: list[str], target_canonical_id: str) -> None:
        """Merge raw_ids under a single canonical_id (write merge event)."""
        for rid in raw_ids:
            self._cache[rid] = target_canonical_id
        self._append({"event": "merge", "canonical_id": target_canonical_id, "raw_ids": raw_ids})

    def unmerge(self, reassignments: dict[str, str]) -> None:
        """Reassign raw_ids to new canonical_ids (write unmerge event)."""
        for rid, new_cid in reassignments.items():
            self._cache[rid] = new_cid
        self._append({"event": "unmerge", "reassignments": reassignments})

    def raw_ids_for(self, canonical_id: str) -> list[str]:
        """Return all raw_ids currently mapped to a canonical_id."""
        return [rid for rid, cid in self._cache.items() if cid == canonical_id]

    def _append(self, record: dict) -> None:
        record["ts"] = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
