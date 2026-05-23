# M2: Identity + Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After `socialgraph import linkedin`, automatically resolve identity (dedup by profile URL slug), write a snapshot, load a queryable NetworkX graph, and expose `who-at` / `neighbors` CLI queries — making the user's 1654 real LinkedIn connections live and searchable.

**Architecture:** Three new packages (`identity/`, `snapshot/`, `graph/`) chain together: identity resolve assigns stable `canonical_id` UUIDs to RawContacts (persisted in `merge_decisions.jsonl`), snapshot serialises the resulting graph to an immutable JSONL file, and the NetworkX projection loads the latest snapshot into memory for queries. All packages are pure functions over their inputs; CLI commands wire them together. `import` now auto-runs the full pipeline after writing JSONL.

**Tech Stack:** Python 3.12 · Pydantic v2 · NetworkX · existing: Typer, DataPaths, SyncLog, RawContact, ExitCode

**Spec reference:** `docs/superpowers/specs/2026-05-23-socialgraph-design.md` §4.2–4.4, milestone M2.

---

## File Structure

**Create:**
```
src/socialgraph/runs.py                    # _new_run_id() shared utility
src/socialgraph/identity/__init__.py       # empty
src/socialgraph/identity/canonical.py      # CanonicalLog — UUID assignment + merge_decisions.jsonl
src/socialgraph/identity/merge_fields.py   # per-field priority rules → merged Person attrs
src/socialgraph/identity/resolve.py        # within-platform dedup → (canonical_id, RawContact) list
src/socialgraph/snapshot/__init__.py       # empty
src/socialgraph/snapshot/models.py         # SnapshotPerson, SnapshotCompany, SnapshotEdge, Snapshot
src/socialgraph/snapshot/build.py          # build_snapshot(contacts, canonical_map) → Snapshot
src/socialgraph/snapshot/store.py          # SnapshotStore: write (skip-if-empty) + read_latest
src/socialgraph/snapshot/diff.py           # diff(a, b) → SnapshotDiff
src/socialgraph/graph/__init__.py          # empty
src/socialgraph/graph/projection.py        # build_graph(Snapshot) → nx.MultiDiGraph
src/socialgraph/graph/query.py             # at_company(), neighbors_via_company()
src/socialgraph/cli/who_at_cmd.py          # socialgraph who-at "<company>"
src/socialgraph/cli/neighbors_cmd.py       # socialgraph neighbors <id>
src/socialgraph/cli/rebuild_cmd.py         # socialgraph rebuild
tests/unit/test_runs.py
tests/unit/test_canonical.py
tests/unit/test_merge_fields.py
tests/unit/test_resolve.py
tests/unit/test_snapshot_models.py
tests/unit/test_snapshot_build.py
tests/unit/test_snapshot_store.py
tests/unit/test_snapshot_diff.py
tests/unit/test_projection.py
tests/unit/test_query.py
tests/integration/test_pipeline_e2e.py     # import → resolve → snapshot → query
tests/integration/test_who_at_command.py
tests/integration/test_neighbors_command.py
tests/integration/test_rebuild_command.py
tests/e2e/test_m2_smoke.py                 # full M2 demo + round-trip sovereignty
```

**Modify:**
```
src/socialgraph/cli/import_cmd.py          # call pipeline after JSONL write
src/socialgraph/cli/status_cmd.py          # add graph counts from latest snapshot
src/socialgraph/cli/main.py                # register who-at, neighbors, rebuild
```

---

## Task 1: Runs module (extract _new_run_id)

**Files:**
- Create: `src/socialgraph/runs.py`
- Create: `tests/unit/test_runs.py`
- Modify: `src/socialgraph/cli/import_cmd.py` (remove local `_new_run_id`, import from runs)

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_runs.py`:
```python
import re
from socialgraph.runs import new_run_id


def test_new_run_id_format():
    rid = new_run_id()
    # format: YYYYMMDDTHHMMSSZ_<6hex>
    assert re.match(r"^\d{8}T\d{6}Z_[0-9a-f]{6}$", rid), f"bad run_id: {rid!r}"


def test_new_run_id_unique():
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50  # UUID hex suffix ensures uniqueness
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_runs.py -v
```
Expected: `ImportError: No module named 'socialgraph.runs'`

- [ ] **Step 3: Implement `runs.py`**

Create `src/socialgraph/runs.py`:
```python
"""Shared run-ID generator for all ingest operations."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime


def new_run_id() -> str:
    """Return a UTC-timestamped, collision-resistant run identifier.

    Format: YYYYMMDDTHHMMSSZ_<6-hex-chars>
    Used as the base for all parsed/ JSONL filenames via DataPaths.parsed_for_run().
    DataPaths.parsed_for_run() prepends {platform}_{source}_ — keep this bare.
    """
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{ts}_{uuid.uuid4().hex[:6]}"
```

- [ ] **Step 4: Update `import_cmd.py`**

In `src/socialgraph/cli/import_cmd.py`:

Remove the old `_new_run_id` function and import. Add at the top with other imports:
```python
from socialgraph.runs import new_run_id
```

Replace `run_id = _new_run_id()` with `run_id = new_run_id()`.

- [ ] **Step 5: Run tests, verify pass**

```bash
.venv/bin/pytest tests/unit/test_runs.py tests/integration/test_import_pipeline.py -v
```
Expected: `test_runs.py` 2 passed, `test_import_pipeline.py` 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/runs.py tests/unit/test_runs.py src/socialgraph/cli/import_cmd.py
git commit -m "refactor: extract new_run_id() to runs module"
```

---

## Task 2: Canonical ID module

**Files:**
- Create: `src/socialgraph/identity/__init__.py`
- Create: `src/socialgraph/identity/canonical.py`
- Create: `tests/unit/test_canonical.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_canonical.py`:
```python
from pathlib import Path
from socialgraph.identity.canonical import CanonicalLog


def test_get_or_create_assigns_uuid(tmp_path: Path):
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    cid = log.get_or_create("linkedin#alice-example")
    assert len(cid) == 36  # UUID4 format
    assert "-" in cid


def test_get_or_create_idempotent(tmp_path: Path):
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    c1 = log.get_or_create("linkedin#alice-example")
    c2 = log.get_or_create("linkedin#alice-example")
    assert c1 == c2


def test_get_or_create_writes_log(tmp_path: Path):
    p = tmp_path / "merge_decisions.jsonl"
    log = CanonicalLog(p)
    log.get_or_create("linkedin#alice")
    lines = p.read_text().splitlines()
    assert len(lines) == 1
    import json
    entry = json.loads(lines[0])
    assert entry["event"] == "create"
    assert entry["raw_id"] == "linkedin#alice"
    assert "canonical_id" in entry
    assert "ts" in entry


def test_reload_replays_from_log(tmp_path: Path):
    p = tmp_path / "merge_decisions.jsonl"
    log1 = CanonicalLog(p)
    cid = log1.get_or_create("linkedin#alice")
    # fresh instance replays from same file
    log2 = CanonicalLog(p)
    assert log2.get_or_create("linkedin#alice") == cid
    # only one create event (not two)
    assert len(p.read_text().splitlines()) == 1


def test_get_all_returns_mapping(tmp_path: Path):
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    c1 = log.get_or_create("linkedin#alice")
    c2 = log.get_or_create("linkedin#bob")
    mapping = log.get_all()
    assert mapping["linkedin#alice"] == c1
    assert mapping["linkedin#bob"] == c2
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_canonical.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create empty `__init__.py`**

```bash
touch src/socialgraph/identity/__init__.py
```

- [ ] **Step 4: Implement `canonical.py`**

Create `src/socialgraph/identity/canonical.py`:
```python
"""Canonical ID assignment and merge_decisions.jsonl log.

Every RawContact gets a stable UUID canonical_id on first observation.
All assignments are written as append-only events to merge_decisions.jsonl
so canonical_ids are reproducible via log replay (sovereignty guarantee).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path


