"""`socialgraph port next` — walk the follow queue, one URL at a time.

Opens each queued X profile in the user's default browser via the OS
'open' command (macOS) or 'xdg-open' (Linux). The user clicks Follow
in their real browser. State is updated based on user choice:
  [f] followed   [s] skipped   [e] error   [q] quit
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import typer

from socialgraph.paths import DataPaths
from socialgraph.port.state import PortState


def _open_url(url: str) -> None:
    """Open URL in the user's default browser (cross-platform)."""
    if sys.platform == "darwin":
        opener = "open"
    elif sys.platform.startswith("linux"):
        opener = "xdg-open"
    else:
        opener = None
    if opener and shutil.which(opener):
        subprocess.run([opener, url], check=False)
    else:
        typer.echo(f"  (open this URL manually: {url})")


def port_next_command() -> None:
    paths = DataPaths(Path.cwd() / "data")
    state = PortState(paths.port_state)
    queued = state.list_queued()
    if not queued:
        typer.echo("queue is empty.")
        return

    typer.echo(f"{len(queued)} in queue. For each: [f]ollowed [s]kipped [e]rror [q]uit\n")
    for entry in queued:
        typer.echo(f"  -> @{entry.selected_handle}  {entry.x_profile_url}")
        state.opened(entry.candidate_id)
        _open_url(entry.x_profile_url or "")
        choice = typer.prompt("    Decision", default="s").strip().lower()
        if choice == "q":
            typer.echo("quit.")
            return
        if choice == "f":
            state.followed(entry.candidate_id)
            typer.echo("    followed")
        elif choice == "e":
            state.error(entry.candidate_id, code="user_reported")
            typer.echo("    error logged")
        else:
            state.skipped(entry.candidate_id)
            typer.echo("    skipped")
