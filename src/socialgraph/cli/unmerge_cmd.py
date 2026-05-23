"""`socialgraph unmerge <canonical_id>` — split a wrongly-merged person.

Finds all raw_ids currently mapped to canonical_id, assigns each (except
the first) a fresh UUID, writes an unmerge event, and rebuilds the graph.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import typer

from socialgraph.exit_codes import ExitCode
from socialgraph.identity.canonical import CanonicalLog
from socialgraph.paths import DataPaths
from socialgraph.pipeline import run_pipeline


def unmerge_command(canonical_id: str) -> None:
    paths = DataPaths(Path.cwd() / "data")
    log = CanonicalLog(paths.merge_decisions)

    raw_ids = log.raw_ids_for(canonical_id)
    if not raw_ids:
        typer.secho(f"error: canonical_id not found: {canonical_id}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    if len(raw_ids) == 1:
        typer.echo(f"only one raw_id ({raw_ids[0]}) — nothing to unmerge")
        return

    # Keep first raw_id under canonical_id; assign new UUIDs to the rest
    reassignments: dict[str, str] = {}
    for rid in raw_ids[1:]:
        reassignments[rid] = str(uuid.uuid4())

    log.unmerge(reassignments=reassignments)
    typer.echo(f"unmerged {canonical_id[:8]}... -> {len(reassignments) + 1} separate persons")

    counts = run_pipeline(paths)
    typer.echo(f"graph updated: {counts['persons']} persons, {counts['companies']} companies")
