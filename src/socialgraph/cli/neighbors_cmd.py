"""`socialgraph neighbors <canonical_id>` — list company colleagues.

In M2, neighbors are Persons who share a company (via WORKS_AT edges).
Inter-person edges become available in M4 when scrape provides mutual
connection data.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import neighbors_via_company
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore


def neighbors_command(canonical_id: str, depth: int) -> None:
    paths = DataPaths(Path.cwd() / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is None:
        typer.echo("no graph yet — run: socialgraph import linkedin <path>")
        return

    G = build_graph(snap)
    results = neighbors_via_company(G, canonical_id, depth=depth)

    if not results:
        typer.echo(f"no neighbors found for {canonical_id!r}")
        typer.echo(
            "(neighbors = colleagues at the same company;"
            " scrape data adds richer connections in M4)"
        )
        return

    typer.echo(f"{len(results)} neighbor(s) (depth={depth}):\n")
    for person in sorted(results, key=lambda p: p.get("full_name", "")):
        name = person.get("full_name", "(unknown)")
        company = person.get("current_company", "")
        cid = person.get("canonical_id", "")
        line = f"  {name}"
        if company:
            line += f" @ {company}"
        line += f"  [{cid}]"
        typer.echo(line)
