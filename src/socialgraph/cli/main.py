"""Top-level Typer app for the socialgraph CLI.

Subcommands are registered in this module to keep `cli/main.py` as the single
entry point. Each subcommand's implementation lives in its own module under
`src/socialgraph/cli/`.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph import __version__
from socialgraph.cli.import_cmd import import_command
from socialgraph.cli.init_cmd import init_command
from socialgraph.cli.link_cmd import link_command
from socialgraph.cli.login_cmd import login_command
from socialgraph.cli.merge_review_cmd import merge_review_command
from socialgraph.cli.neighbors_cmd import neighbors_command
from socialgraph.cli.rebuild_cmd import rebuild_command
from socialgraph.cli.status_cmd import status_command
from socialgraph.cli.unmerge_cmd import unmerge_command
from socialgraph.cli.who_at_cmd import who_at_command

app = typer.Typer(
    name="socialgraph",
    help="Personal network sovereignty tool.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"socialgraph {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """SocialGraph CLI."""


@app.command("init")
def init() -> None:
    """Scaffold data/ dir and copy example .env / config.yml."""
    init_command()


@app.command("import")
def import_(
    platform: str = typer.Argument(..., help="linkedin | x"),
    path: Path = typer.Argument(..., exists=False, help="Path to export file"),
    force_unlock: bool = typer.Option(
        False, "--force-unlock", help="Clear stale lock and proceed."
    ),
) -> None:
    """Import official platform data export → parsed JSONL."""
    import_command(platform, path, force_unlock=force_unlock)


@app.command("status")
def status() -> None:
    """Show counts of parsed files, last imports, recent errors."""
    status_command()


@app.command("rebuild")
def rebuild() -> None:
    """Rebuild graph from all parsed JSONL files (restores after nuke)."""
    rebuild_command()


@app.command("who-at")
def who_at(company: str = typer.Argument(..., help="Company name to search for")) -> None:
    """List connections at a company."""
    who_at_command(company)


@app.command("neighbors")
def neighbors(
    canonical_id: str = typer.Argument(..., help="Canonical ID of the person"),
    depth: int = typer.Option(1, "--depth", "-d", help="Traversal depth via company nodes"),
) -> None:
    """List company colleagues of a person (depth=1: same company)."""
    neighbors_command(canonical_id, depth)


@app.command("merge-review")
def merge_review() -> None:
    """Interactively review cross-platform merge candidates."""
    merge_review_command()


@app.command("link")
def link(
    canonical_id_a: str = typer.Argument(..., help="Canonical ID to keep (primary)"),
    canonical_id_b: str = typer.Argument(..., help="Canonical ID to merge into id_a"),
) -> None:
    """Explicitly link two persons as the same individual."""
    link_command(canonical_id_a, canonical_id_b)


@app.command("unmerge")
def unmerge(
    canonical_id: str = typer.Argument(
        ..., help="Canonical ID to split back into separate persons"
    ),
) -> None:
    """Split a wrongly-merged person back into separate identities."""
    unmerge_command(canonical_id)


@app.command("login")
def login(
    platform: str = typer.Argument(..., help="linkedin | x"),
) -> None:
    """Open Chromium so you can log in; session persists for later commands."""
    login_command(platform)


if __name__ == "__main__":
    app()
