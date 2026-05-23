# M4-Lite: 4-Tier Handle Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace X name search (noisy, ~10% reliable) with a 4-tier cascade — LinkedIn Contact Info scrape → Google CSE → Apollo enrichment → manual entry — dramatically improving handle discovery accuracy.

**Architecture:** A `Tier` Protocol + `run_tiers()` orchestrator sits between the port discover command and each data source. Tier 1 (LinkedIn contact info) auto-resolves without user review when it finds an explicit Twitter/X link. Tiers 2 and 3 produce candidates that land in the review queue with source annotated. Tier 4 marks persons as `needs_review` with an empty candidate list, surfaced in `port review` with a new `[t]ype handle` option. All HTTP clients are behind Protocol interfaces so tests never touch real APIs or browsers.

**Tech Stack:** Python 3.12 · `httpx` (async-capable, replaces requests) · Playwright (existing, Tier 1 only) · existing: PortState, PortCandidate, DataPaths, SyncLog

**Spec reference:** User-defined 4-tier priority: (1) LI contact info, (2) Google CSE `site:x.com`, (3) Apollo API optional, (4) unresolved → manual entry.

---

## Design constraints

1. **Tier 1 auto-resolves.** LinkedIn explicitly providing a Twitter/X URL = 100% confidence. No review queue needed. Goes straight to `port_state.queue()`.
2. **Tiers 2 + 3 go to review.** Confidence < 1.0 always surfaces to user.
3. **Tier 4 = empty candidates.** `port review` now has `[t]ype handle manually` option. Persons remain in `needs_review` until manually entered or skipped.
4. **Config-gated tiers.** Tier 2 requires `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` in env. Tier 3 requires `APOLLO_API_KEY`. Missing keys = tier silently skipped.
5. **`PortCandidate` gains `source: str = ""`** — backward-compatible (default empty for old records).
6. **`httpx` added to deps** — cleaner than `urllib.request` for sync HTTP in CLI tools.

---

## File Structure

**Create:**
```
src/socialgraph/port/discovery.py          # DiscoveryResult, Tier Protocol, run_tiers()
src/socialgraph/port/linkedin_scraper.py   # LinkedInContactInfoClient (Playwright)
src/socialgraph/port/web_search.py         # GoogleCSEClient + FakeGoogleCSEClient
src/socialgraph/port/enrichment.py         # ApolloClient + FakeApolloClient + Protocol
tests/unit/test_discovery.py
tests/unit/test_linkedin_scraper.py        # mocked Playwright
tests/unit/test_web_search.py
tests/unit/test_enrichment.py
```

**Modify:**
```
src/socialgraph/port/state.py              # PortCandidate: add source: str = ""
pyproject.toml                             # + httpx>=0.27
src/socialgraph/cli/port_discover_cmd.py   # use run_tiers(), read config for tier selection
src/socialgraph/cli/port_review_cmd.py     # add [t]ype handle option
config.yml.example                         # port.discovery + google/apollo sections
.env.example                               # GOOGLE_CSE_API_KEY, GOOGLE_CSE_ID, APOLLO_API_KEY
```

---

## Task 1: DiscoveryResult + Tier Protocol + run_tiers() + PortCandidate.source

