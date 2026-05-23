"""LinkedIn Contact Info Scraper — Tier 1 handle discovery.

Navigates to a LinkedIn profile's contact-info overlay and extracts any
Twitter/X URL the person has explicitly linked. This is the highest-confidence
signal: user-provided link = definitive handle, no review needed.

Requires an active LinkedIn Playwright session (data/profiles/linkedin/).
Run `socialgraph login linkedin` first.
"""

from __future__ import annotations

import random
import re
import time
from pathlib import Path

from socialgraph.port.browser import launch_persistent_browser
from socialgraph.port.discovery import DiscoveryResult

# Twitter/X reserved paths that are not user handles
_RESERVED_X_PATHS = {
    "home",
    "explore",
    "notifications",
    "messages",
    "bookmarks",
    "settings",
    "compose",
    "search",
    "i",
    "login",
    "signup",
}


def _extract_handle_from_social_url(url: str) -> str | None:
    """Extract @handle from a twitter.com or x.com URL. Returns None for non-profile URLs."""
    if not url:
        return None
    url_lower = url.lower()
    if "twitter.com" not in url_lower and "x.com" not in url_lower:
        return None
    # Extract path segment after domain
    m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
    if not m:
        return None
    handle = m.group(1)
    if handle.lower() in _RESERVED_X_PATHS:
        return None
    return handle


class LinkedInContactInfoClient:
    """Tier 1: scrape Twitter/X links from LinkedIn Contact Info overlay."""

    def __init__(self, profile_dir: Path, throttle_seconds: float = 2.0) -> None:
        self.profile_dir = profile_dir
        self.throttle_seconds = throttle_seconds
        self._last_request_at: float = 0.0
        self._context = None
        self._playwright_cm = None

    def __enter__(self) -> LinkedInContactInfoClient:
        self._playwright_cm = launch_persistent_browser(self.profile_dir, headed=False)
        self._context = self._playwright_cm.__enter__()
        return self

    def __exit__(self, *exc):
        if self._playwright_cm is not None:
            return self._playwright_cm.__exit__(*exc)

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = self.throttle_seconds + random.uniform(0, 1.0) - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()

    def _get_page(self, url: str):
        """Navigate to URL and return page. Override in tests."""
        if self._context is None:
            raise RuntimeError("Use LinkedInContactInfoClient as a context manager")
        self._throttle()
        page = self._context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=10000)
        return page

    def _slug_from_url(self, profile_url: str) -> str:
        """Extract slug from linkedin.com/in/{slug}."""
        m = re.search(r"linkedin\.com/in/([^/?]+)", profile_url)
        return m.group(1) if m else profile_url.rstrip("/").rsplit("/", 1)[-1]

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult:
        """Scrape LinkedIn contact-info overlay for Twitter/X link."""
        slug = self._slug_from_url(profile_url)
        contact_url = f"https://www.linkedin.com/in/{slug}/overlay/contact-info/"
        try:
            page = self._get_page(contact_url)
            try:
                links = page.query_selector_all("a[href]")
                for link in links:
                    href = link.get_attribute("href") or ""
                    handle = _extract_handle_from_social_url(href)
                    if handle:
                        return DiscoveryResult(
                            handle=handle,
                            confidence=1.0,
                            source="li_contact_info",
                            candidates=[],
                        )
            finally:
                try:
                    page.close()
                except Exception:
                    pass
        except RuntimeError:
            raise
        except Exception:
            pass
        return DiscoveryResult(
            handle=None,
            confidence=0.0,
            source="li_contact_info",
            candidates=[],
        )
