"""Pending merge queue — cross-platform identity candidates awaiting user decision.

pending_merges.jsonl stores one JSON record per candidate pair.
Records are rewritten on any status change (queue is small in practice).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from socialgraph.identity.cross_platform import CandidatePair

Status = Literal["pending", "confirmed", "rejected"]


@dataclass
class PendingMerge:
    candidate_id: str
    linkedin_raw_id: str
    x_raw_id: str
    linkedin_canonical_id: str
    x_canonical_id: str
    signals: list[str]
    linkedin_attrs: dict
    x_attrs: dict
    status: Status = "pending"
    decided_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> PendingMerge:
        return cls(**d)


class PendingMergeQueue:
    """Wraps pending_merges.jsonl: add, list, confirm, reject candidates."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._records: list[PendingMerge] = []
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        self._records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self._records.append(PendingMerge.from_dict(json.loads(line)))
            except (json.JSONDecodeError, TypeError):
                continue

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            for record in self._records:
                f.write(json.dumps(record.to_dict(), default=str) + "\n")

    def add(self, candidate: CandidatePair) -> PendingMerge | None:
        """Add a candidate pair. Returns None if pair already exists."""
        existing_keys = {(r.linkedin_raw_id, r.x_raw_id) for r in self._records}
        key = (candidate.linkedin_raw_id, candidate.x_raw_id)
        if key in existing_keys:
            return None
        merge = PendingMerge(
            candidate_id=str(uuid.uuid4()),
            linkedin_raw_id=candidate.linkedin_raw_id,
            x_raw_id=candidate.x_raw_id,
            linkedin_canonical_id=candidate.linkedin_canonical_id,
            x_canonical_id=candidate.x_canonical_id,
            signals=candidate.signals,
            linkedin_attrs=candidate.linkedin_attrs,
            x_attrs=candidate.x_attrs,
        )
        self._records.append(merge)
        self._save()
        return merge

    def list_pending(self) -> list[PendingMerge]:
        return [r for r in self._records if r.status == "pending"]

    def list_all(self) -> list[PendingMerge]:
        return list(self._records)

    def paired_raw_ids(self) -> set[tuple[str, str]]:
        """All (linkedin_raw_id, x_raw_id) pairs regardless of status."""
        return {(r.linkedin_raw_id, r.x_raw_id) for r in self._records}

    def count_pending(self) -> int:
        return sum(1 for r in self._records if r.status == "pending")

    def reject(self, candidate_id: str) -> bool:
        for record in self._records:
            if record.candidate_id == candidate_id:
                record.status = "rejected"
                record.decided_at = datetime.now(UTC).isoformat()
                self._save()
                return True
        return False

    def confirm(self, candidate_id: str) -> PendingMerge | None:
        """Mark confirmed. Caller must also call CanonicalLog.merge()."""
        for record in self._records:
            if record.candidate_id == candidate_id:
                record.status = "confirmed"
                record.decided_at = datetime.now(UTC).isoformat()
                self._save()
                return record
        return None
