"""`socialgraph import {linkedin|x} <path>` — ingest official platform export.

Wraps the linkedin/x ingesters in:
- lockfile guard (no two imports concurrent)
- sync_log start/end events
- structured exit codes
"""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import typer

from socialgraph.exit_codes import ExitCode
from socialgraph.ingest.import_linkedin import LinkedInImportError, import_linkedin_csv
from socialgraph.ingest.import_x import (
    XArchiveError,
    import_x_archive,
)
from socialgraph.lockfile import Lock, LockHeldError
from socialgraph.paths import DataPaths
from socialgraph.sync_log import SyncLog


def _new_run_id() -> str:
    """Return a UTC-timestamped, collision-resistant run identifier.

    `parsed_for_run(platform, source, run_id)` will prepend `{platform}_{source}_`
    on its own — keep this bare to avoid duplicate prefixes in filenames.
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{uuid.uuid4().hex[:6]}"


def import_command(platform: str, path: Path, force_unlock: bool) -> None:
    if platform not in ("linkedin", "x"):
        typer.secho(
            f"unknown platform: {platform!r} (expected: linkedin | x)",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    if not path.is_file():
        typer.secho(f"file not found: {path}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    data_root = Path.cwd() / "data"
    paths = DataPaths(data_root)
    paths.ensure()
    log = SyncLog(paths.sync_log)
    run_id = _new_run_id()
    dst = paths.parsed_for_run(platform, "import", run_id)

    try:
        with Lock(paths.lock_file, force_unlock=force_unlock):
            log.append(
                "import.start",
                cmd="import",
                platform=platform,
                run_id=run_id,
                source_path=str(path),
            )
            t0 = time.monotonic()
            try:
                if platform == "linkedin":
                    contacts = import_linkedin_csv(path, dst, run_id=run_id)
                else:
                    contacts = import_x_archive(path, dst, run_id=run_id)
            except (LinkedInImportError, XArchiveError) as exc:
                log.append(
                    "error.import_failed",
                    run_id=run_id,
                    platform=platform,
                    message=str(exc),
                )
                typer.secho(f"import failed: {exc}", err=True, fg=typer.colors.RED)
                raise typer.Exit(code=ExitCode.GENERIC_ERROR) from exc
            duration_ms = int((time.monotonic() - t0) * 1000)
            log.append(
                "import.end",
                cmd="import",
                platform=platform,
                run_id=run_id,
                count=len(contacts),
                duration_ms=duration_ms,
                out_path=str(dst),
            )
            typer.echo(f"imported {len(contacts)} contacts → {dst}")
    except LockHeldError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.LOCK_HELD) from exc
