"""Playwright browser launcher with persistent user-data-dir per platform.

Sessions persist between commands (login → discover → review → next).
Headed by default so the user can see CAPTCHA, throttling, etc. and intervene.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, sync_playwright


@contextmanager
def launch_persistent_browser(
    profile_dir: Path,
    headed: bool = True,
) -> Iterator[BrowserContext]:
    """Launch Chromium with a persistent user-data-dir. Headed by default.

    Usage:
        with launch_persistent_browser(paths.profiles / "x") as context:
            page = context.new_page()
            page.goto("https://x.com/search?q=...")
    """
    profile_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not headed,
            viewport={"width": 1280, "height": 800},
            # Stealth flags — suppress automation signals that trigger X's "not secure" warning
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            ignore_default_args=["--enable-automation"],
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        try:
            yield context
        finally:
            context.close()
