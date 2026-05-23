"""`socialgraph who-at "<company>"` — list network connections at a company."""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import at_company
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore


def who_at_command(company: str) -> None:
    paths = DataPaths(Path.cwd() / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is None:
        typer.echo("no graph yet — run: socialgraph import linkedin <path>")
        return

    G = build_graph(snap)
    results = at_company(G, company)

    if not results:
        typer.echo(f"no connections at '{company}'")
        return

    typer.echo(f"{len(results)} connection(s) at '{company}':\n")
    for person in sorted(results, key=lambda p: p.get("full_name", "")):
        name = person.get("full_name", "(unknown)")
        title = person.get("current_title", "")
        line = f"  {name}"
        if title:
            line += f" — {title}"
        typer.echo(line)