class CanonicalLog:
    """Wraps merge_decisions.jsonl: assigns canonical_ids and replays history.

    The log is append-only. On construction, existing entries are replayed
    into an in-memory cache so every get_or_create() call is O(1) after init.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self._cache: dict[str, str] = {}  # raw_id → canonical_id
        self._replay()

    def _replay(self) -> None:
        if not self.path.is_file():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                event = entry.get("event")
                if event == "create":
                    self._cache[entry["raw_id"]] = entry["canonical_id"]
                elif event == "merge":
                    for rid in entry.get("raw_ids", []):
                        self._cache[rid] = entry["canonical_id"]
                elif event == "unmerge":
                    for rid, cid in entry.get("reassignments", {}).items():
                        self._cache[rid] = cid

    def get_or_create(self, raw_id: str) -> str:
        """Return existing canonical_id or assign a new UUID and persist it."""
        if raw_id in self._cache:
            return self._cache[raw_id]
        cid = str(uuid.uuid4())
        self._cache[raw_id] = cid
        self._append({"event": "create", "canonical_id": cid, "raw_id": raw_id})
        return cid

    def get_all(self) -> dict[str, str]:
        """Return snapshot of current raw_id → canonical_id mapping."""
        return dict(self._cache)

    def _append(self, record: dict) -> None:
        record["ts"] = datetime.now(UTC).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())
```

- [ ] **Step 5: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_canonical.py -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/identity/__init__.py src/socialgraph/identity/canonical.py tests/unit/test_canonical.py
git commit -m "feat: canonical ID module with merge_decisions.jsonl"
```

---

## Task 3: Field merge rules

**Files:**
- Create: `src/socialgraph/identity/merge_fields.py`
- Create: `tests/unit/test_merge_fields.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_merge_fields.py`:
```python
from datetime import UTC, datetime
from socialgraph.schema.raw_contact import RawContact
from socialgraph.identity.merge_fields import merge_person_attrs, extract_company_name


def _contact(**kw) -> RawContact:
    base = {
        "raw_id": "r#slug",
        "platform": "linkedin",
        "source": "import",
        "platform_native_id": "slug",
        "profile_url": "https://linkedin.com/in/slug",
        "observed_at": datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC),
        "run_id": "run1",
        "full_name": "Test Person",
    }
    base.update(kw)
    return RawContact(**base)


def test_merge_single_contact():
    c = _contact(first_name="Alice", last_name="Smith", current_company="Acme", current_title="Founder")
    attrs = merge_person_attrs([c])
    assert attrs["full_name"] == "Alice Smith"
    assert attrs["current_company"] == "Acme"
    assert attrs["current_title"] == "Founder"
    assert attrs["platform_urls"] == {"linkedin": "https://linkedin.com/in/slug"}


def test_merge_prefers_scrape_over_import():
    import_ = _contact(full_name="A B", current_company="Old Co", source="import")
    scrape = _contact(full_name="A B", current_company="New Co", source="scrape")
    attrs = merge_person_attrs([import_, scrape])
    # scrape > import for company (spec §4.2 field priority)
    assert attrs["current_company"] == "New Co"


def test_merge_latest_non_null_wins_for_title():
    c1 = _contact(current_title=None, observed_at=datetime(2026, 1, 1, tzinfo=UTC))
    c2 = _contact(current_title="CEO", observed_at=datetime(2026, 5, 1, tzinfo=UTC))
    attrs = merge_person_attrs([c1, c2])
    assert attrs["current_title"] == "CEO"


def test_extract_company_name_returns_none_when_missing():
    c = _contact(current_company=None)
    assert extract_company_name([c]) is None


def test_extract_company_name_strips_whitespace():
    c = _contact(current_company="  Acme Corp  ")
    assert extract_company_name([c]) == "Acme Corp"
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_merge_fields.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `merge_fields.py`**

Create `src/socialgraph/identity/merge_fields.py`:
```python
"""Per-field merge rules for combining multiple RawContact observations.

When a Person is observed more than once (e.g., import + scrape), fields are
merged by priority (spec §4.2):

    scrape > import   for company, title, location, headline, bio
    latest non-null   as the tiebreaker
    union             for list fields (topics)

Only fields present in the first milestone import are implemented here.
Scrape-only fields (headline, bio, location_*, photo_url) are carried through
verbatim from whichever observation has them.
"""
from __future__ import annotations

from typing import Any

from socialgraph.schema.raw_contact import RawContact

# Higher = higher priority. "scrape" > "import" per spec.
_SOURCE_PRIORITY = {"import": 0, "scrape": 1}


def merge_person_attrs(contacts: list[RawContact]) -> dict[str, Any]:
    """Merge multiple observations of the same person into one attrs dict.

    Returns a plain dict suitable for SnapshotPerson.attrs.
    """
    # Sort by (source_priority asc, observed_at asc) so highest-priority
    # and most-recent value wins when we overwrite.
    sorted_contacts = sorted(
        contacts,
        key=lambda c: (_SOURCE_PRIORITY.get(c.source, 0), c.observed_at),
    )

    attrs: dict[str, Any] = {}

    scalar_fields = [
        "full_name", "first_name", "last_name", "display_name",
        "handle", "email", "headline", "bio",
        "location_raw", "location_city", "location_country",
        "photo_url", "language", "current_company", "current_company_url",
        "current_title", "industry", "seniority", "function",
        "follower_count", "following_count", "mutual_count",
    ]
    list_fields = ["topics", "mutual_names_sample"]

    for contact in sorted_contacts:
        for field in scalar_fields:
            val = getattr(contact, field, None)
            if val is not None:
                attrs[field] = val
        for field in list_fields:
            val = getattr(contact, field, None) or []
            existing = attrs.get(field, [])
            attrs[field] = list(dict.fromkeys(existing + val))  # union, order-preserving

    # connected_on = earliest observed (first time you connected)
    dates = [c.connected_on for c in contacts if c.connected_on]
    if dates:
        attrs["connected_on"] = min(dates).isoformat()

    # platform_urls: aggregated per-platform profile URLs
    urls: dict[str, str] = attrs.get("platform_urls", {})
    for c in contacts:
        if c.profile_url:
            urls[c.platform] = c.profile_url
    attrs["platform_urls"] = urls

    return attrs


def extract_company_name(contacts: list[RawContact]) -> str | None:
    """Return the most recent non-null current_company across contacts."""
    sorted_contacts = sorted(
        contacts,
        key=lambda c: (_SOURCE_PRIORITY.get(c.source, 0), c.observed_at),
        reverse=True,
    )
    for c in sorted_contacts:
        if c.current_company and c.current_company.strip():
            return c.current_company.strip()
    return None
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_merge_fields.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/identity/merge_fields.py tests/unit/test_merge_fields.py
git commit -m "feat: field merge rules for multi-observation persons"
```

---

## Task 4: Within-platform identity resolve

**Files:**
- Create: `src/socialgraph/identity/resolve.py`
- Create: `tests/unit/test_resolve.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_resolve.py`:
```python
from datetime import UTC, datetime
from pathlib import Path
from socialgraph.identity.canonical import CanonicalLog
from socialgraph.identity.resolve import within_platform_resolve
from socialgraph.schema.raw_contact import RawContact


def _contact(slug: str, platform: str = "linkedin", **kw) -> RawContact:
    return RawContact(
        raw_id=f"run1#{slug}",
        platform=platform,
        source="import",
        platform_native_id=slug,
        profile_url=f"https://linkedin.com/in/{slug}",
        observed_at=datetime(2026, 5, 23, tzinfo=UTC),
        run_id="run1",
        full_name=slug.replace("-", " ").title(),
        **kw,
    )


def test_resolve_assigns_canonical_ids(tmp_path: Path):
    contacts = [_contact("alice"), _contact("bob"), _contact("carol")]
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve(contacts, log)
    assert len(result) == 3
    canonical_ids = {cid for cid, _ in result}
    assert len(canonical_ids) == 3  # one per unique slug


def test_resolve_same_slug_same_canonical_id(tmp_path: Path):
    # Two observations of the same person
    c1 = _contact("alice", run_id="run1")
    c2 = RawContact(
        raw_id="run2#alice",
        platform="linkedin",
        source="scrape",
        platform_native_id="alice",
        profile_url="https://linkedin.com/in/alice",
        observed_at=datetime(2026, 5, 24, tzinfo=UTC),
        run_id="run2",
        full_name="Alice",
    )
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve([c1, c2], log)
    cids = [cid for cid, _ in result]
    assert cids[0] == cids[1]  # same person, same canonical_id


def test_resolve_stable_across_calls(tmp_path: Path):
    p = tmp_path / "merge_decisions.jsonl"
    contacts = [_contact("alice"), _contact("bob")]
    log1 = CanonicalLog(p)
    result1 = within_platform_resolve(contacts, log1)
    log2 = CanonicalLog(p)
    result2 = within_platform_resolve(contacts, log2)
    assert [cid for cid, _ in result1] == [cid for cid, _ in result2]


def test_resolve_returns_one_entry_per_contact(tmp_path: Path):
    contacts = [_contact("alice"), _contact("alice"), _contact("bob")]
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    result = within_platform_resolve(contacts, log)
    # returns one entry per input contact (not one per unique person)
    assert len(result) == 3
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_resolve.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `resolve.py`**

Create `src/socialgraph/identity/resolve.py`:
```python
"""Within-platform identity resolution.