**Files:**
- Modify: `src/socialgraph/port/state.py` — add `source: str = ""` to `PortCandidate`
- Create: `src/socialgraph/port/discovery.py`
- Create: `tests/unit/test_discovery.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_discovery.py`:
```python
from socialgraph.port.discovery import DiscoveryResult, Tier, run_tiers
from socialgraph.port.state import PortCandidate


def _candidate(handle: str, score: float = 0.9, source: str = "test") -> PortCandidate:
    return PortCandidate(
        handle=handle, display_name=handle, bio_preview="", score=score, rationale="", source=source
    )


class AlwaysHitTier:
    """Fake tier that always returns a resolved handle."""
    confidence = 1.0

    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(
            handle=f"@{name.lower().replace(' ', '_')}",
            confidence=1.0,
            source="always_hit",
            candidates=[],
        )


class AlwaysMissTier:
    confidence = 0.0

    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(handle=None, confidence=0.0, source="always_miss", candidates=[])


class CandidateTier:
    """Returns candidates but no definitive handle."""
    def discover(self, name: str, company: str | None, profile_url: str) -> DiscoveryResult:
        return DiscoveryResult(
            handle=None,
            confidence=0.7,
            source="candidate_tier",
            candidates=[_candidate("maybe_handle", score=0.7, source="candidate_tier")],
        )


def test_run_tiers_stops_at_first_auto_resolve():
    hit = AlwaysHitTier()
    miss = AlwaysMissTier()
    result = run_tiers("Alice Example", "Acme", "https://linkedin.com/in/alice", tiers=[hit, miss], auto_resolve_threshold=1.0)
    assert result.handle is not None
    assert result.source == "always_hit"


def test_run_tiers_falls_through_miss():
    miss = AlwaysMissTier()
    hit = AlwaysHitTier()
    result = run_tiers("Alice", None, "https://linkedin.com/in/alice", tiers=[miss, hit], auto_resolve_threshold=1.0)
    assert result.handle is not None
    assert result.source == "always_hit"


def test_run_tiers_returns_candidates_when_no_auto_resolve():
    miss = AlwaysMissTier()
    candidates_tier = CandidateTier()
    result = run_tiers("Alice", None, "https://linkedin.com/in/alice", tiers=[miss, candidates_tier], auto_resolve_threshold=1.0)
    assert result.handle is None
    assert len(result.candidates) == 1
    assert result.candidates[0].source == "candidate_tier"


def test_run_tiers_returns_empty_when_all_miss():
    result = run_tiers("Alice", None, "https://linkedin.com/in/alice", tiers=[AlwaysMissTier()], auto_resolve_threshold=1.0)
    assert result.handle is None
    assert result.candidates == []


def test_port_candidate_has_source_field():
    c = PortCandidate(handle="x", display_name="X", bio_preview="", score=0.9, rationale="")
    assert c.source == ""  # default
    c2 = PortCandidate(handle="x", display_name="X", bio_preview="", score=0.9, rationale="", source="google_cse")
    assert c2.source == "google_cse"
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_discovery.py -v
```
Expected: `ImportError: No module named 'socialgraph.port.discovery'` and failure on `source` field.

- [ ] **Step 3: Add `source` field to `PortCandidate`**

Read `src/socialgraph/port/state.py`. In the `PortCandidate` dataclass, add `source: str = ""` as the last field:

```python
@dataclass
class PortCandidate:
    handle: str
    display_name: str
    bio_preview: str
    score: float
    rationale: str
    source: str = ""   # which tier discovered this: li_contact_info | google_cse | apollo | manual
```

- [ ] **Step 4: Create `discovery.py`**

Create `src/socialgraph/port/discovery.py`:
```python
"""Multi-tier handle discovery orchestration.

Each Tier is a data source tried in order. The first tier that returns a
handle with confidence >= auto_resolve_threshold resolves immediately (no
user review). Tiers returning candidates below threshold accumulate results
for the review queue. All tiers exhausted → DiscoveryResult with no handle
and all collected candidates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from socialgraph.port.state import PortCandidate


@dataclass
class DiscoveryResult:
    """Output of a single tier or the full tier cascade."""

    handle: str | None
    confidence: float
    source: str
    candidates: list[PortCandidate] = field(default_factory=list)


@runtime_checkable
class Tier(Protocol):
    """A single data source for handle discovery."""

    def discover(
        self,
        name: str,
        company: str | None,
        profile_url: str,
    ) -> DiscoveryResult: ...


def run_tiers(
    name: str,
    company: str | None,
    profile_url: str,
    tiers: list[Tier],
    auto_resolve_threshold: float = 1.0,
) -> DiscoveryResult:
    """Run tiers in order; stop and auto-resolve at first high-confidence hit.

    Returns the merged DiscoveryResult: auto-resolved handle if any tier hits
    the threshold, otherwise all collected candidates from lower-confidence tiers.
    """
    all_candidates: list[PortCandidate] = []

    for tier in tiers:
        try:
            result = tier.discover(name, company, profile_url)
        except Exception:
            continue  # tier failure = skip, don't abort cascade

        if result.handle is not None and result.confidence >= auto_resolve_threshold:
            return result  # auto-resolve, stop cascade

        all_candidates.extend(result.candidates)

    return DiscoveryResult(
        handle=None,
        confidence=0.0,
        source="unresolved",
        candidates=all_candidates,
    )
```

- [ ] **Step 5: Run tests, verify pass**

```bash
.venv/bin/pytest tests/unit/test_discovery.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Run full suite, no regressions**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
```
Expected: 181 passed (no change in count — no new integration tests yet).

- [ ] **Step 7: Commit**

```bash
git add src/socialgraph/port/state.py src/socialgraph/port/discovery.py tests/unit/test_discovery.py
git commit -m "feat: DiscoveryResult/Tier protocol + run_tiers() + PortCandidate.source"
```

---

## Task 2: Add `httpx` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add httpx**

Read `pyproject.toml`. In `dependencies = [...]` add `"httpx>=0.27",`.

