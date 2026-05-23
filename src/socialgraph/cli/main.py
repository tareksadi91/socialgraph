"""Top-level Typer app for the socialgraph CLI.

Subcommands are registered in this module to keep `cli/main.py` as the single
entry point. Each subcommand's implementation lives in its own module under
`src/socialgraph/cli/`.
"""
from __future__ import annotations

import typer

from socialgraph import __version__

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


if __name__ == "__main__":
    app()
