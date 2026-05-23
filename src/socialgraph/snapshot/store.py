"""SnapshotStore — write and read immutable graph snapshots.

Each snapshot is an atomic JSONL file under snapshots/{ts}.jsonl.
Writes are skipped when the diff vs the previous snapshot is empty,
preventing unnecessary disk growth on repeated re-imports.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from socialgraph.snapshot.diff import snapshot_diff
from socialgraph.snapshot.models import Snapshot


class SnapshotStore:
    """Manages the snapshots/ directory."""

    def __init__(self, snapshots_dir: Path) -> None:
        self.dir = snapshots_dir

    def write(self, snapshot: Snapshot) -> Path | None:
        """Write snapshot atomically. Returns the path, or None if skipped.

        Skipped when: snapshot is empty, OR diff vs latest is empty.
        """
        if snapshot.is_empty():
            return None

        previous = self.read_latest()
        if previous is not None and snapshot_diff(previous, snapshot).is_empty():
            return None

        self.dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        final_path = self.dir / f"{ts}.jsonl"
        tmp_path = self.dir / f".{ts}.tmp"

        lines = snapshot.to_jsonl_lines()
        with tmp_path.open("w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        tmp_path.rename(final_path)
        return final_path

    def read_latest(self) -> Snapshot | None:
        """Return the most recent snapshot, or None if none exist."""
        if not self.dir.is_dir():
            return None
        files = sorted(
            (p for p in self.dir.glob("*.jsonl") if not p.name.startswith(".")),
            reverse=True,
        )
        if not files:
            return None
        return self._read_file(files[0])

    def _read_file(self, path: Path) -> Snapshot:
        lines = path.read_text(encoding="utf-8").splitlines()
        return Snapshot.from_jsonl_lines(lines)
