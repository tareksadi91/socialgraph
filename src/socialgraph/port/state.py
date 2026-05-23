"""Port lifecycle state — append-only JSONL log, replay-derived state.

Each LinkedIn canonical_id can be in one of these states:

  needs_review → resolved → queued → opened → followed | skipped | error
  needs_review → rejected (no X candidate selected)

Events are appended to data/port_state.jsonl. Current state is derived by
replaying the log on construction — same pattern as CanonicalLog.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

PortStatus = Literal[
    "needs_review",
    "resolved",
    "queued",
    "opened",
    "followed",
    "skipped",
    "rejected",
    "error",
]


@dataclass
class PortCandidate:
    """One X candidate found for a LinkedIn person."""

    handle: str
    display_name: str
    bio_preview: str
    score: float
    rationale: str
    source: str = ""  # which tier discovered this: li_contact_info | google_cse | apollo | manual


@dataclass
class PortEntry:
    """Current state of one LinkedIn-to-X port attempt."""

    candidate_id: str
    linkedin_canonical_id: str
    candidates: list[PortCandidate] = field(default_factory=list)
    selected_handle: str | None = None
    x_profile_url: str | None = None
    status: PortStatus = "needs_review"
    last_event_ts: str | None = None
    error_code: str | None = None


class PortState:
    """Wraps port_state.jsonl: record events, expose state by status."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._entries: dict[str, PortEntry] = {}  # candidate_id → PortEntry
        self._linkedin_to_candidate: dict[str, str] = {}  # linkedin_canonical_id → candidate_id
        self._replay()

    def record_discovered(
        self,
        linkedin_canonical_id: str,
        candidates: list[PortCandidate],
    ) -> str:
        """Record discovery result. Returns the candidate_id."""
        candidate_id = str(uuid.uuid4())
        entry = PortEntry(
            candidate_id=candidate_id,
            linkedin_canonical_id=linkedin_canonical_id,
            candidates=candidates,
            status="needs_review",
        )
        self._entries[candidate_id] = entry
        self._linkedin_to_candidate[linkedin_canonical_id] = candidate_id
        self._append(
            {
                "event": "discovered",
                "candidate_id": candidate_id,
                "linkedin_canonical_id": linkedin_canonical_id,
                "candidates": [asdict(c) for c in candidates],
            }
        )
        return candidate_id

    def resolve(self, candidate_id: str, selected_handle: str) -> None:
        entry = self._entries.get(candidate_id)
        if entry is None:
            return
        entry.selected_handle = selected_handle
        entry.status = "resolved"
        self._append(
            {
                "event": "resolved",
                "candidate_id": candidate_id,
                "selected_handle": selected_handle,
            }
        )

    def reject(self, candidate_id: str) -> None:
        entry = self._entries.get(candidate_id)
        if entry is None:
            return
        entry.status = "rejected"
        self._append({"event": "rejected", "candidate_id": candidate_id})

    def queue(self, candidate_id: str, x_profile_url: str) -> None:
        entry = self._entries.get(candidate_id)
        if entry is None:
            return
        entry.x_profile_url = x_profile_url
        entry.status = "queued"
        self._append(
            {
                "event": "queued",
                "candidate_id": candidate_id,
                "x_profile_url": x_profile_url,
            }
        )

    def opened(self, candidate_id: str) -> None:
        self._transition(candidate_id, "opened")

    def followed(self, candidate_id: str) -> None:
        self._transition(candidate_id, "followed")

    def skipped(self, candidate_id: str) -> None:
        self._transition(candidate_id, "skipped")

    def error(self, candidate_id: str, code: str) -> None:
        entry = self._entries.get(candidate_id)
        if entry is None:
            return
        entry.status = "error"
        entry.error_code = code
        self._append({"event": "error", "candidate_id": candidate_id, "code": code})

    def has_been_processed(self, linkedin_canonical_id: str) -> bool:
        return linkedin_canonical_id in self._linkedin_to_candidate

    def list_needs_review(self) -> list[PortEntry]:
        return [e for e in self._entries.values() if e.status == "needs_review"]

    def list_resolved_not_queued(self) -> list[PortEntry]:
        return [e for e in self._entries.values() if e.status == "resolved"]

    def list_queued(self) -> list[PortEntry]:
        return [e for e in self._entries.values() if e.status == "queued"]

    def list_followed(self) -> list[PortEntry]:
        return [e for e in self._entries.values() if e.status == "followed"]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for entry in self._entries.values():
            out[entry.status] = out.get(entry.status, 0) + 1
        for key in (
            "needs_review",
            "resolved",
            "queued",
            "opened",
            "followed",
            "skipped",
            "rejected",
            "error",
        ):
            out.setdefault(key, 0)
        return out

    def _transition(self, candidate_id: str, new_status: PortStatus) -> None:
        entry = self._entries.get(candidate_id)
        if entry is None:
            return
        entry.status = new_status
        self._append({"event": new_status, "candidate_id": candidate_id})

    def _replay(self) -> None:
        if not self.path.is_file():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            self._apply(event)

    def _apply(self, event: dict) -> None:
        kind = event.get("event")
        cid = event.get("candidate_id")
        if not cid:
            return
        if kind == "discovered":
            candidates = [PortCandidate(**c) for c in event.get("candidates", [])]
            entry = PortEntry(
                candidate_id=cid,
                linkedin_canonical_id=event["linkedin_canonical_id"],
                candidates=candidates,
                status="needs_review",
            )
            self._entries[cid] = entry
            self._linkedin_to_candidate[entry.linkedin_canonical_id] = cid
        elif kind == "resolved":
            entry = self._entries.get(cid)
            if entry:
                entry.selected_handle = event.get("selected_handle")
                entry.status = "resolved"
        elif kind == "rejected":
            entry = self._entries.get(cid)
            if entry:
                entry.status = "rejected"
        elif kind == "queued":
            entry = self._entries.get(cid)
            if entry:
                entry.x_profile_url = event.get("x_profile_url")
                entry.status = "queued"
        elif kind in ("opened", "followed", "skipped"):
            entry = self._entries.get(cid)
            if entry:
                entry.status = kind
        elif kind == "error":
            entry = self._entries.get(cid)
            if entry:
                entry.status = "error"
                entry.error_code = event.get("code")

    def _append(self, record: dict) -> None:
        record["ts"] = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
