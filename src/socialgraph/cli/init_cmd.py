"""`socialgraph init` — scaffold data/ dir and copy example .env + config.yml.

Run once per project clone. Does NOT overwrite existing .env or config.yml
to protect user customizations.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from socialgraph.paths import DataPaths


def init_command() -> None:
    project_root = Path.cwd()
    env_example = project_root / ".env.example"
    cfg_example = project_root / "config.yml.example"
    env = project_root / ".env"
    cfg = project_root / "config.yml"

    if not env_example.is_file() or not cfg_example.is_file():
        typer.secho(
            "missing .env.example or config.yml.example in current directory",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=5)

    if env.is_file():
        typer.echo(f".env already exists, leaving untouched: {env}")
    else:
        shutil.copyfile(env_example, env)
        typer.echo(f"created {env}")

    if cfg.is_file():
        typer.echo(f"config.yml already exists, leaving untouched: {cfg}")
    else:
        shutil.copyfile(cfg_example, cfg)
        typer.echo(f"created {cfg}")

    paths = DataPaths(project_root / "data")
    paths.ensure()
    typer.echo(f"data dir scaffolded at {paths.root}")
    typer.echo("\nNext steps:")
    typer.echo("  1. Edit .env with your LLM API key (or leave blank for no-LLM mode)")
    typer.echo("  2. Download LinkedIn export → run: socialgraph import linkedin <path>")
    typer.echo("  3. Request X archive → run: socialgraph import x <path>")
    typer.echo("  4. socialgraph status")