```bash
.venv/bin/pip install -e . -q
.venv/bin/python -c "import httpx; print(httpx.__version__)"
```
Expected: version string printed (e.g., `0.27.2`).

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add httpx dependency for tier HTTP clients"
```

---

## Task 3: LinkedIn Contact Info scraper (Tier 1)

**Files:**
- Create: `src/socialgraph/port/linkedin_scraper.py`
- Create: `tests/unit/test_linkedin_scraper.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_linkedin_scraper.py`:
```python
from unittest.mock import MagicMock, patch

from socialgraph.port.linkedin_scraper import LinkedInContactInfoClient


def _make_client(tmp_path) -> LinkedInContactInfoClient:
    return LinkedInContactInfoClient(profile_dir=tmp_path / "profiles" / "linkedin")


def test_discovers_twitter_link_in_contact_info(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        MagicMock(**{"get_attribute.return_value": "https://twitter.com/holger_seim"}),
    ]
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover(
            name="Holger Seim",
            company="Blinkist",
            profile_url="https://www.linkedin.com/in/holger-seim",
        )
    assert result.handle == "holger_seim"
    assert result.confidence == 1.0
    assert result.source == "li_contact_info"


def test_discovers_x_com_link(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = [
        MagicMock(**{"get_attribute.return_value": "https://x.com/alice_example"}),
    ]
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle == "alice_example"
    assert result.source == "li_contact_info"


def test_returns_no_handle_when_no_link(tmp_path):
    client = _make_client(tmp_path)
    mock_page = MagicMock()
    mock_page.query_selector_all.return_value = []
    with patch.object(client, "_get_page", return_value=mock_page):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle is None
    assert result.candidates == []


def test_handles_page_error_gracefully(tmp_path):
    client = _make_client(tmp_path)
    with patch.object(client, "_get_page", side_effect=Exception("nav failed")):
        result = client.discover("Alice", None, "https://www.linkedin.com/in/alice")
    assert result.handle is None


def test_extracts_handle_from_various_url_formats(tmp_path):
    from socialgraph.port.linkedin_scraper import _extract_handle_from_social_url
    assert _extract_handle_from_social_url("https://twitter.com/alice") == "alice"
    assert _extract_handle_from_social_url("https://x.com/alice_example/") == "alice_example"
    assert _extract_handle_from_social_url("https://x.com/i/user/12345") is None  # reserved path
    assert _extract_handle_from_social_url("https://linkedin.com/in/alice") is None  # wrong domain
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_linkedin_scraper.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `linkedin_scraper.py`**

Create `src/socialgraph/port/linkedin_scraper.py`:
```python
"""LinkedIn Contact Info Scraper — Tier 1 handle discovery.

Navigates to a LinkedIn profile's contact-info overlay and extracts any
Twitter/X URL the person has explicitly linked. This is the highest-confidence
signal: user-provided link = definitive handle, no review needed.

Requires an active LinkedIn Playwright session (data/profiles/linkedin/).
Run `socialgraph login linkedin` first.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

from socialgraph.port.browser import launch_persistent_browser
from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate

# Twitter/X reserved paths that are not user handles
_RESERVED_X_PATHS = {
    "home", "explore", "notifications", "messages", "bookmarks",
    "settings", "compose", "search", "i", "login", "signup",
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

    def __enter__(self) -> "LinkedInContactInfoClient":
        self._playwright_cm = launch_persistent_browser(self.profile_dir, headed=False)
        self._context = self._playwright_cm.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        if self._playwright_cm is not None:
            self._playwright_cm.__exit__(*exc)

    def _throttle(self) -> None:
        import random
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
            # Find all anchor hrefs in the contact-info overlay
            links = page.query_selector_all("a[href]")
            for link in links:
                href = link.get_attribute("href") or ""
                handle = _extract_handle_from_social_url(href)
                if handle:
                    try:
                        page.close()
                    except Exception:
                        pass
                    return DiscoveryResult(
                        handle=handle,
                        confidence=1.0,
                        source="li_contact_info",
                        candidates=[],
                    )
            try:
                page.close()
            except Exception:
                pass
        except Exception:
            pass
        return DiscoveryResult(handle=None, confidence=0.0, source="li_contact_info", candidates=[])
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv/bin/pytest tests/unit/test_linkedin_scraper.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/port/linkedin_scraper.py tests/unit/test_linkedin_scraper.py
git commit -m "feat: LinkedIn contact-info scraper (Tier 1)"
```

---

## Task 4: Google CSE search client (Tier 2)

**Files:**
- Create: `src/socialgraph/port/web_search.py`
- Create: `tests/unit/test_web_search.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_web_search.py`:
```python
from unittest.mock import MagicMock, patch

from socialgraph.port.web_search import FakeGoogleCSEClient, GoogleCSEClient, _parse_handles_from_cse_response


def test_fake_returns_seeded_results():
    fake = FakeGoogleCSEClient(
        responses={'"Alice Example" "Acme Co" site:x.com': ["alice_example"]},
    )
    result = fake.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "google_cse"


def test_fake_returns_empty_for_unknown():
    fake = FakeGoogleCSEClient(responses={})
    result = fake.discover("Unknown Person", None, "https://linkedin.com/in/unknown")
    assert result.handle is None
    assert result.candidates == []


def test_parse_handles_from_cse_response():
    response = {
        "items": [
            {"link": "https://x.com/alice_example", "title": "Alice Example (@alice_example)"},
            {"link": "https://twitter.com/bob_sample", "title": "Bob Sample"},
            {"link": "https://x.com/i/user/12345", "title": "reserved"},  # should skip
        ]
    }
    handles = _parse_handles_from_cse_response(response)
    assert handles == ["alice_example", "bob_sample"]


def test_google_cse_client_builds_correct_query():
    client = GoogleCSEClient(api_key="test_key", cse_id="test_cx")
    calls = []
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {"items": []})
        client.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
        assert mock_get.called
        url, kwargs = mock_get.call_args[0][0], mock_get.call_args[1]
        assert "alice" in url.lower() or "Alice" in kwargs.get("params", {}).get("q", "")


def test_google_cse_returns_no_results_on_api_error():
    client = GoogleCSEClient(api_key="bad_key", cse_id="cx")
    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=403, json=lambda: {"error": "forbidden"})
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.handle is None
    assert result.candidates == []
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_web_search.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `web_search.py`**

Create `src/socialgraph/port/web_search.py`:
```python
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
from dataclasses import dataclass

import httpx

from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate

_GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"
_RESERVED_X_PATHS = {
    "home", "explore", "notifications", "messages", "bookmarks",
    "settings", "compose", "search", "i", "login", "signup",
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
                params={"key": self.api_key, "cx": self.cse_id, "q": query, "num": self.num_results},
                timeout=10.0,
            )
            if resp.status_code != 200:
                return DiscoveryResult(handle=None, confidence=0.0, source="google_cse", candidates=[])
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
        return DiscoveryResult(handle=None, confidence=0.7, source="google_cse", candidates=candidates)


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
                handle=h, display_name=name, bio_preview="", score=0.85, rationale="fake", source="google_cse"
            )
            for h in handles
        ]
        return DiscoveryResult(handle=None, confidence=0.7 if handles else 0.0, source="google_cse", candidates=candidates)
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv/bin/pytest tests/unit/test_web_search.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/port/web_search.py tests/unit/test_web_search.py
git commit -m "feat: Google CSE search client (Tier 2)"
```

---

## Task 5: Apollo enrichment client (Tier 3, optional)

**Files:**
- Create: `src/socialgraph/port/enrichment.py`
- Create: `tests/unit/test_enrichment.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_enrichment.py`:
```python
from unittest.mock import MagicMock, patch

