"""`socialgraph port queue` — list the upcoming follow queue."""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.paths import DataPaths
from socialgraph.port.state import PortState


def port_queue_command() -> None:
    paths = DataPaths(Path.cwd() / "data")
    state = PortState(paths.port_state)
    queued = state.list_queued()
    if not queued:
        typer.echo("0 in queue — run: socialgraph port review to resolve candidates")
        return
    typer.echo(f"{len(queued)} person(s) queued for follow:\n")
    for entry in queued:
        typer.echo(f"  @{entry.selected_handle}  ->  {entry.x_profile_url}")
    typer.echo("\nrun: socialgraph port next")
