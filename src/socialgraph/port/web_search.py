"""Google Custom Search Engine client for Tier 2 handle discovery.

Queries Google CSE with `site:x.com` to find X profiles for a person by name + company.
Requires GOOGLE_CSE_API_KEY and GOOGLE_CSE_ID environment variables.

Setup (one-time):
  1. Create CSE at https://programmablesearch.google.com/
  2. Set to "Search the entire web"
  3. Enable in Google Cloud Console → APIs & Services → Custom Search JSON API
  4. Get API key from Google Cloud Console → Credentials

FakeGoogleCSEClient provides a test double with canned responses.
"""

from __future__ import annotations

import re

import httpx

from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate

_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
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


def _extract_handle_from_url(url: str) -> str | None:
    m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url or "")
    if not m:
        return None
    handle = m.group(1)
    return None if handle.lower() in _RESERVED_X_PATHS else handle


def _build_query(name: str, company: str | None) -> str:
    q = f'"{name}"'
    if company:
        q += f' "{company}"'
    q += " site:x.com"
    return q


def _parse_handles_from_cse_response(response: dict) -> list[str]:
    handles: list[str] = []
    for item in response.get("items", []):
        handle = _extract_handle_from_url(item.get("link", ""))
        if handle and handle not in handles:
            handles.append(handle)
    return handles


class GoogleCSEClient:
    """Tier 2: Google Custom Search to find X profiles."""

    def __init__(self, api_key: str, cse_id: str, num_results: int = 5) -> None:
        self.api_key = api_key
        self.cse_id = cse_id
        self.num_results = num_results

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult:
        query = _build_query(name, company)
        try:
            resp = httpx.get(
                _GOOGLE_CSE_URL,
                params={
                    "key": self.api_key,
                    "cx": self.cse_id,
                    "q": query,
                    "num": self.num_results,
                },
                timeout=10.0,
            )
            if resp.status_code != 200:
                return DiscoveryResult(
                    handle=None, confidence=0.0, source="google_cse", candidates=[]
                )
            handles = _parse_handles_from_cse_response(resp.json())
        except Exception:
            return DiscoveryResult(handle=None, confidence=0.0, source="google_cse", candidates=[])

        candidates = [
            PortCandidate(
                handle=h,
                display_name=name,
                bio_preview="",
                score=0.85 - i * 0.05,  # position-based score decay
                rationale=f"google_cse_result_{i + 1}",
                source="google_cse",
            )
            for i, h in enumerate(handles)
        ]
        return DiscoveryResult(
            handle=None, confidence=0.7, source="google_cse", candidates=candidates
        )


class FakeGoogleCSEClient:
    """Test double — keyed by query string → list of handles."""

    def __init__(self, responses: dict[str, list[str]]) -> None:
        self._responses = responses

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult:
        query = _build_query(name, company)
        handles = self._responses.get(query, [])
        candidates = [
            PortCandidate(
                handle=h,
                display_name=name,
                bio_preview="",
                score=0.85,
                rationale="fake",
                source="google_cse",
            )
            for h in handles
        ]
        return DiscoveryResult(
            handle=None,
            confidence=0.7 if handles else 0.0,
            source="google_cse",
            candidates=candidates,
        )
