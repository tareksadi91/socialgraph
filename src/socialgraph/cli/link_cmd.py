"""`socialgraph link <canonical_id_a> <canonical_id_b>` — explicit cross-platform link.

Merges two canonical_ids into one (canonical_id_a survives). All raw_ids
currently mapped to canonical_id_b are reassigned to canonical_id_a.
Triggers a pipeline rebuild so the snapshot reflects the merge.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.exit_codes import ExitCode
from socialgraph.identity.canonical import CanonicalLog
from socialgraph.paths import DataPaths
from socialgraph.pipeline import run_pipeline


def link_command(canonical_id_a: str, canonical_id_b: str) -> None:
    if canonical_id_a == canonical_id_b:
        typer.secho("error: cannot link a person to themselves", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    paths = DataPaths(Path.cwd() / "data")
    log = CanonicalLog(paths.merge_decisions)

    raw_ids_a = log.raw_ids_for(canonical_id_a)
    raw_ids_b = log.raw_ids_for(canonical_id_b)

    if not raw_ids_a:
        typer.secho(
            f"error: canonical_id_a not found: {canonical_id_a}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)
    if not raw_ids_b:
        typer.secho(
            f"error: canonical_id_b not found: {canonical_id_b}", err=True, fg=typer.colors.RED
        )
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    log.merge(raw_ids_b, target_canonical_id=canonical_id_a)
    typer.echo(f"linked {canonical_id_b[:8]}... -> {canonical_id_a[:8]}...")

    counts = run_pipeline(paths)
    typer.echo(f"graph updated: {counts['persons']} persons, {counts['companies']} companies")
