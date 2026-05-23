"""Canonical filesystem layout under the data/ root."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    """Resolves all data/ subpaths from a single root.

    The data/ directory is the source of truth for the socialgraph project.
    Every persistent artifact (raw scrapes, parsed records, snapshots, logs,
    merge decisions, etc.) lives under DataPaths(root).<property>.
    """

    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def parsed(self) -> Path:
        return self.root / "parsed"

    @property
    def snapshots(self) -> Path:
        return self.root / "snapshots"

    @property
    def profiles(self) -> Path:
        return self.root / "profiles"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def viz(self) -> Path:
        return self.root / "viz"

    @property
    def lock_file(self) -> Path:
        return self.root / ".lock"

    @property
    def merge_decisions(self) -> Path:
        return self.root / "merge_decisions.jsonl"

    @property
    def pending_merges(self) -> Path:
        return self.root / "pending_merges.jsonl"

    @property
    def port_state(self) -> Path:
        return self.root / "port_state.jsonl"

    @property
    def sync_log(self) -> Path:
        return self.root / "sync_log.jsonl"

    @property
    def tos_ack(self) -> Path:
        return self.root / ".tos_ack"

    @property
    def no_llm_ack(self) -> Path:
        return self.root / ".no_llm_ack"

    def ensure(self) -> None:
        for d in (self.raw, self.parsed, self.snapshots, self.profiles, self.backups, self.cache, self.viz):
            d.mkdir(parents=True, exist_ok=True)

    def parsed_for_run(self, platform: str, source: str, run_id: str) -> Path:
        return self.parsed / f"{platform}_{source}_{run_id}.jsonl"

    def raw_run_dir(self, platform: str, run_id: str) -> Path:
        return self.raw / platform / run_id
