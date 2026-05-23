"""`socialgraph login {linkedin|x}` — open browser, persist session.

Opens a Chromium window pointed at the login URL of the chosen platform.
The user logs in interactively; cookies and session storage are saved
under data/profiles/{platform}/. Subsequent scrape/port commands reuse
this profile directory and start already logged in.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.exit_codes import ExitCode
from socialgraph.paths import DataPaths
from socialgraph.port.browser import launch_persistent_browser

_LOGIN_URLS = {
    "x": "https://x.com/login",
    "linkedin": "https://www.linkedin.com/login",
}


def login_command(platform: str) -> None:
    if platform not in _LOGIN_URLS:
        typer.secho(
            f"unknown platform: {platform!r} (expected: linkedin | x)",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    paths = DataPaths(Path.cwd() / "data")
    profile_dir = paths.profiles / platform

    typer.echo(f"Opening Chromium for {platform} login.")
    typer.echo(f"Profile will be saved to: {profile_dir}")
    typer.echo("Log in, then come back here and press Enter.\n")

    with launch_persistent_browser(profile_dir) as context:
        page = context.new_page()
        page.goto(_LOGIN_URLS[platform])
        typer.prompt("Press Enter when you have finished logging in", default="")

    typer.echo(f"Session saved. You can now run port discovery against {platform}.")
