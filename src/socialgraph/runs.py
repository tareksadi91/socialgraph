"""Shared run-ID generator for all ingest operations."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_run_id() -> str:
    """Return a UTC-timestamped, collision-resistant run identifier.

    Format: YYYYMMDDTHHMMSSZ_<6-hex-chars>
    Used as the base for all parsed/ JSONL filenames via DataPaths.parsed_for_run().
    DataPaths.parsed_for_run() prepends {platform}_{source}_ — keep this bare.
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{uuid.uuid4().hex[:6]}"