Groups RawContact records by platform_native_id and assigns stable
canonical_ids via CanonicalLog. Same platform_native_id = same person.
Cross-platform merge is handled in M3 (conservative + review queue).
"""
from __future__ import annotations

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.schema.raw_contact import RawContact


def within_platform_resolve(
    contacts: list[RawContact],
    log: CanonicalLog,
) -> list[tuple[str, RawContact]]:
    """Assign canonical_ids to a flat list of RawContacts.

    Returns one (canonical_id, contact) tuple per input contact, in the
    same order. Contacts sharing a platform_native_id get the same
    canonical_id (they are the same person observed multiple times).
    """
    result: list[tuple[str, RawContact]] = []
    for contact in contacts:
        # raw_id key: {platform}#{platform_native_id} — unique across platforms
        raw_key = f"{contact.platform}#{contact.platform_native_id}"
        cid = log.get_or_create(raw_key)
        result.append((cid, contact))
    return result
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_resolve.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/identity/resolve.py tests/unit/test_resolve.py
git commit -m "feat: within-platform identity resolve"
```

---

## Task 5: Snapshot models

**Files:**
- Create: `src/socialgraph/snapshot/__init__.py`
- Create: `src/socialgraph/snapshot/models.py`
- Create: `tests/unit/test_snapshot_models.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_snapshot_models.py`:
```python
import json
from socialgraph.snapshot.models import SnapshotPerson, SnapshotCompany, SnapshotEdge, Snapshot


def test_snapshot_person_round_trip():
    p = SnapshotPerson(
        canonical_id="uuid-1",
        attrs={"full_name": "Alice", "current_company": "Acme"},
        observations=["run1#alice"],
    )
    line = p.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "node"
    assert parsed["node_type"] == "Person"
    p2 = SnapshotPerson.from_jsonl_dict(parsed)
    assert p2.canonical_id == "uuid-1"
    assert p2.attrs["full_name"] == "Alice"


def test_snapshot_company_round_trip():
    c = SnapshotCompany(canonical_id="co-1", name="Acme Corp")
    line = c.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "node"
    assert parsed["node_type"] == "Company"
    c2 = SnapshotCompany.from_jsonl_dict(parsed)
    assert c2.name == "Acme Corp"


def test_snapshot_edge_round_trip():
    e = SnapshotEdge(
        edge_type="WORKS_AT",
        src="uuid-1",
        dst="co-1",
        attrs={"title": "Founder"},
    )
    line = e.to_jsonl_line()
    parsed = json.loads(line)
    assert parsed["type"] == "edge"
    assert parsed["edge_type"] == "WORKS_AT"
    e2 = SnapshotEdge.from_jsonl_dict(parsed)
    assert e2.src == "uuid-1"
    assert e2.dst == "co-1"


def test_snapshot_is_empty():
    s = Snapshot(persons=[], companies=[], edges=[])
    assert s.is_empty()
    s2 = Snapshot(persons=[SnapshotPerson(canonical_id="x", attrs={}, observations=[])], companies=[], edges=[])
    assert not s2.is_empty()
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_snapshot_models.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Create `__init__.py`**

```bash
touch src/socialgraph/snapshot/__init__.py
```

- [ ] **Step 4: Implement `models.py`**

Create `src/socialgraph/snapshot/models.py`:
```python
"""Snapshot data model — immutable JSONL records for Persons, Companies, Edges.

Each line in a snapshot file has a discriminator:
  {"type": "node", "node_type": "Person", "canonical_id": ..., "attrs": {...}, "observations": [...]}
  {"type": "node", "node_type": "Company", "canonical_id": ..., "name": ..., "attrs": {...}}
  {"type": "edge", "edge_type": "WORKS_AT", "src": ..., "dst": ..., "attrs": {...}}
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SnapshotPerson:
    canonical_id: str
    attrs: dict[str, Any]
    observations: list[str]  # raw_ids that contributed

    def to_jsonl_line(self) -> str:
        return json.dumps({
            "type": "node",
            "node_type": "Person",
            "canonical_id": self.canonical_id,
            "attrs": self.attrs,
            "observations": self.observations,
        })

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> "SnapshotPerson":
        return cls(
            canonical_id=d["canonical_id"],
            attrs=d.get("attrs", {}),
            observations=d.get("observations", []),
        )


@dataclass
class SnapshotCompany:
    canonical_id: str
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_jsonl_line(self) -> str:
        return json.dumps({
            "type": "node",
            "node_type": "Company",
            "canonical_id": self.canonical_id,
            "name": self.name,
            "attrs": self.attrs,
        })

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> "SnapshotCompany":
        return cls(
            canonical_id=d["canonical_id"],
            name=d.get("name", ""),
            attrs=d.get("attrs", {}),
        )


@dataclass
class SnapshotEdge:
    edge_type: str
    src: str
    dst: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_jsonl_line(self) -> str:
        return json.dumps({
            "type": "edge",
            "edge_type": self.edge_type,
            "src": self.src,
            "dst": self.dst,
            "attrs": self.attrs,
        })

    @classmethod
    def from_jsonl_dict(cls, d: dict) -> "SnapshotEdge":
        return cls(
            edge_type=d["edge_type"],
            src=d["src"],
            dst=d["dst"],
            attrs=d.get("attrs", {}),
        )


@dataclass
class Snapshot:
    persons: list[SnapshotPerson]
    companies: list[SnapshotCompany]
    edges: list[SnapshotEdge]

    def is_empty(self) -> bool:
        return not self.persons and not self.companies and not self.edges

    def to_jsonl_lines(self) -> list[str]:
        lines: list[str] = []
        lines.extend(p.to_jsonl_line() for p in self.persons)
        lines.extend(c.to_jsonl_line() for c in self.companies)
        lines.extend(e.to_jsonl_line() for e in self.edges)
        return lines

    @classmethod
    def from_jsonl_lines(cls, lines: list[str]) -> "Snapshot":
        persons, companies, edges = [], [], []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") == "node":
                if d.get("node_type") == "Person":
                    persons.append(SnapshotPerson.from_jsonl_dict(d))
                elif d.get("node_type") == "Company":
                    companies.append(SnapshotCompany.from_jsonl_dict(d))
            elif d.get("type") == "edge":
                edges.append(SnapshotEdge.from_jsonl_dict(d))
        return cls(persons=persons, companies=companies, edges=edges)
```

- [ ] **Step 5: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_snapshot_models.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/snapshot/__init__.py src/socialgraph/snapshot/models.py tests/unit/test_snapshot_models.py
git commit -m "feat: snapshot JSONL models (Person, Company, Edge)"
```

---

## Task 6: Build snapshot from RawContacts

**Files:**
- Create: `src/socialgraph/snapshot/build.py`
- Create: `tests/unit/test_snapshot_build.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_snapshot_build.py`:
```python
from datetime import UTC, datetime
from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.build import build_snapshot


def _contact(slug: str, company: str | None = None, title: str | None = None) -> RawContact:
    return RawContact(
        raw_id=f"r#{slug}",
        platform="linkedin",
        source="import",
        platform_native_id=slug,
        profile_url=f"https://linkedin.com/in/{slug}",
        observed_at=datetime(2026, 5, 23, tzinfo=UTC),
        run_id="run1",
        full_name=slug.title(),
        current_company=company,
        current_title=title,
    )


def test_build_creates_person_nodes():
    contacts = [
        ("cid-1", _contact("alice", company="Acme")),
        ("cid-2", _contact("bob", company="Beta")),
    ]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 2
    assert {p.canonical_id for p in snap.persons} == {"cid-1", "cid-2"}


def test_build_creates_company_nodes():
    contacts = [
        ("cid-1", _contact("alice", company="Acme")),
        ("cid-2", _contact("bob", company="Acme")),  # same company
        ("cid-3", _contact("carol", company="Beta")),
    ]
    snap = build_snapshot(contacts)
    company_names = {c.name for c in snap.companies}
    assert company_names == {"Acme", "Beta"}


def test_build_deduplicates_companies():
    contacts = [("cid-1", _contact("alice", company="Acme")),
                ("cid-2", _contact("bob", company="Acme"))]
    snap = build_snapshot(contacts)
    assert len(snap.companies) == 1


def test_build_creates_works_at_edges():
    contacts = [("cid-1", _contact("alice", company="Acme", title="Founder"))]
    snap = build_snapshot(contacts)
    works_at = [e for e in snap.edges if e.edge_type == "WORKS_AT"]
    assert len(works_at) == 1
    assert works_at[0].src == "cid-1"
    assert works_at[0].attrs.get("title") == "Founder"


def test_build_skips_persons_without_company():
    contacts = [("cid-1", _contact("alice", company=None))]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 1
    assert len(snap.companies) == 0
    assert len(snap.edges) == 0


def test_build_groups_multiple_observations():
    # same canonical_id, two observations → one merged person
    c1 = _contact("alice", company="OldCo")
    c2 = RawContact(
        raw_id="r2#alice",
        platform="linkedin",
        source="scrape",
        platform_native_id="alice",
        profile_url="https://linkedin.com/in/alice",
        observed_at=datetime(2026, 5, 24, tzinfo=UTC),
        run_id="run2",
        full_name="Alice",
        current_company="NewCo",
    )
    contacts = [("cid-1", c1), ("cid-1", c2)]
    snap = build_snapshot(contacts)
    assert len(snap.persons) == 1  # merged, not duplicated
    person = snap.persons[0]
    assert person.attrs["current_company"] == "NewCo"  # scrape > import
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_snapshot_build.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `build.py`**

Create `src/socialgraph/snapshot/build.py`:
```python
"""Build a Snapshot from a resolved (canonical_id, RawContact) list.

Groups contacts by canonical_id, merges attributes via field-priority rules,
derives Company nodes from current_company, and creates WORKS_AT edges.
"""
from __future__ import annotations

