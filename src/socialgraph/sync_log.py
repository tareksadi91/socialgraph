"""Append-only operational event log (data/sync_log.jsonl).

Every CLI command emits structured `cmd.start` / `cmd.end` events plus any
`error.*` events. Each record is one JSON line with a UTC timestamp.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class SyncLog:
    """JSONL append-only event log with fsync-per-line durability."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: str, **fields: Any) -> None:
        """Append one event with current UTC timestamp + arbitrary fields."""
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def iter(self) -> Iterator[dict[str, Any]]:
        """Yield parsed events in file order. Skips blank/malformed lines."""
        if not self.path.is_file():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def last_errors(self, limit: int = 3) -> list[dict[str, Any]]:
        """Return up to `limit` most-recent events whose event name starts with 'error.'."""
        errs = [e for e in self.iter() if e.get("event", "").startswith("error.")]
        return errs[-limit:]
