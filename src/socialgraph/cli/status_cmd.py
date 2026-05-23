"""`socialgraph status` — surface counts, last imports, recent errors.

M1 scope: counts only (parsed file counts per platform, last import timestamps,
last few error events from sync_log). Later milestones extend with graph
counts, pending merges, port queue state.
"""

from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore
from socialgraph.sync_log import SyncLog


def _count_jsonl_lines(p: Path) -> int:
    if not p.is_file():
        return 0
    with p.open("r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def status_command() -> None:
    data_root = Path.cwd() / "data"
    paths = DataPaths(data_root)

    if not paths.root.is_dir():
        typer.echo("no data/ dir. Run: socialgraph init")
        raise typer.Exit(code=0)

    parsed_files = sorted(paths.parsed.glob("*.jsonl")) if paths.parsed.is_dir() else []
    per_platform: dict[str, int] = {}
    for p in parsed_files:
        prefix = p.stem.split("_", 1)[0]  # "linkedin" | "x"
        per_platform[prefix] = per_platform.get(prefix, 0) + _count_jsonl_lines(p)

    typer.echo(f"parsed: {len(parsed_files)} files")
    for plat in sorted(per_platform):
        typer.echo(f"  {plat}: {per_platform[plat]} contacts")

    log = SyncLog(paths.sync_log)
    last_import_per_platform: dict[str, str] = {}
    for ev in log.iter():
        if ev.get("event") == "import.end":
            plat = ev.get("platform")
            ts = ev.get("ts")
            if isinstance(plat, str) and isinstance(ts, str):
                last_import_per_platform[plat] = ts

    typer.echo("\nlast import:")
    if not last_import_per_platform:
        typer.echo("  (none)")
    for plat in sorted(last_import_per_platform):
        typer.echo(f"  {plat}: {last_import_per_platform[plat]}")

    errors = log.last_errors(limit=3)
    if errors:
        typer.echo("\nrecent errors:")
        for e in errors:
            typer.echo(f"  {e.get('ts', '')} {e.get('event', '')}: {e.get('message', '')}")

    # Graph counts from latest snapshot
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is not None:
        typer.echo("\ngraph:")
        typer.echo(f"  {len(snap.persons)} persons")
        typer.echo(f"  {len(snap.companies)} companies")
        typer.echo(f"  {len(snap.edges)} edges")
    else:
        typer.echo("\ngraph: (none — run 'socialgraph import' to build)")
