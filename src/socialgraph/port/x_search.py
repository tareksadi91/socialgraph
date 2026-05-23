"""X search client — Protocol + fake (for tests) + Playwright (for real use).

Production code receives `XSearchClient` via dependency injection so
tests inject `FakeXSearchClient` and never touch a real browser.

The Playwright implementation is intentionally minimal: navigate to the
user search URL, wait for results, scrape the first N user cards by their
data-testid attributes, return XSearchResult objects.
Selector breakage in production is contained to this file.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Protocol
from urllib.parse import quote_plus

from socialgraph.port.browser import launch_persistent_browser
from socialgraph.port.scoring import XSearchResult


class XSearchClient(Protocol):
    """Search X for users matching a free-text query."""

    def search(self, query: str) -> list[XSearchResult]: ...


class FakeXSearchClient:
    """Test double — returns canned responses keyed by query string."""

    def __init__(self, responses: dict[str, list[XSearchResult]]) -> None:
        self._responses = responses
        self.queries: list[str] = []

    def search(self, query: str) -> list[XSearchResult]:
        self.queries.append(query)
        return list(self._responses.get(query, []))


class PlaywrightXSearchClient:
    """Real X user search via headed Playwright.

    Rate-limits requests (8s + jitter by default). Reuses one browser context
    across calls. Use as a context manager.
    """

    def __init__(
        self,
        profile_dir: Path,
        throttle_seconds: float = 8.0,
        jitter_seconds: float = 3.0,
        max_results_per_query: int = 5,
        headed: bool = True,
    ) -> None:
        self.profile_dir = profile_dir
        self.throttle_seconds = throttle_seconds
        self.jitter_seconds = jitter_seconds
        self.max_results_per_query = max_results_per_query
        self.headed = headed
        self._context = None
        self._page = None
        self._playwright_cm = None
        self._last_search_at: float = 0.0

    def __enter__(self) -> PlaywrightXSearchClient:
        self._playwright_cm = launch_persistent_browser(self.profile_dir, headed=self.headed)
        self._context = self._playwright_cm.__enter__()
        self._page = self._context.new_page()
        return self

    def __exit__(self, *exc) -> None:
        if self._playwright_cm is not None:
            self._playwright_cm.__exit__(*exc)

    def search(self, query: str) -> list[XSearchResult]:
        if self._page is None:
            raise RuntimeError("PlaywrightXSearchClient must be used as a context manager")
        self._throttle()
        url = f"https://x.com/search?q={quote_plus(query)}&f=user"
        self._page.goto(url, wait_until="domcontentloaded")
        try:
            self._page.wait_for_selector('[data-testid="UserCell"]', timeout=8000)
        except Exception:
            return []
        cells = self._page.locator('[data-testid="UserCell"]').all()[: self.max_results_per_query]
        out: list[XSearchResult] = []
        for cell in cells:
            try:
                handle_locator = cell.locator('a[href^="/"]').first
                href = handle_locator.get_attribute("href") or ""
                handle = href.lstrip("/").split("/")[0]
                text = cell.inner_text()
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                display_name = lines[0] if lines else ""
                bio_preview = " ".join(lines[1:])[:200] if len(lines) > 1 else ""
                if handle:
                    out.append(
                        XSearchResult(
                            handle=handle,
                            display_name=display_name,
                            bio_preview=bio_preview,
                        )
                    )
            except Exception:
                continue
        return out

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_search_at
        sleep_for = self.throttle_seconds + random.uniform(0, self.jitter_seconds) - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_search_at = time.monotonic()
