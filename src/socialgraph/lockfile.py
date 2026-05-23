"""Lockfile primitive — prevents concurrent socialgraph CLI invocations.

A single `data/.lock` file holds {pid, started_at, hostname}. New invocations
refuse to start while it's held. Stale locks (process not alive) auto-clear.
"""

from __future__ import annotations

import json
import os
import platform
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import Self

from socialgraph.exit_codes import ExitCode


class LockHeldError(Exception):
    """Raised when another socialgraph instance is already running."""

    exit_code = ExitCode.LOCK_HELD


class Lock:
    """Context manager guarding the data/.lock file.

    Usage:
        with Lock(paths.lock_file):
            ...  # exclusive section

    Holds {pid, started_at, hostname} as JSON. Stale locks (pid not running)
    are detected via os.kill(pid, 0) and cleared automatically. `force_unlock`
    bypasses staleness detection.
    """

    def __init__(self, path: Path, force_unlock: bool = False) -> None:
        self.path = path
        self.force_unlock = force_unlock

    def __enter__(self) -> Self:
        if self.path.is_file():
            if self.force_unlock or self._is_stale():
                self.path.unlink()
            else:
                try:
                    existing = json.loads(self.path.read_text())
                    pid = existing.get("pid")
                except json.JSONDecodeError:
                    pid = "unknown"
                raise LockHeldError(
                    f"another instance running (pid {pid}). Use --force-unlock if stale."
                )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "started_at": datetime.now(UTC).isoformat(),
                    "hostname": platform.node(),
                }
            )
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.path.is_file():
            try:
                existing = json.loads(self.path.read_text())
                if existing.get("pid") == os.getpid():
                    self.path.unlink()
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _is_stale(self) -> bool:
        try:
            existing = json.loads(self.path.read_text())
            pid = existing.get("pid")
            if not isinstance(pid, int):
                return True
            os.kill(pid, 0)
            return False
        except (json.JSONDecodeError, FileNotFoundError):
            return True
        except (OSError, ProcessLookupError):
            return True