from socialgraph.port.enrichment import ApolloClient, FakeApolloClient


def test_fake_returns_seeded_handle():
    fake = FakeApolloClient(
        responses={"Alice Example|Acme Co": "alice_example"},
    )
    result = fake.discover("Alice Example", "Acme Co", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "apollo"


def test_fake_returns_empty_for_unknown():
    fake = FakeApolloClient(responses={})
    result = fake.discover("Unknown", None, "https://linkedin.com/in/unknown")
    assert result.handle is None
    assert result.candidates == []


def test_apollo_client_parses_twitter_url():
    client = ApolloClient(api_key="test_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"person": {"twitter_url": "https://twitter.com/alice_example"}},
        )
        result = client.discover("Alice Example", "Acme", "https://linkedin.com/in/alice")
    assert len(result.candidates) == 1
    assert result.candidates[0].handle == "alice_example"
    assert result.candidates[0].source == "apollo"


def test_apollo_client_returns_empty_on_no_twitter_url():
    client = ApolloClient(api_key="test_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"person": {"twitter_url": None}},
        )
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.candidates == []


def test_apollo_client_returns_empty_on_api_error():
    client = ApolloClient(api_key="bad_key")
    with patch("httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=401, json=lambda: {"error": "unauthorized"})
        result = client.discover("Alice", None, "https://linkedin.com/in/alice")
    assert result.candidates == []
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_enrichment.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement `enrichment.py`**

Create `src/socialgraph/port/enrichment.py`:
```python
"""Apollo.io enrichment client — Tier 3 handle discovery (optional).

Apollo's People Match API accepts name + company and returns social profiles
including Twitter handle. Free tier: 10,000 credits/month.
Requires APOLLO_API_KEY in environment.

Setup: https://app.apollo.io/ → Settings → API Keys
"""
from __future__ import annotations

import re

import httpx

from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate

_APOLLO_URL = "https://api.apollo.io/v1/people/match"
_RESERVED_X_PATHS = {
    "home", "explore", "notifications", "messages", "bookmarks",
    "settings", "compose", "search", "i", "login", "signup",
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
            handle=handle, display_name=name, bio_preview="", score=0.9, rationale="apollo_match", source="apollo"
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
            handle=handle, display_name=name, bio_preview="", score=0.9, rationale="fake_apollo", source="apollo"
        )
        return DiscoveryResult(handle=None, confidence=0.9, source="apollo", candidates=[candidate])
```

- [ ] **Step 4: Run tests, verify pass**

```bash
.venv/bin/pytest tests/unit/test_enrichment.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/port/enrichment.py tests/unit/test_enrichment.py
git commit -m "feat: Apollo enrichment client (Tier 3, optional)"
```

---

## Task 6: Refactor `port_discover_cmd.py` to use multi-tier pipeline

**Files:**
- Modify: `src/socialgraph/cli/port_discover_cmd.py`
- Modify: `tests/integration/test_port_discover_command.py`

This is the most complex task. Read `src/socialgraph/cli/port_discover_cmd.py` and `tests/integration/test_port_discover_command.py` BEFORE editing.

- [ ] **Step 1: Update the integration test**

In `tests/integration/test_port_discover_command.py`, replace ALL test content with:

```python
"""port discover tests — all tiers mocked via _make_tiers() injection."""
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate, PortState

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_li_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


class FakeTierWithCandidate:
    """Always returns a candidate for any person."""
    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(
            handle=None,
            confidence=0.7,
            source="fake",
            candidates=[PortCandidate(handle=f"{name.split()[0].lower()}_x", display_name=name, bio_preview="", score=0.7, rationale="", source="fake")],
        )


class FakeTierAutoResolve:
    """Always auto-resolves (confidence >= 1.0)."""
    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(
            handle=f"{name.split()[0].lower()}_auto",
            confidence=1.0,
            source="fake_auto",
            candidates=[],
        )


class FakeTierMiss:
    """Never finds anything."""
    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(handle=None, confidence=0.0, source="fake_miss", candidates=[])


def test_port_discover_tier1_auto_resolves(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[FakeTierAutoResolve()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0, result.stdout
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    # Auto-resolved → queued directly, no needs_review
    assert state.counts()["queued"] >= 1
    assert state.counts()["needs_review"] == 0


def test_port_discover_tier2_sends_to_review(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[FakeTierWithCandidate()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert state.counts()["needs_review"] >= 1
    assert state.counts()["queued"] == 0


def test_port_discover_all_miss_marks_unresolved(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[FakeTierMiss()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    # All unresolved — still in needs_review with empty candidates
    counts = state.counts()
    assert counts["needs_review"] + counts["rejected"] == 3


def test_port_discover_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["port", "discover", "--limit", "5"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()


def test_port_discover_skips_already_processed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[FakeTierWithCandidate()]):
        runner.invoke(app, ["port", "discover", "--limit", "3"])
        runner.invoke(app, ["port", "discover", "--limit", "3"])
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    seen_li = {e.linkedin_canonical_id for e in state.list_needs_review()}
    assert len(seen_li) <= 3
```

Run: `.venv/bin/pytest tests/integration/test_port_discover_command.py -v` — expect 5 failures (no `_make_tiers`).

- [ ] **Step 2: Rewrite `port_discover_cmd.py`**

Replace the ENTIRE content of `src/socialgraph/cli/port_discover_cmd.py`:

```python
"""`socialgraph port discover [--limit N]` — find X handles via 4-tier cascade.

Tier 1 (LinkedIn contact info): auto-resolves when explicit X link found.
Tier 2 (Google CSE): produces candidates for review queue.
Tier 3 (Apollo, optional): produces candidates if APOLLO_API_KEY set.
Tier 4: unresolved — lands in review queue with empty candidates for manual entry.

Tiers are loaded via _make_tiers(paths) which reads config/env. Tests
monkeypatch _make_tiers to inject fakes.
"""
from __future__ import annotations

import os
from pathlib import Path

import typer

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.paths import DataPaths
from socialgraph.port.discovery import DiscoveryResult, Tier, run_tiers
from socialgraph.port.state import PortState
from socialgraph.snapshot.store import SnapshotStore

_AUTO_RESOLVE_THRESHOLD = 1.0  # only Tier 1 (explicit link) auto-resolves


def _make_tiers(paths: DataPaths) -> list[Tier]:
    """Build tier list from env config. Tests monkeypatch this function."""
    tiers: list[Tier] = []

    # Tier 1: LinkedIn contact info (requires logged-in session)
    li_profile = paths.profiles / "linkedin"
    if li_profile.is_dir():
        from socialgraph.port.linkedin_scraper import LinkedInContactInfoClient
        tiers.append(LinkedInContactInfoClient(li_profile).__enter__())

    # Tier 2: Google CSE (requires API key)
    google_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    google_cx = os.environ.get("GOOGLE_CSE_ID", "")
    if google_key and google_cx:
        from socialgraph.port.web_search import GoogleCSEClient
        tiers.append(GoogleCSEClient(api_key=google_key, cse_id=google_cx))

    # Tier 3: Apollo (optional, requires API key)
    apollo_key = os.environ.get("APOLLO_API_KEY", "")
    if apollo_key:
        from socialgraph.port.enrichment import ApolloClient
        tiers.append(ApolloClient(api_key=apollo_key))

    return tiers


def _already_has_x_observation(canonical_id: str, log: CanonicalLog) -> bool:
    return any(rid.startswith("x#") for rid in log.raw_ids_for(canonical_id))


def port_discover_command(limit: int) -> None:
    paths = DataPaths(Path.cwd() / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is None:
        typer.echo("no graph yet — run: socialgraph import linkedin <path>")
        return

    log = CanonicalLog(paths.merge_decisions)
    port_state = PortState(paths.port_state)

    targets = []
    for person in snap.persons:
        platform_urls = person.attrs.get("platform_urls") or {}
        if "linkedin" not in platform_urls:
            continue
        if port_state.has_been_processed(person.canonical_id):
            continue
        if _already_has_x_observation(person.canonical_id, log):
            continue
        targets.append(person)
        if len(targets) >= limit:
            break

    if not targets:
        typer.echo("no LinkedIn-only persons to discover (all processed or already on X)")
        return

    tiers = _make_tiers(paths)
    if not tiers:
        typer.echo("no discovery tiers configured.")
        typer.echo("  Tier 1: run `socialgraph login linkedin` to enable contact-info scrape")
        typer.echo("  Tier 2: set GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID in .env")
        typer.echo("  Tier 3: set APOLLO_API_KEY in .env (optional)")
        return

    typer.echo(f"discovering X handles for {len(targets)} person(s) via {len(tiers)} tier(s)...")
    auto_resolved = 0
    queued_for_review = 0

    for target in targets:
        name = target.attrs.get("full_name", "")
        company = target.attrs.get("current_company")
        profile_url = (target.attrs.get("platform_urls") or {}).get("linkedin", "")

        result: DiscoveryResult = run_tiers(
            name, company, profile_url, tiers, auto_resolve_threshold=_AUTO_RESOLVE_THRESHOLD
        )

        if result.handle is not None:
            # Auto-resolved (Tier 1 found explicit link) — queue directly
            cid = port_state.record_discovered(
                linkedin_canonical_id=target.canonical_id, candidates=[]
            )
            port_state.resolve(cid, selected_handle=result.handle)
            port_state.queue(cid, x_profile_url=f"https://x.com/{result.handle}")
            auto_resolved += 1
            typer.echo(f"  {name} → @{result.handle} [auto] ({result.source})")
        else:
            # Candidates for review OR unresolved
            port_state.record_discovered(
                linkedin_canonical_id=target.canonical_id, candidates=result.candidates
            )
            queued_for_review += 1
            label = f"{len(result.candidates)} candidate(s)" if result.candidates else "unresolved"
            typer.echo(f"  {name} → {label}")

    typer.echo(f"\ndone. auto-resolved: {auto_resolved}, needs_review: {queued_for_review}")
    if queued_for_review:
        typer.echo("next: socialgraph port review")
```

- [ ] **Step 3: Run integration tests, verify pass**

```bash
.venv/bin/pytest tests/integration/test_port_discover_command.py -v
```
Expected: 5 passed.

- [ ] **Step 4: Run full suite**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
```
Expected: all pass (some tests from old port discover may now fail — fix them here).

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/cli/port_discover_cmd.py tests/integration/test_port_discover_command.py
git commit -m "feat: multi-tier discovery pipeline in port discover"
```

---

## Task 7: `port review` manual entry `[t]ype handle`

**Files:**
- Modify: `src/socialgraph/cli/port_review_cmd.py`
- Modify: `tests/integration/test_port_review_command.py`

- [ ] **Step 1: Add failing test**

Open `tests/integration/test_port_review_command.py`. Append at the end:

```python
def test_port_review_type_handle_manually(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    # Seed a review entry with NO candidates (unresolved)
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    state.record_discovered(linkedin_canonical_id="li-unresolved", candidates=[])
    # Input: 't' to type, then the handle, then quit
    result = runner.invoke(app, ["port", "review"], input="t\nmanual_handle\nq\n")
    assert result.exit_code == 0
    state = PortState(paths.port_state)
    queued = state.list_queued()
    assert len(queued) == 1
    assert queued[0].selected_handle == "manual_handle"
```

Run: `.venv/bin/pytest tests/integration/test_port_review_command.py::test_port_review_type_handle_manually -v` — expect fail.

- [ ] **Step 2: Update `port_review_cmd.py`**

Read `src/socialgraph/cli/port_review_cmd.py`. Update `port_review_command()`:

After the line `typer.echo("  pick: 1..N   skip: s   reject: n   quit: q\n")`, change to:
```python
    typer.echo("  pick: 1..N   type: t   skip: s   reject: n   quit: q\n")
```

In the choice handling block, add a `[t]` branch BEFORE the `try: idx = int(choice)` block:
```python
        if choice == "t":
            handle = typer.prompt("    Type X handle (without @)").strip().lstrip("@")
            if handle:
                state.resolve(entry.candidate_id, selected_handle=handle)
                state.queue(entry.candidate_id, x_profile_url=f"https://x.com/{handle}")
                typer.echo(f"  manually linked -> @{handle}, queued for follow")
            else:
                typer.echo("  empty handle, skipping")
            continue
```

The full updated `for entry in pending:` block becomes:
```python
    for entry in pending:
        typer.echo("─" * 60)
        typer.echo(f"  LinkedIn: {entry.linkedin_canonical_id[:8]}...")
        if entry.candidates:
            for idx, c in enumerate(entry.candidates, start=1):
                line = f"  [{idx}] @{c.handle}  ({c.display_name})  score={c.score:.2f}  [{c.source}]"
                if c.bio_preview:
                    line += f"  — {c.bio_preview[:80]}"
                typer.echo(line)
        else:
            typer.echo("  (no candidates found — use [t] to enter handle manually)")

        choice = typer.prompt("\n  Decision", default="s").strip().lower()

        if choice == "q":
            typer.echo("quit.")
            return
        if choice == "n":
            state.reject(entry.candidate_id)
            typer.echo("  rejected")
            continue
        if choice in ("s", ""):
            typer.echo("  skipped")
            continue
        if choice == "t":
            handle = typer.prompt("    Type X handle (without @)").strip().lstrip("@")
            if handle:
                state.resolve(entry.candidate_id, selected_handle=handle)
                state.queue(entry.candidate_id, x_profile_url=f"https://x.com/{handle}")
                typer.echo(f"  manually linked -> @{handle}, queued for follow")
            else:
                typer.echo("  empty handle, skipping")
            continue
        try:
            idx = int(choice) - 1
        except ValueError:
            typer.echo("  unknown input, skipping")
            continue
        if 0 <= idx < len(entry.candidates):
            handle = entry.candidates[idx].handle
            state.resolve(entry.candidate_id, selected_handle=handle)
            state.queue(entry.candidate_id, x_profile_url=f"https://x.com/{handle}")
            typer.echo(f"  resolved -> @{handle}, queued for follow")
        else:
            typer.echo("  out of range, skipping")
```

- [ ] **Step 3: Run tests, verify pass**

```bash
.venv/bin/pytest tests/integration/test_port_review_command.py -v
```
Expected: 5 passed (4 original + 1 new).

- [ ] **Step 4: Commit**

```bash
git add src/socialgraph/cli/port_review_cmd.py tests/integration/test_port_review_command.py
git commit -m "feat: port review [t]ype handle manually for unresolved persons"
```

---

## Task 8: Config updates

**Files:**
- Modify: `config.yml.example`
- Modify: `.env.example`

- [ ] **Step 1: Update `.env.example`**

Read `.env.example`. Add these lines at the end:

```
# Tier 2: Google Custom Search Engine (site:x.com for X handle discovery)
# Setup: https://programmablesearch.google.com/ → Create CSE → search entire web
# API key: https://console.cloud.google.com/ → APIs & Services → Credentials
GOOGLE_CSE_API_KEY=
GOOGLE_CSE_ID=

# Tier 3: Apollo enrichment (optional, 10K free credits/month)
# Setup: https://app.apollo.io/ → Settings → API Keys
APOLLO_API_KEY=
```

- [ ] **Step 2: Update `config.yml.example`**

Read `config.yml.example`. Add a `port:` section before the closing (at the end of the file):

```yaml
port:
  # Discovery tiers run in order until a handle is found.
  # Tier 1 (linkedin_contact_info): auto-resolves; requires `socialgraph login linkedin`
  # Tier 2 (google_cse): needs GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID in .env
  # Tier 3 (apollo): optional; needs APOLLO_API_KEY in .env
  # Tier 4 (unresolved): always active — `port review [t]` for manual entry
  discovery_tiers:
    - linkedin_contact_info
    - google_cse
    - apollo
```

- [ ] **Step 3: Commit**

```bash
git add .env.example config.yml.example
git commit -m "docs: document 4-tier discovery config in .env.example + config.yml.example"
```

---

## Task 9: Full suite green + lint + tag + push

- [ ] **Step 1: Run full suite**

```bash
.venv/bin/pytest -v 2>&1 | tail -5
```
Expected: all green. If any test fails due to port_discover_cmd refactor (old test references `_make_search_client`), fix now: old tests patching `_make_search_client` must be updated to patch `_make_tiers` instead.

- [ ] **Step 2: Lint + typecheck**

```bash
.venv/bin/ruff check src tests --fix && .venv/bin/ruff format src tests
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests
.venv/bin/pyright src 2>&1 | tail -3
```
Expected: clean. Note: httpx has type stubs; no issues expected.

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A && git commit -m "chore: lint + pyright clean for M4-lite"
```
Only commit if changes.

- [ ] **Step 4: Clean-room CLI smoke**

```bash
rm -rf data .env config.yml
socialgraph init
socialgraph import linkedin tests/fixtures/linkedin/connections_small.csv
socialgraph port discover --limit 5
```
Expected: "no discovery tiers configured" message (no env keys set) — correct, no browser open.

- [ ] **Step 5: Tag + push**

```bash
rm -rf data .env config.yml
git status   # clean
git tag -a m4-lite -m "M4-lite: 4-tier handle discovery (LI contact-info, Google CSE, Apollo, manual)"
git push origin main --tags
```

---

## Self-Review

**Spec coverage:**

| Requirement | Task |
|---|---|
| Tier 1: LinkedIn contact-info scrape, auto-resolve | T3 + T6 |
| Tier 2: Google CSE `site:x.com` | T4 + T6 |
| Tier 3: Enrichment API (Apollo), optional | T5 + T6 |
| Tier 4: Unresolved → manual entry `[t]` in review | T7 |
| `DiscoveryResult` + `Tier` Protocol + `run_tiers()` | T1 |
| `PortCandidate.source` field (visible in review UI) | T1 |
| Config-gated tiers (env keys drive which run) | T6 (`_make_tiers`) + T8 |
| `httpx` dep | T2 |
| Full suite + lint + tag | T9 |

**Placeholder scan:** None. All code complete.

**Type consistency:**
- `Tier` Protocol's `discover(name, company, profile_url) -> DiscoveryResult` used by: `LinkedInContactInfoClient`, `GoogleCSEClient`, `FakeGoogleCSEClient`, `ApolloClient`, `FakeApolloClient`, `AlwaysHitTier`, `AlwaysMissTier`, `CandidateTier`, `FakeTierAutoResolve`, `FakeTierWithCandidate`, `FakeTierMiss` — all match. ✓
- `run_tiers(name, company, profile_url, tiers, auto_resolve_threshold)` matches usage in `port_discover_cmd.py`. ✓
- `port_state.record_discovered(linkedin_canonical_id, candidates)` — same signature as Task 3 of the state plan. ✓
- `PortCandidate(handle, display_name, bio_preview, score, rationale, source="")` — source defaulted, backward-compatible. ✓
- `_make_tiers(paths: DataPaths)` → test patches `socialgraph.cli.port_discover_cmd._make_tiers`. ✓

**Key behavioural invariants:**
- Tier 1 auto-resolve: `result.handle is not None` AND `confidence >= 1.0` → `record_discovered(candidates=[])` + `resolve()` + `queue()` all called. Persons skip review queue.
- Tier 2/3 candidates: `result.handle is None` → `record_discovered(candidates=[...])` → lands in `needs_review`. Shown in `port review`.
- Tier 4 unresolved: all tiers miss → `record_discovered(candidates=[])` → lands in `needs_review` with empty list → `port review` shows `[t]` prompt.
