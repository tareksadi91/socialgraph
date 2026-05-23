"""`socialgraph rebuild` — rebuild graph from all parsed JSONL files.

Re-reads every record in data/parsed/, resolves identity using the
existing merge_decisions.jsonl (preserves canonical_ids), builds a
fresh snapshot, and writes it if it differs from the latest one.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.paths import DataPaths
from socialgraph.pipeline import run_pipeline


def rebuild_command() -> None:
    paths = DataPaths(Path.cwd() / "data")

    if not paths.parsed.is_dir() or not any(paths.parsed.glob("*.jsonl")):
        typer.echo("no parsed data found — run: socialgraph import linkedin <path>")
        return

    typer.echo("rebuilding graph from all parsed records…")
    counts = run_pipeline(paths)

    if counts["persons"] == 0:
        typer.echo("nothing to rebuild (all parsed files empty)")
        return

    typer.echo(
        f"graph rebuilt: {counts['persons']} persons, "
        f"{counts['companies']} companies, {counts['edges']} edges"
    )
    if counts["snapshot_written"]:
        typer.echo("new snapshot written")
    else:
        typer.echo("graph unchanged — no new snapshot")
