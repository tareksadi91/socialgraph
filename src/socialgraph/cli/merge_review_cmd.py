"""`socialgraph merge-review` — interactive cross-platform merge review.

Shows each pending candidate side-by-side and prompts:
  [y] confirm merge   [n] reject   [s] skip   [q] quit

Confirmed merges write to merge_decisions.jsonl and trigger a pipeline
rebuild to update the snapshot.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.identity.pending import PendingMergeQueue
from socialgraph.paths import DataPaths
from socialgraph.pipeline import run_pipeline


def merge_review_command() -> None:
    paths = DataPaths(Path.cwd() / "data")
    queue = PendingMergeQueue(paths.pending_merges)
    log = CanonicalLog(paths.merge_decisions)

    pending = queue.list_pending()
    if not pending:
        typer.echo("no pending merges — import both LinkedIn and X data to detect candidates")
        return

    typer.echo(f"{len(pending)} pending merge(s). Review each:\n")
    typer.echo("  [y] confirm  [n] reject  [s] skip  [q] quit\n")

    snapshot_needs_rebuild = False

    for merge in pending:
        li = merge.linkedin_attrs
        x_a = merge.x_attrs
        typer.echo("─" * 60)
        name = li.get("full_name", "?")
        title = li.get("current_title", "")
        company = li.get("current_company", "")
        typer.echo(f"  LinkedIn:  {name}  —  {title}  @  {company}")
        typer.echo(f"  X:         @{x_a.get('handle', '?')}  ({x_a.get('full_name', '?')})")
        typer.echo(f"  Signals:   {', '.join(merge.signals)}")
        li_short = merge.linkedin_canonical_id[:8]
        x_short = merge.x_canonical_id[:8]
        typer.echo(f"  IDs:       {li_short}… (LI)  <->  {x_short}… (X)")

        choice = typer.prompt("\n  Decision", default="s").strip().lower()

        if choice == "q":
            typer.echo("quit.")
            break
        elif choice == "y":
            x_raw_ids = log.raw_ids_for(merge.x_canonical_id)
            if not x_raw_ids:
                x_raw_ids = [merge.x_raw_id]
            log.merge(x_raw_ids, target_canonical_id=merge.linkedin_canonical_id)
            queue.confirm(merge.candidate_id)
            snapshot_needs_rebuild = True
            typer.echo(f"  merged -> {merge.linkedin_canonical_id[:8]}...")
        elif choice == "n":
            queue.reject(merge.candidate_id)
            typer.echo("  rejected")
        else:
            typer.echo("  skipped")

    if snapshot_needs_rebuild:
        typer.echo("\nrebuilding graph...")
        counts = run_pipeline(paths)
        typer.echo(f"graph updated: {counts['persons']} persons, {counts['companies']} companies")
