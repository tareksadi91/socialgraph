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
from socialgraph.cli.status_cmd import status_command

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
        False, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."
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
    force_unlock: bool = typer.Option(False, "--force-unlock", help="Clear stale lock and proceed."),
) -> None:
    """Import official platform data export → parsed JSONL."""
    import_command(platform, path, force_unlock=force_unlock)


@app.command("status")
def status() -> None:
    """Show counts of parsed files, last imports, recent errors."""
    status_command()


if __name__ == "__main__":
    app()