import re
from collections import defaultdict

from socialgraph.identity.merge_fields import extract_company_name, merge_person_attrs
from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.models import Snapshot, SnapshotCompany, SnapshotEdge, SnapshotPerson


def _company_slug(name: str) -> str:
    """Derive a stable canonical_id for a company from its name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    return f"company-{slug}"


def build_snapshot(resolved: list[tuple[str, RawContact]]) -> Snapshot:
    """Build a Snapshot from resolved (canonical_id, RawContact) pairs.

    resolved: output of within_platform_resolve() — one pair per raw observation.
    """
    # Group observations by canonical_id
    by_cid: dict[str, list[RawContact]] = defaultdict(list)
    for cid, contact in resolved:
        by_cid[cid].append(contact)

    persons: list[SnapshotPerson] = []
    companies: dict[str, SnapshotCompany] = {}  # slug → SnapshotCompany
    edges: list[SnapshotEdge] = []

    for cid, contacts in by_cid.items():
        attrs = merge_person_attrs(contacts)
        observations = [c.raw_id for c in contacts]
        persons.append(SnapshotPerson(canonical_id=cid, attrs=attrs, observations=observations))

        company_name = extract_company_name(contacts)
        if company_name:
            slug = _company_slug(company_name)
            if slug not in companies:
                companies[slug] = SnapshotCompany(canonical_id=slug, name=company_name)
            edge_attrs: dict[str, object] = {}
            title = attrs.get("current_title")
            if title:
                edge_attrs["title"] = title
            edges.append(SnapshotEdge(
                edge_type="WORKS_AT",
                src=cid,
                dst=slug,
                attrs=edge_attrs,
            ))

    return Snapshot(
        persons=persons,
        companies=list(companies.values()),
        edges=edges,
    )
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_snapshot_build.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/snapshot/build.py tests/unit/test_snapshot_build.py
git commit -m "feat: build snapshot from resolved contacts"
```

---

## Task 7: Snapshot diff

**Files:**
- Create: `src/socialgraph/snapshot/diff.py`
- Create: `tests/unit/test_snapshot_diff.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_snapshot_diff.py`:
```python
from socialgraph.snapshot.models import Snapshot, SnapshotPerson, SnapshotCompany, SnapshotEdge
from socialgraph.snapshot.diff import snapshot_diff, SnapshotDiff


def _person(cid: str, name: str = "Test", company: str = "Co") -> SnapshotPerson:
    return SnapshotPerson(canonical_id=cid, attrs={"full_name": name, "current_company": company}, observations=[])


def _company(cid: str, name: str = "Co") -> SnapshotCompany:
    return SnapshotCompany(canonical_id=cid, name=name)


def _edge(src: str, dst: str, etype: str = "WORKS_AT") -> SnapshotEdge:
    return SnapshotEdge(edge_type=etype, src=src, dst=dst, attrs={})


def test_diff_empty_vs_empty():
    d = snapshot_diff(Snapshot([], [], []), Snapshot([], [], []))
    assert isinstance(d, SnapshotDiff)
    assert d.is_empty()


def test_diff_detects_added_person():
    a = Snapshot([], [], [])
    b = Snapshot([_person("p1", "Alice")], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.added_persons
    assert d.removed_persons == set()


def test_diff_detects_removed_person():
    a = Snapshot([_person("p1")], [], [])
    b = Snapshot([], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.removed_persons
    assert d.added_persons == set()


def test_diff_detects_changed_attr():
    a = Snapshot([_person("p1", company="Old Co")], [], [])
    b = Snapshot([_person("p1", company="New Co")], [], [])
    d = snapshot_diff(a, b)
    assert "p1" in d.changed_persons
    change = d.changed_persons["p1"]
    assert change["current_company"] == ("Old Co", "New Co")


def test_diff_no_change_same_snapshot():
    snap = Snapshot([_person("p1")], [_company("co1")], [_edge("p1", "co1")])
    d = snapshot_diff(snap, snap)
    assert d.is_empty()
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_snapshot_diff.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `diff.py`**

Create `src/socialgraph/snapshot/diff.py`:
```python
"""Diff two snapshots to detect added/removed/changed nodes and edges."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from socialgraph.snapshot.models import Snapshot


