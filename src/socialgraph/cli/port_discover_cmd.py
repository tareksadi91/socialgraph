"""`socialgraph port discover [--limit N]` — find X handles for LinkedIn contacts.

For each LinkedIn-only person (not yet processed):
  1. Build query: '"Full Name" Current Company'
  2. Call XSearchClient.search()
  3. Score results, keep top candidates above threshold
  4. Record in PortState

Skips already-processed persons. Stops at --limit.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.paths import DataPaths
from socialgraph.port.scoring import XSearchResult, score_candidate
from socialgraph.port.state import PortCandidate, PortState
from socialgraph.port.x_search import (
    PlaywrightXSearchClient,
    XSearchClient,
)
from socialgraph.snapshot.store import SnapshotStore

_MIN_SCORE = 0.4
_MAX_KEEP_CANDIDATES = 3


def _make_search_client(paths: DataPaths) -> XSearchClient:
    """Construct the production XSearchClient. Tests monkeypatch this function."""
    profile_dir = paths.profiles / "x"
    if not profile_dir.is_dir():
        raise FileNotFoundError(f"X profile not found at {profile_dir}. Run: socialgraph login x")
    return PlaywrightXSearchClient(profile_dir).__enter__()


def _build_query(name: str, company: str | None) -> str:
    if company:
        return f'"{name}" {company}'
    return f'"{name}"'


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
        typer.echo("no LinkedIn-only persons to discover (everyone is processed or has X)")
        return

    typer.echo(f"discovering X handles for {len(targets)} LinkedIn contact(s)...")

    client = _make_search_client(paths)
    try:
        for target in targets:
            name = target.attrs.get("full_name", "")
            company = target.attrs.get("current_company")
            query = _build_query(name, company)
            try:
                results = client.search(query)
            except Exception as exc:
                typer.secho(
                    f"  search failed for {name!r}: {exc}", err=True, fg=typer.colors.YELLOW
                )
                continue

            scored: list[tuple[float, str, XSearchResult]] = []
            for r in results:
                s, rationale = score_candidate(name, company, r)
                if s >= _MIN_SCORE:
                    scored.append((s, rationale, r))
            scored.sort(key=lambda t: t[0], reverse=True)
            top = scored[:_MAX_KEEP_CANDIDATES]

            candidates = [
                PortCandidate(
                    handle=r.handle,
                    display_name=r.display_name,
                    bio_preview=r.bio_preview,
                    score=s,
                    rationale=rationale,
                )
                for s, rationale, r in top
            ]
            port_state.record_discovered(
                linkedin_canonical_id=target.canonical_id,
                candidates=candidates,
            )
            label = f"({len(candidates)} candidate(s))" if candidates else "(no match)"
            typer.echo(f"  {name} {label}")
    finally:
        exit_method = getattr(client, "__exit__", None)
        if exit_method is not None:
            exit_method(None, None, None)

    counts = port_state.counts()
    typer.echo(f"\ndone. needs_review: {counts['needs_review']}, rejected: {counts['rejected']}")
    typer.echo("next: socialgraph port review")
