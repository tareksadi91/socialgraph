"""`socialgraph port review` — confirm/reject X handle candidates.

For each entry in needs_review, show the candidate list and prompt:
  1..N    pick that candidate (1-indexed)
  n       reject all (no X handle for this person)
  s       skip (decide later)
  q       quit
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.paths import DataPaths
from socialgraph.port.state import PortState


def port_review_command() -> None:
    paths = DataPaths(Path.cwd() / "data")
    state = PortState(paths.port_state)

    pending = state.list_needs_review()
    if not pending:
        typer.echo("no candidates to review — run: socialgraph port discover")
        return

    typer.echo(f"{len(pending)} candidate set(s) to review.")
    typer.echo("  pick: 1..N   type: t   skip: s   reject: n   quit: q\n")

    for entry in pending:
        typer.echo("─" * 60)
        typer.echo(f"  LinkedIn: {entry.linkedin_canonical_id[:8]}...")
        if entry.candidates:
            for idx, c in enumerate(entry.candidates, start=1):
                line = (
                    f"  [{idx}] @{c.handle}  ({c.display_name})  score={c.score:.2f}  [{c.source}]"
                )
                if c.bio_preview:
                    line += f"  — {c.bio_preview[:80]}"
                typer.echo(line)
        else:
            typer.echo("  (no candidates found — use [t] to enter handle manually)")

        choice = typer.prompt("\n  Decision", default="s").strip().lower()

        if choice == "q":
            typer.echo("quit.")
            return
        if choice == "n":
            state.reject(entry.candidate_id)
            typer.echo("  rejected")
            continue
        if choice in ("s", ""):
            typer.echo("  skipped")
            continue
        if choice == "t":
            handle = typer.prompt("    Type X handle (without @)").strip().lstrip("@")
            if handle:
                state.resolve(entry.candidate_id, selected_handle=handle)
                state.queue(entry.candidate_id, x_profile_url=f"https://x.com/{handle}")
                typer.echo(f"  manually linked -> @{handle}, queued for follow")
            else:
                typer.echo("  empty handle, skipping")
            continue
        try:
            idx = int(choice) - 1
        except ValueError:
            typer.echo("  unknown input, skipping")
            continue
        if 0 <= idx < len(entry.candidates):
            handle = entry.candidates[idx].handle
            state.resolve(entry.candidate_id, selected_handle=handle)
            state.queue(entry.candidate_id, x_profile_url=f"https://x.com/{handle}")
            typer.echo(f"  resolved -> @{handle}, queued for follow")
        else:
            typer.echo("  out of range, skipping")