@dataclass
class SnapshotDiff:
    added_persons: set[str] = field(default_factory=set)       # canonical_ids
    removed_persons: set[str] = field(default_factory=set)
    changed_persons: dict[str, dict[str, tuple[Any, Any]]] = field(default_factory=dict)
    added_companies: set[str] = field(default_factory=set)
    removed_companies: set[str] = field(default_factory=set)
    added_edges: list[tuple[str, str, str]] = field(default_factory=list)   # (type, src, dst)
    removed_edges: list[tuple[str, str, str]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return (
            not self.added_persons
            and not self.removed_persons
            and not self.changed_persons
            and not self.added_companies
            and not self.removed_companies
            and not self.added_edges
            and not self.removed_edges
        )


def snapshot_diff(a: Snapshot, b: Snapshot) -> SnapshotDiff:
    """Compute the diff between snapshot a (before) and snapshot b (after)."""
    d = SnapshotDiff()

    a_persons = {p.canonical_id: p for p in a.persons}
    b_persons = {p.canonical_id: p for p in b.persons}
    d.added_persons = set(b_persons) - set(a_persons)
    d.removed_persons = set(a_persons) - set(b_persons)
    for cid in set(a_persons) & set(b_persons):
        changes: dict[str, tuple[Any, Any]] = {}
        a_attrs = a_persons[cid].attrs
        b_attrs = b_persons[cid].attrs
        all_keys = set(a_attrs) | set(b_attrs)
        for key in all_keys:
            av, bv = a_attrs.get(key), b_attrs.get(key)
            if av != bv:
                changes[key] = (av, bv)
        if changes:
            d.changed_persons[cid] = changes

    a_companies = {c.canonical_id for c in a.companies}
    b_companies = {c.canonical_id for c in b.companies}
    d.added_companies = b_companies - a_companies
    d.removed_companies = a_companies - b_companies

    a_edges = {(e.edge_type, e.src, e.dst) for e in a.edges}
    b_edges = {(e.edge_type, e.src, e.dst) for e in b.edges}
    d.added_edges = list(b_edges - a_edges)
    d.removed_edges = list(a_edges - b_edges)

    return d
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_snapshot_diff.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/snapshot/diff.py tests/unit/test_snapshot_diff.py
git commit -m "feat: snapshot diff (added/removed/changed persons, companies, edges)"
```

---

## Task 8: Snapshot store (write + read)

**Files:**
- Create: `src/socialgraph/snapshot/store.py`
- Create: `tests/unit/test_snapshot_store.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_snapshot_store.py`:
```python
from pathlib import Path
from socialgraph.snapshot.models import Snapshot, SnapshotPerson, SnapshotCompany, SnapshotEdge
from socialgraph.snapshot.store import SnapshotStore


def _snap_with_person(cid: str = "p1", name: str = "Alice") -> Snapshot:
    p = SnapshotPerson(canonical_id=cid, attrs={"full_name": name}, observations=[])
    return Snapshot(persons=[p], companies=[], edges=[])


def test_write_creates_file(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    path = store.write(snap)
    assert path is not None
    assert path.is_file()


def test_write_skips_when_empty(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    empty = Snapshot([], [], [])
    path = store.write(empty)
    assert path is None


def test_write_skips_when_no_diff(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    store.write(snap)  # first write
    path = store.write(snap)  # same snapshot again
    assert path is None  # skipped


def test_read_latest_returns_none_when_empty(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    assert store.read_latest() is None


def test_read_latest_round_trips(tmp_path: Path):
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    store.write(snap)
    loaded = store.read_latest()
    assert loaded is not None
    assert len(loaded.persons) == 1
    assert loaded.persons[0].canonical_id == "p1"
    assert loaded.persons[0].attrs["full_name"] == "Alice"


def test_write_is_atomic(tmp_path: Path):
    # File must not be partially visible (uses tmp + rename)
    store = SnapshotStore(tmp_path / "snapshots")
    snap = _snap_with_person()
    path = store.write(snap)
    assert path is not None
    # Read back byte-by-byte — every line must be valid JSON
    import json
    for line in path.read_text().splitlines():
        json.loads(line)  # raises if malformed
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_snapshot_store.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `store.py`**

Create `src/socialgraph/snapshot/store.py`:
```python
"""SnapshotStore — write and read immutable graph snapshots.

Each snapshot is an atomic JSONL file under snapshots/{ts}.jsonl.
Writes are skipped when the diff vs the previous snapshot is empty,
preventing unnecessary disk growth on repeated re-imports.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from socialgraph.snapshot.diff import snapshot_diff
from socialgraph.snapshot.models import Snapshot


class SnapshotStore:
    """Manages the snapshots/ directory."""

    def __init__(self, snapshots_dir: Path) -> None:
        self.dir = snapshots_dir

    def write(self, snapshot: Snapshot) -> Path | None:
        """Write snapshot atomically. Returns the path, or None if skipped.

        Skipped when: snapshot is empty, OR diff vs latest is empty.
        """
        if snapshot.is_empty():
            return None

        previous = self.read_latest()
        if previous is not None and snapshot_diff(previous, snapshot).is_empty():
            return None

        self.dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        final_path = self.dir / f"{ts}.jsonl"
        tmp_path = self.dir / f".{ts}.tmp"

        lines = snapshot.to_jsonl_lines()
        with tmp_path.open("w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        tmp_path.rename(final_path)
        return final_path

    def read_latest(self) -> Snapshot | None:
        """Return the most recent snapshot, or None if none exist."""
        if not self.dir.is_dir():
            return None
        files = sorted(
            (p for p in self.dir.glob("*.jsonl") if not p.name.startswith(".")),
            reverse=True,
        )
        if not files:
            return None
        return self._read_file(files[0])

    def _read_file(self, path: Path) -> Snapshot:
        lines = path.read_text(encoding="utf-8").splitlines()
        return Snapshot.from_jsonl_lines(lines)
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_snapshot_store.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/snapshot/store.py tests/unit/test_snapshot_store.py
git commit -m "feat: SnapshotStore — atomic write with skip-if-no-diff"
```

---

## Task 9: NetworkX projection

**Files:**
- Create: `src/socialgraph/graph/__init__.py`
- Create: `src/socialgraph/graph/projection.py`
- Create: `tests/unit/test_projection.py`

Install networkx first:

- [ ] **Step 1: Add networkx to pyproject.toml + install**

In `pyproject.toml`, add `"networkx>=3.3"` to the `dependencies` list.

Run: `.venv/bin/pip install -e .`
Expected: `Successfully installed networkx-...`

- [ ] **Step 2: Write failing test**

Create `tests/unit/test_projection.py`:
```python
from socialgraph.snapshot.models import Snapshot, SnapshotPerson, SnapshotCompany, SnapshotEdge
from socialgraph.graph.projection import build_graph


def _snap() -> Snapshot:
    alice = SnapshotPerson(canonical_id="p-alice", attrs={"full_name": "Alice", "current_company": "Acme"}, observations=[])
    bob = SnapshotPerson(canonical_id="p-bob", attrs={"full_name": "Bob", "current_company": "Acme"}, observations=[])
    acme = SnapshotCompany(canonical_id="company-acme", name="Acme Corp")
    e1 = SnapshotEdge(edge_type="WORKS_AT", src="p-alice", dst="company-acme", attrs={"title": "CEO"})
    e2 = SnapshotEdge(edge_type="WORKS_AT", src="p-bob", dst="company-acme", attrs={"title": "Eng"})
    return Snapshot(persons=[alice, bob], companies=[acme], edges=[e1, e2])


def test_build_graph_has_person_nodes():
    G = build_graph(_snap())
    assert "p-alice" in G
    assert G.nodes["p-alice"]["node_type"] == "Person"
    assert G.nodes["p-alice"]["full_name"] == "Alice"


def test_build_graph_has_company_nodes():
    G = build_graph(_snap())
    assert "company-acme" in G
    assert G.nodes["company-acme"]["node_type"] == "Company"
    assert G.nodes["company-acme"]["name"] == "Acme Corp"


def test_build_graph_has_works_at_edges():
    G = build_graph(_snap())
    edges = list(G.edges("p-alice", data=True))
    assert any(
        d.get("edge_type") == "WORKS_AT" and v == "company-acme"
        for u, v, d in edges
    )


def test_build_graph_empty_snapshot():
    G = build_graph(Snapshot([], [], []))
    assert len(G.nodes) == 0
    assert len(G.edges) == 0
```

- [ ] **Step 3: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_projection.py -v
```
Expected: `ImportError`

- [ ] **Step 4: Create `__init__.py`**

```bash
touch src/socialgraph/graph/__init__.py
```

- [ ] **Step 5: Implement `projection.py`**

Create `src/socialgraph/graph/projection.py`:
```python
"""NetworkX graph projection from a Snapshot.

Builds an in-memory MultiDiGraph with Person and Company nodes and
WORKS_AT edges. All node/edge attributes from the snapshot are preserved
as node/edge data for query and analytics use.
"""
from __future__ import annotations

import networkx as nx

from socialgraph.snapshot.models import Snapshot


def build_graph(snapshot: Snapshot) -> nx.MultiDiGraph:
    """Return a MultiDiGraph from snapshot nodes and edges."""
    G: nx.MultiDiGraph = nx.MultiDiGraph()

    for person in snapshot.persons:
        G.add_node(
            person.canonical_id,
            node_type="Person",
            **person.attrs,
        )

    for company in snapshot.companies:
        G.add_node(
            company.canonical_id,
            node_type="Company",
            name=company.name,
            **company.attrs,
        )

    for edge in snapshot.edges:
        G.add_edge(
            edge.src,
            edge.dst,
            edge_type=edge.edge_type,
            **edge.attrs,
        )

    return G
```

- [ ] **Step 6: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_projection.py -v
```
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/socialgraph/graph/__init__.py src/socialgraph/graph/projection.py tests/unit/test_projection.py
git commit -m "feat: NetworkX graph projection from snapshot"
```

---

## Task 10: Graph queries

**Files:**
- Create: `src/socialgraph/graph/query.py`
- Create: `tests/unit/test_query.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_query.py`:
```python
from socialgraph.snapshot.models import Snapshot, SnapshotPerson, SnapshotCompany, SnapshotEdge
from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import at_company, neighbors_via_company


def _snap() -> Snapshot:
    persons = [
        SnapshotPerson("p-alice", {"full_name": "Alice", "current_company": "Acme"}, []),
        SnapshotPerson("p-bob", {"full_name": "Bob", "current_company": "Acme"}, []),
        SnapshotPerson("p-carol", {"full_name": "Carol", "current_company": "Beta"}, []),
    ]
    companies = [
        SnapshotCompany("company-acme", "Acme Corp"),
        SnapshotCompany("company-beta", "Beta Inc"),
    ]
    edges = [
        SnapshotEdge("WORKS_AT", "p-alice", "company-acme"),
        SnapshotEdge("WORKS_AT", "p-bob", "company-acme"),
        SnapshotEdge("WORKS_AT", "p-carol", "company-beta"),
    ]
    return Snapshot(persons, companies, edges)


def test_at_company_exact_match():
    G = build_graph(_snap())
    results = at_company(G, "Acme Corp")
    names = [r["full_name"] for r in results]
    assert sorted(names) == ["Alice", "Bob"]


def test_at_company_case_insensitive():
    G = build_graph(_snap())
    results = at_company(G, "acme corp")
    assert len(results) == 2


def test_at_company_not_found():
    G = build_graph(_snap())
    results = at_company(G, "Nonexistent")
    assert results == []


def test_neighbors_via_company_finds_colleagues():
    G = build_graph(_snap())
    # Alice and Bob both work at Acme → neighbors of each other via company
    neighbors = neighbors_via_company(G, "p-alice")
    ids = [n["canonical_id"] for n in neighbors]
    assert "p-bob" in ids
    assert "p-alice" not in ids  # self excluded


def test_neighbors_via_company_no_company():
    # Person without WORKS_AT edge → no neighbors
    snap = Snapshot(
        persons=[SnapshotPerson("p-lone", {"full_name": "Lone"}, [])],
        companies=[],
        edges=[],
    )
    G = build_graph(snap)
    assert neighbors_via_company(G, "p-lone") == []


def test_neighbors_returns_attrs():
    G = build_graph(_snap())
    neighbors = neighbors_via_company(G, "p-alice")
    for n in neighbors:
        assert "canonical_id" in n
        assert "full_name" in n
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/unit/test_query.py -v
```
Expected: `ImportError`

- [ ] **Step 3: Implement `query.py`**

Create `src/socialgraph/graph/query.py`:
```python
"""Graph query functions over the NetworkX MultiDiGraph.

All functions accept the graph G produced by build_graph() and return
plain dicts — ready for JSON serialisation or CLI display.
"""
from __future__ import annotations

import networkx as nx


def at_company(G: nx.MultiDiGraph, company_name: str) -> list[dict]:
    """Return all Persons with a WORKS_AT edge to the named company.

    Match is case-insensitive on the Company node's 'name' attribute.
    """
    company_name_lower = company_name.lower()

    # Find matching company node(s)
    company_ids = {
        n
        for n, d in G.nodes(data=True)
        if d.get("node_type") == "Company" and d.get("name", "").lower() == company_name_lower
    }

    results: list[dict] = []
    for company_id in company_ids:
        # Find persons with WORKS_AT edge into this company
        for src, dst, data in G.in_edges(company_id, data=True):
            if data.get("edge_type") == "WORKS_AT":
                node_data = dict(G.nodes[src])
                node_data["canonical_id"] = src
                results.append(node_data)

    return results


def neighbors_via_company(G: nx.MultiDiGraph, canonical_id: str, depth: int = 1) -> list[dict]:
    """Return Persons who share a company with the given Person.

    In M2, inter-person edges don't exist (no scrape data for mutual connections).
    The meaningful 1st-degree neighbors are colleagues at the same company,
    reachable via WORKS_AT edges through Company nodes.

    depth > 1 follows WORKS_AT chains: Person → Company → Person → Company → ...
    For M2, depth=1 (same-company colleagues) is the primary use case.
    """
    if canonical_id not in G:
        return []

    visited_persons: set[str] = {canonical_id}
    result: list[dict] = []

    # Collect companies this person works at
    companies: set[str] = {
        dst
        for src, dst, data in G.out_edges(canonical_id, data=True)
        if data.get("edge_type") == "WORKS_AT"
    }

    for _ in range(depth):
        new_companies: set[str] = set()
        for co_id in companies:
            # All persons who also WORKS_AT this company
            for src, dst, data in G.in_edges(co_id, data=True):
                if data.get("edge_type") == "WORKS_AT" and src not in visited_persons:
                    visited_persons.add(src)
                    node_data = dict(G.nodes[src])
                    node_data["canonical_id"] = src
                    result.append(node_data)
                    # For depth > 1: also traverse their companies
                    for _, co2, d2 in G.out_edges(src, data=True):
                        if d2.get("edge_type") == "WORKS_AT":
                            new_companies.add(co2)
        companies = new_companies

    return result
```

- [ ] **Step 4: Run test, verify pass**

```bash
.venv/bin/pytest tests/unit/test_query.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/graph/query.py tests/unit/test_query.py
git commit -m "feat: graph queries — at_company(), neighbors_via_company()"
```

---

## Task 11: Ingest pipeline (wire resolve + snapshot into import)

**Files:**
- Create: `src/socialgraph/pipeline.py`
- Create: `tests/integration/test_pipeline_e2e.py`
- Modify: `src/socialgraph/cli/import_cmd.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/integration/test_pipeline_e2e.py`:
```python
"""End-to-end test of the full ingest pipeline: import → resolve → snapshot."""
from pathlib import Path
from typer.testing import CliRunner
from socialgraph.cli.main import app
from socialgraph.snapshot.store import SnapshotStore
from socialgraph.paths import DataPaths

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])


def test_import_creates_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 0, result.stdout

    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3  # Alice, Bob, Carol


def test_import_creates_merge_decisions(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    paths = DataPaths(tmp_path / "data")
    assert paths.merge_decisions.is_file()
    lines = paths.merge_decisions.read_text().splitlines()
    # 3 contacts → 3 create events
    import json
    creates = [json.loads(l) for l in lines if '"event": "create"' in l]
    assert len(creates) == 3


def test_reimport_same_data_no_new_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_files_before = list((tmp_path / "data" / "snapshots").glob("*.jsonl"))
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_files_after = list((tmp_path / "data" / "snapshots").glob("*.jsonl"))
    # Same data → diff is empty → no new snapshot written
    assert len(snap_files_before) == len(snap_files_after)
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/integration/test_pipeline_e2e.py -v
```
Expected: 3 failures (no snapshot creation after import).

- [ ] **Step 3: Create `pipeline.py`**

Create `src/socialgraph/pipeline.py`:
```python
"""Full ingest pipeline: resolve identity + build + write snapshot.

Called by import_cmd after writing JSONL. Reads ALL parsed JSONL for
the platform (not just the current run) to build a complete picture.
"""
from __future__ import annotations

import json
from pathlib import Path

from socialgraph.identity.canonical import CanonicalLog
from socialgraph.identity.resolve import within_platform_resolve
from socialgraph.paths import DataPaths
from socialgraph.schema.raw_contact import RawContact
from socialgraph.snapshot.build import build_snapshot
from socialgraph.snapshot.store import SnapshotStore


def _load_all_contacts(paths: DataPaths) -> list[RawContact]:
    """Load all RawContact records from all parsed JSONL files."""
    contacts: list[RawContact] = []
    if not paths.parsed.is_dir():
        return contacts
    for jsonl_file in sorted(paths.parsed.glob("*.jsonl")):
        for line in jsonl_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                contacts.append(RawContact.model_validate(json.loads(line)))
            except Exception:
                continue
    return contacts


def run_pipeline(paths: DataPaths) -> dict[str, int]:
    """Resolve identity, build snapshot, write if changed.

    Returns counts: {persons, companies, edges, snapshot_written}.
    """
    contacts = _load_all_contacts(paths)
    if not contacts:
        return {"persons": 0, "companies": 0, "edges": 0, "snapshot_written": 0}

    log = CanonicalLog(paths.merge_decisions)
    resolved = within_platform_resolve(contacts, log)

    snapshot = build_snapshot(resolved)
    store = SnapshotStore(paths.snapshots)
    written_path = store.write(snapshot)

    return {
        "persons": len(snapshot.persons),
        "companies": len(snapshot.companies),
        "edges": len(snapshot.edges),
        "snapshot_written": 1 if written_path else 0,
    }
```

- [ ] **Step 4: Wire pipeline into `import_cmd.py`**

In `src/socialgraph/cli/import_cmd.py`, add the import at the top:
```python
from socialgraph.pipeline import run_pipeline
```

After the `log.append("import.end", ...)` call and before the `typer.echo(...)` line, add:
```python
            counts = run_pipeline(paths)
```

Replace the existing `typer.echo(f"imported {len(contacts)} contacts → {dst}")` with:
```python
            typer.echo(f"imported {len(contacts)} contacts → {dst}")
            if counts["snapshot_written"]:
                typer.echo(
                    f"graph updated: {counts['persons']} persons, "
                    f"{counts['companies']} companies, {counts['edges']} edges"
                )
```

- [ ] **Step 5: Run tests, verify pass**

```bash
.venv/bin/pytest tests/integration/test_pipeline_e2e.py tests/integration/test_import_pipeline.py -v
```
Expected: both test files pass (6 + 3 = 9 tests).

- [ ] **Step 6: Run full suite**

```bash
.venv/bin/pytest -q
```
Expected: all prior tests + new ones pass (≥ 68 tests).

- [ ] **Step 7: Commit**

```bash
git add src/socialgraph/pipeline.py src/socialgraph/cli/import_cmd.py tests/integration/test_pipeline_e2e.py
git commit -m "feat: wire resolve+snapshot pipeline into import command"
```

---

## Task 12: `socialgraph who-at` command

**Files:**
- Create: `src/socialgraph/cli/who_at_cmd.py`
- Create: `tests/integration/test_who_at_command.py`
- Modify: `src/socialgraph/cli/main.py`

- [ ] **Step 1: Write failing test**

Create `tests/integration/test_who_at_command.py`:
```python
from pathlib import Path
from typer.testing import CliRunner
from socialgraph.cli.main import app

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def test_who_at_finds_connections(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    result = runner.invoke(app, ["who-at", "Acme Co"])
    assert result.exit_code == 0, result.stdout
    assert "Alice Example" in result.stdout
    assert "Carol Test" in result.stdout
    assert "Bob Sample" not in result.stdout  # Bob is at Beta Corp


def test_who_at_no_results(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    result = runner.invoke(app, ["who-at", "Nonexistent Corp"])
    assert result.exit_code == 0
    assert "no connections" in result.stdout.lower() or "0" in result.stdout


def test_who_at_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["who-at", "Acme"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/integration/test_who_at_command.py -v
```
Expected: fail (no `who-at` command).

- [ ] **Step 3: Implement `who_at_cmd.py`**

Create `src/socialgraph/cli/who_at_cmd.py`:
```python
"""`socialgraph who-at "<company>"` — list network connections at a company."""
from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import at_company
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore


def who_at_command(company: str) -> None:
    paths = DataPaths(Path.cwd() / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is None:
        typer.echo("no graph yet — run: socialgraph import linkedin <path>")
        return

    G = build_graph(snap)
    results = at_company(G, company)

    if not results:
        typer.echo(f"no connections at '{company}'")
        return

    typer.echo(f"{len(results)} connection(s) at '{company}':\n")
    for person in sorted(results, key=lambda p: p.get("full_name", "")):
        name = person.get("full_name", "(unknown)")
        title = person.get("current_title", "")
        line = f"  {name}"
        if title:
            line += f" — {title}"
        typer.echo(line)
```

- [ ] **Step 4: Register command in `main.py`**

Add to imports in `src/socialgraph/cli/main.py`:
```python
from socialgraph.cli.who_at_cmd import who_at_command
```

Add command registration (before `if __name__ == "__main__":`):
```python
@app.command("who-at")
def who_at(company: str = typer.Argument(..., help="Company name to search for")) -> None:
    """List connections at a company."""
    who_at_command(company)
```

- [ ] **Step 5: Run test, verify pass**

```bash
.venv/bin/pytest tests/integration/test_who_at_command.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/cli/who_at_cmd.py src/socialgraph/cli/main.py tests/integration/test_who_at_command.py
git commit -m "feat: socialgraph who-at command"
```

---

## Task 13: `socialgraph neighbors` command

**Files:**
- Create: `src/socialgraph/cli/neighbors_cmd.py`
- Create: `tests/integration/test_neighbors_command.py`
- Modify: `src/socialgraph/cli/main.py`

- [ ] **Step 1: Write failing test**

Create `tests/integration/test_neighbors_command.py`:
```python
from pathlib import Path
from typer.testing import CliRunner
from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def _get_canonical_id(tmp_path: Path, name_fragment: str) -> str:
    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    for p in snap.persons:
        if name_fragment.lower() in p.attrs.get("full_name", "").lower():
            return p.canonical_id
    raise AssertionError(f"person {name_fragment!r} not found in snapshot")


def test_neighbors_finds_colleagues(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    alice_id = _get_canonical_id(tmp_path, "Alice")
    result = runner.invoke(app, ["neighbors", alice_id])
    assert result.exit_code == 0, result.stdout
    # Alice and Carol both work at Acme Co → Carol is a neighbor of Alice
    assert "Carol Test" in result.stdout


def test_neighbors_unknown_id(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    result = runner.invoke(app, ["neighbors", "nonexistent-uuid"])
    assert result.exit_code == 0
    assert "no neighbors" in result.stdout.lower() or "0" in result.stdout


def test_neighbors_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["neighbors", "any-id"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/integration/test_neighbors_command.py -v
```
Expected: fail (no `neighbors` command).

- [ ] **Step 3: Implement `neighbors_cmd.py`**

Create `src/socialgraph/cli/neighbors_cmd.py`:
```python
"""`socialgraph neighbors <canonical_id>` — list company colleagues.

In M2, neighbors are Persons who share a company (via WORKS_AT edges).
Inter-person edges become available in M4 when scrape provides mutual
connection data.
"""
from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.graph.projection import build_graph
from socialgraph.graph.query import neighbors_via_company
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore


def neighbors_command(canonical_id: str, depth: int) -> None:
    paths = DataPaths(Path.cwd() / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is None:
        typer.echo("no graph yet — run: socialgraph import linkedin <path>")
        return

    G = build_graph(snap)
    results = neighbors_via_company(G, canonical_id, depth=depth)

    if not results:
        typer.echo(f"no neighbors found for {canonical_id!r}")
        typer.echo("(neighbors are colleagues at the same company; scrape data adds richer connections in M4)")
        return

    typer.echo(f"{len(results)} neighbor(s) (depth={depth}):\n")
    for person in sorted(results, key=lambda p: p.get("full_name", "")):
        name = person.get("full_name", "(unknown)")
        company = person.get("current_company", "")
        cid = person.get("canonical_id", "")
        line = f"  {name}"
        if company:
            line += f" @ {company}"
        line += f"  [{cid}]"
        typer.echo(line)
```

- [ ] **Step 4: Register in `main.py`**

Add import:
```python
from socialgraph.cli.neighbors_cmd import neighbors_command
```

Add command:
```python
@app.command("neighbors")
def neighbors(
    canonical_id: str = typer.Argument(..., help="Canonical ID of the person"),
    depth: int = typer.Option(1, "--depth", "-d", help="Traversal depth via company nodes"),
) -> None:
    """List company colleagues of a person (depth=1: same company)."""
    neighbors_command(canonical_id, depth)
```

- [ ] **Step 5: Run test, verify pass**

```bash
.venv/bin/pytest tests/integration/test_neighbors_command.py -v
```
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/cli/neighbors_cmd.py src/socialgraph/cli/main.py tests/integration/test_neighbors_command.py
git commit -m "feat: socialgraph neighbors command (via-company depth traversal)"
```

---

## Task 14: `socialgraph rebuild` command + extend `status`

**Files:**
- Create: `src/socialgraph/cli/rebuild_cmd.py`
- Create: `tests/integration/test_rebuild_command.py`
- Modify: `src/socialgraph/cli/status_cmd.py`
- Modify: `src/socialgraph/cli/main.py`

- [ ] **Step 1: Write failing tests**

Create `tests/integration/test_rebuild_command.py`:
```python
from pathlib import Path
from typer.testing import CliRunner
from socialgraph.cli.main import app
from socialgraph.snapshot.store import SnapshotStore
from socialgraph.paths import DataPaths

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def test_rebuild_rebuilds_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    # Delete snapshot to simulate corruption
    paths = DataPaths(tmp_path / "data")
    for f in paths.snapshots.glob("*.jsonl"):
        f.unlink()
    # Rebuild from parsed JSONL
    result = runner.invoke(app, ["rebuild"])
    assert result.exit_code == 0, result.stdout
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3


def test_rebuild_with_no_parsed_data(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["rebuild"])
    assert result.exit_code == 0
    assert "no parsed" in result.stdout.lower() or "nothing" in result.stdout.lower()
```

- [ ] **Step 2: Run test, verify fail**

```bash
.venv/bin/pytest tests/integration/test_rebuild_command.py -v
```
Expected: fail.

- [ ] **Step 3: Implement `rebuild_cmd.py`**

Create `src/socialgraph/cli/rebuild_cmd.py`:
```python
"""`socialgraph rebuild` — rebuild graph from all parsed JSONL files.

Re-reads every record in data/parsed/, resolves identity using the
existing merge_decisions.jsonl (preserves canonical_ids), builds a
fresh snapshot, and writes it if it differs from the latest one.
"""
from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.pipeline import run_pipeline
from socialgraph.paths import DataPaths


def rebuild_command() -> None:
    paths = DataPaths(Path.cwd() / "data")

    if not paths.parsed.is_dir() or not any(paths.parsed.glob("*.jsonl")):
        typer.echo("no parsed data found — run: socialgraph import linkedin <path>")
        return

    typer.echo("rebuilding graph from all parsed records…")
    counts = run_pipeline(paths)

    if counts["persons"] == 0:
        typer.echo("nothing to rebuild (all parsed files empty)")
        return

    typer.echo(
        f"graph rebuilt: {counts['persons']} persons, "
        f"{counts['companies']} companies, {counts['edges']} edges"
    )
    if counts["snapshot_written"]:
        typer.echo("new snapshot written")
    else:
        typer.echo("graph unchanged — no new snapshot")
```

- [ ] **Step 4: Extend `status_cmd.py` with graph counts**

In `src/socialgraph/cli/status_cmd.py`, add imports at the top:
```python
from socialgraph.snapshot.store import SnapshotStore
```

Add this block at the end of `status_command()`, after the existing error-printing block:
```python
    # Graph counts from latest snapshot
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    if snap is not None:
        typer.echo(f"\ngraph:")
        typer.echo(f"  {len(snap.persons)} persons")
        typer.echo(f"  {len(snap.companies)} companies")
        typer.echo(f"  {len(snap.edges)} edges")
    else:
        typer.echo("\ngraph: (none — run 'socialgraph import' to build)")
```

- [ ] **Step 5: Register `rebuild` in `main.py`**

Add import:
```python
from socialgraph.cli.rebuild_cmd import rebuild_command
```

Add command:
```python
@app.command("rebuild")
def rebuild() -> None:
    """Rebuild graph from all parsed JSONL files (restores after nuke)."""
    rebuild_command()
```

- [ ] **Step 6: Update `test_status_command.py` to check graph output**

Open `tests/integration/test_status_command.py`. Extend `test_status_after_imports`:
```python
def test_status_shows_graph_counts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "persons" in result.stdout
    assert "companies" in result.stdout
```

- [ ] **Step 7: Run tests, verify pass**

```bash
.venv/bin/pytest tests/integration/test_rebuild_command.py tests/integration/test_status_command.py -v
```
Expected: 2 rebuild + 3 status = 5 tests pass.

- [ ] **Step 8: Commit**

```bash
git add src/socialgraph/cli/rebuild_cmd.py src/socialgraph/cli/rebuild_cmd.py src/socialgraph/cli/status_cmd.py src/socialgraph/cli/main.py tests/integration/test_rebuild_command.py tests/integration/test_status_command.py
git commit -m "feat: rebuild command + graph counts in status"
```

---

## Task 15: Full suite green-check + ruff pass

**Files:** none new. Verification only.

- [ ] **Step 1: Run full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all prior 50 tests + new M2 tests pass (≥ 80 tests total). If any fail, fix before continuing.

- [ ] **Step 2: Run ruff**

```bash
.venv/bin/ruff check src tests --fix && .venv/bin/ruff format src tests
```
Expected: clean.

- [ ] **Step 3: Run pyright**

```bash
.venv/bin/pyright src
```
Expected: 0 errors (note: networkx stubs may not be installed — `pyright` will report `reportMissingModuleSource` for `networkx`. This is acceptable; add `"reportMissingModuleSource": "none"` to `[tool.pyright]` in pyproject.toml if noisy).

If pyright flags networkx, add to `pyproject.toml`:
```toml
[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.12"
typeCheckingMode = "basic"
venvPath = "."
venv = ".venv"
reportMissingModuleSource = "none"
```

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -A
git commit -m "chore: lint + pyright clean for M2 modules"
```

---

## Task 16: M2 E2E smoke + round-trip sovereignty test

**Files:**
- Create: `tests/e2e/test_m2_smoke.py`

- [ ] **Step 1: Write E2E test**

Create `tests/e2e/test_m2_smoke.py`:
```python
"""M2 smoke: import → resolve → graph → query → round-trip sovereignty."""
import json
import shutil
import tarfile
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.snapshot.store import SnapshotStore

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"])


def test_m2_full_pipeline(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)

    # 1. Import and pipeline
    r = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert r.exit_code == 0
    assert "graph updated" in r.stdout
    assert "3 persons" in r.stdout

    # 2. Snapshot exists
    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap = store.read_latest()
    assert snap is not None
    assert len(snap.persons) == 3
    assert len(snap.companies) >= 1  # Acme Co, Beta Corp

    # 3. merge_decisions.jsonl has 3 create events
    creates = [
        json.loads(l) for l in paths.merge_decisions.read_text().splitlines()
        if '"event": "create"' in l
    ]
    assert len(creates) == 3

    # 4. who-at works
    r = runner.invoke(app, ["who-at", "Acme Co"])
    assert r.exit_code == 0
    assert "Alice Example" in r.stdout
    assert "Carol Test" in r.stdout

    # 5. status shows graph counts
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert "3 persons" in r.stdout

    # 6. Re-import → no new snapshot (idempotent)
    snap_count_before = len(list(paths.snapshots.glob("*.jsonl")))
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    snap_count_after = len(list(paths.snapshots.glob("*.jsonl")))
    assert snap_count_before == snap_count_after


def test_m2_round_trip_sovereignty(tmp_path: Path, monkeypatch):
    """Round-trip test: backup data/ → nuke → restore → rebuild → identical graph."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)

    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])

    paths = DataPaths(tmp_path / "data")
    store = SnapshotStore(paths.snapshots)
    snap_before = store.read_latest()
    assert snap_before is not None

    # Canonical state: person count + company count + sorted canonical_ids
    persons_before = sorted(p.canonical_id for p in snap_before.persons)
    companies_before = sorted(c.canonical_id for c in snap_before.companies)

    # Backup
    backup = tmp_path / "backup.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        tar.add(paths.root, arcname="data")

    # Nuke
    shutil.rmtree(paths.root)
    assert not paths.root.exists()

    # Restore
    with tarfile.open(backup, "r:gz") as tar:
        tar.extractall(tmp_path)

    assert paths.root.exists()

    # Rebuild from restored flat files
    r = runner.invoke(app, ["rebuild"])
    assert r.exit_code == 0

    # Verify identical state
    snap_after = store.read_latest()
    assert snap_after is not None
    persons_after = sorted(p.canonical_id for p in snap_after.persons)
    companies_after = sorted(c.canonical_id for c in snap_after.companies)
    assert persons_after == persons_before
    assert companies_after == companies_before
```

- [ ] **Step 2: Run E2E tests**

```bash
.venv/bin/pytest tests/e2e/ -v
```
Expected: `test_m1_smoke.py` still passes + 2 new M2 tests pass.

- [ ] **Step 3: Run full suite**

```bash
.venv/bin/pytest -q
```
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_m2_smoke.py
git commit -m "test: M2 E2E smoke + round-trip sovereignty"
```

---

## Task 17: M2 demo verify + tag + push

**Files:** none. Verification + git ops.

- [ ] **Step 1: Full clean-room demo**

```bash
rm -rf data .env config.yml
socialgraph init
socialgraph import linkedin tests/fixtures/linkedin/connections_small.csv
# Expect: "imported 3 contacts", "graph updated: 3 persons, ..."

socialgraph status
# Expect: parsed files, graph counts (3 persons, 2+ companies)

socialgraph who-at "Acme Co"
# Expect: Alice Example, Carol Test

socialgraph who-at "Beta Corp"
# Expect: Bob Sample
```

Get canonical ID for Alice from snapshot and run:
```bash
python3 -c "
import json
from pathlib import Path
snap = sorted(Path('data/snapshots').glob('*.jsonl'))[-1]
for l in snap.read_text().splitlines():
    d = json.loads(l)
    if d.get('node_type') == 'Person' and 'Alice' in d.get('attrs', {}).get('full_name', ''):
        print(d['canonical_id'])
"
```

Then:
```bash
socialgraph neighbors <alice-canonical-id>
# Expect: Carol Test (shares Acme Co)
```

- [ ] **Step 2: Full test suite**

```bash
.venv/bin/pytest -v
```
Expected: all green.

- [ ] **Step 3: Lint + typecheck**

```bash
.venv/bin/ruff check src tests && .venv/bin/ruff format --check src tests && .venv/bin/pyright src
```
Expected: clean.

- [ ] **Step 4: Tag + push**

```bash
rm -rf data .env config.yml
git status  # confirm clean
git tag -a m2 -m "M2: identity resolve, snapshot history, NetworkX graph, who-at, neighbors"
git push origin main --tags
```

---

## Self-Review

**Spec coverage check (spec §4.2–4.4, milestone M2):**

| Requirement | Task |
|---|---|
| `identity/resolve` (within-platform dedup) | Task 4 |
| `canonical_id` log (merge_decisions.jsonl) | Task 2 |
| `snapshot/write` + skip-if-empty | Task 8 |
| `snapshot/diff` | Task 7 |
| NetworkX projection (`load_from_snapshots`) | Task 9 |
| `apply_merge_decisions` in projection | Task 9 (log replayed in CanonicalLog, IDs stable) |
| CLI query: `who-at` | Task 12 |
| CLI query: `neighbors` | Task 13 |
| `socialgraph status` extended with graph counts | Task 14 |
| `socialgraph rebuild` | Task 14 |
| Round-trip E2E sovereignty test | Task 16 |
| Auto-resolve + snapshot after import | Task 11 |
| M2 demo verify + tag | Task 17 |
| `runs.py` shared module | Task 1 |
| Field merge rules | Task 3 |
| Snapshot models | Task 5 |
| Snapshot build | Task 6 |
| Pipeline module | Task 11 |

**Placeholder scan:** No TBDs, todos, or "similar to" references found. All code blocks are complete.

**Type consistency verification:**
- `CanonicalLog` defined Task 2, used in Tasks 3 (resolve), 11 (pipeline) ✓
- `within_platform_resolve(contacts, log)` defined Task 4, used in Task 11 (pipeline) ✓
- `build_snapshot(resolved: list[tuple[str, RawContact]])` defined Task 6, used in Task 11 ✓
- `Snapshot`, `SnapshotPerson`, `SnapshotCompany`, `SnapshotEdge` defined Task 5, used in Tasks 6, 7, 8, 9, 10 ✓
- `SnapshotStore.write(snapshot)→Path|None`, `.read_latest()→Snapshot|None` defined Task 8, used in Tasks 11, 12, 13, 14, 16 ✓
- `build_graph(snapshot: Snapshot)→nx.MultiDiGraph` defined Task 9, used in Tasks 10, 12, 13 ✓
- `at_company(G, company_name: str)→list[dict]`, `neighbors_via_company(G, id, depth)→list[dict]` defined Task 10, used in Tasks 12, 13 ✓
- `run_pipeline(paths: DataPaths)→dict[str, int]` defined Task 11, used in Tasks 12 (indirectly via import), 14 (rebuild) ✓
- `new_run_id()` defined Task 1, import_cmd updated in Task 1 ✓

**Out of scope for M2 (confirmed deferred):**
- Cross-platform merge (M3) — X + LinkedIn identity merge
- Pending merge review queue (M3)
- CLI queries: `path`, `changed-jobs`, `new-connections`, `dormant` — these need snapshot diff or inter-person edges
- `socialgraph nuke` (exists in spec, trivial, add in M3 or M6 with other export/viz work)
- `socialgraph export` (M6)
- Scrape enrichment (M4)
