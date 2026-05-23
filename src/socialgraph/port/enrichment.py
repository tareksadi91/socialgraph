"""Apollo.io enrichment client — Tier 3 handle discovery (optional).

Apollo's People Match API accepts name + company and returns social profiles
including Twitter handle. Free tier: 10,000 credits/month.
Requires APOLLO_API_KEY in environment.

Setup: https://app.apollo.io/ → Settings → API Keys

NOTE: Apollo's API endpoint and auth may change. If this tier returns empty
results in production, verify at https://docs.apollo.io/reference/people-enrichment:
  - Endpoint path (may be /api/v1/people/match vs /v1/people/match)
  - Auth header (may be Authorization: Bearer, Api-Key, or x-api-key)
  - Response field path (person.twitter_url vs people[0].twitter_url)
"""

from __future__ import annotations

import re

import httpx

from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate

_APOLLO_URL = "https://api.apollo.io/v1/people/match"
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


def _extract_handle(url: str | None) -> str | None:
    if not url:
        return None
    m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
    if not m:
        return None
    h = m.group(1)
    return None if h.lower() in _RESERVED_X_PATHS else h


class ApolloClient:
    """Tier 3: Apollo.io People Match for Twitter handle enrichment."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult:
        payload: dict[str, str] = {"name": name}
        if company:
            payload["organization_name"] = company
        try:
            resp = httpx.post(
                _APOLLO_URL,
                json=payload,
                headers={"x-api-key": self.api_key, "Content-Type": "application/json"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return DiscoveryResult(handle=None, confidence=0.0, source="apollo", candidates=[])
            twitter_url = resp.json().get("person", {}).get("twitter_url")
            handle = _extract_handle(twitter_url)
        except Exception:
            return DiscoveryResult(handle=None, confidence=0.0, source="apollo", candidates=[])

        if not handle:
            return DiscoveryResult(handle=None, confidence=0.0, source="apollo", candidates=[])
        candidate = PortCandidate(
            handle=handle,
            display_name=name,
            bio_preview="",
            score=0.9,
            rationale="apollo_match",
            source="apollo",
        )
        return DiscoveryResult(handle=None, confidence=0.9, source="apollo", candidates=[candidate])


class FakeApolloClient:
    """Test double — keyed by 'name|company' → handle."""

    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult:
        key = f"{name}|{company or ''}"
        handle = self._responses.get(key)
        if not handle:
            return DiscoveryResult(handle=None, confidence=0.0, source="apollo", candidates=[])
        candidate = PortCandidate(
            handle=handle,
            display_name=name,
            bio_preview="",
            score=0.9,
            rationale="fake_apollo",
            source="apollo",
        )
        return DiscoveryResult(handle=None, confidence=0.9, source="apollo", candidates=[candidate])
