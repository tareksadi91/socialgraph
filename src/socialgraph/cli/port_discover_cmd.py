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
from contextlib import ExitStack
from pathlib import Path

import typer

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.paths import DataPaths
from socialgraph.port.discovery import DiscoveryResult, Tier, run_tiers
from socialgraph.port.state import PortState
from socialgraph.snapshot.store import SnapshotStore

_AUTO_RESOLVE_THRESHOLD = 1.0  # only Tier 1 (explicit link) auto-resolves


def _make_tiers(paths: DataPaths, stack: ExitStack) -> list[Tier]:
    """Build tier list from env config. Tier resources owned by the ExitStack.

    Tests monkeypatch this function to return a list of fake tiers (no stack
    interaction needed since fakes don't require cleanup).
    """
    tiers: list[Tier] = []

    # Tier 1: LinkedIn contact info (requires logged-in session)
    # Owned by ExitStack so the Playwright context is closed on command exit.
    li_profile = paths.profiles / "linkedin"
    if li_profile.is_dir():
        from socialgraph.port.linkedin_scraper import LinkedInContactInfoClient

        tiers.append(stack.enter_context(LinkedInContactInfoClient(li_profile)))

    # Tier 2: Google CSE (requires API key) — pure HTTP, no resources to clean up
    google_key = os.environ.get("GOOGLE_CSE_API_KEY", "")
    google_cx = os.environ.get("GOOGLE_CSE_ID", "")
    if google_key and google_cx:
        from socialgraph.port.web_search import GoogleCSEClient

        tiers.append(GoogleCSEClient(api_key=google_key, cse_id=google_cx))

    # Tier 3: Apollo (optional, requires API key) — pure HTTP
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

    # ExitStack owns all tier resources (Playwright contexts, etc.) — guaranteed
    # cleanup even if run_tiers or downstream raises.
    with ExitStack() as stack:
        tiers = _make_tiers(paths, stack)

        if not tiers:
            typer.echo("no discovery tiers configured.")
            typer.echo("  Tier 1: run `socialgraph login linkedin` to enable contact-info scrape")
            typer.echo("  Tier 2: set GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID in .env")
            typer.echo("  Tier 3: set APOLLO_API_KEY in .env (optional)")
            return

        typer.echo(
            f"discovering X handles for {len(targets)} person(s) via {len(tiers)} tier(s)..."
        )
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
                # Candidates for review OR unresolved — both land in needs_review
                port_state.record_discovered(
                    linkedin_canonical_id=target.canonical_id, candidates=result.candidates
                )
                queued_for_review += 1
                label = (
                    f"{len(result.candidates)} candidate(s)" if result.candidates else "unresolved"
                )
                typer.echo(f"  {name} → {label}")

        typer.echo(f"\ndone. auto-resolved: {auto_resolved}, needs_review: {queued_for_review}")
        if queued_for_review:
            typer.echo("next: socialgraph port review")
