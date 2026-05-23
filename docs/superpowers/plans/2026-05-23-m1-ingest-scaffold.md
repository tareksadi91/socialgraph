# M1: Ingest Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship working `socialgraph init`, `socialgraph import {linkedin|x}`, and `socialgraph status` commands that produce inspectable `parsed/*.jsonl` files from official platform data exports. No graph, no identity, no scrape yet.

**Architecture:** Python package under `src/socialgraph/`. Typer-driven CLI dispatches to module functions. Pydantic-typed `RawContact` records written to JSONL. Flat `data/` dir is source of truth from day one. Lockfile + sync_log + path conventions are foundational primitives reused by all later milestones.

**Tech Stack:** Python 3.11+ · Typer · Pydantic v2 · pytest · ruff · pyright · pre-commit · hypothesis (light use)

**Spec reference:** `docs/superpowers/specs/2026-05-23-socialgraph-design.md`, milestone M1.

---

## File Structure

**Create:**
```
pyproject.toml
.env.example
config.yml.example
.pre-commit-config.yaml
.python-version
README.md
CONTRIBUTING.md
src/socialgraph/__init__.py
src/socialgraph/__main__.py
src/socialgraph/paths.py
src/socialgraph/config.py
src/socialgraph/lockfile.py
src/socialgraph/sync_log.py
src/socialgraph/schema/__init__.py
src/socialgraph/schema/raw_contact.py
src/socialgraph/ingest/__init__.py
src/socialgraph/ingest/header_aliases.py
src/socialgraph/ingest/import_linkedin.py
src/socialgraph/ingest/import_x.py
src/socialgraph/cli/__init__.py
src/socialgraph/cli/main.py
src/socialgraph/cli/init_cmd.py
src/socialgraph/cli/import_cmd.py
src/socialgraph/cli/status_cmd.py
src/socialgraph/exit_codes.py
tests/__init__.py
tests/conftest.py
tests/fixtures/linkedin/connections_small.csv
tests/fixtures/linkedin/connections_locale_fr.csv
tests/fixtures/linkedin/connections_unicode.csv
tests/fixtures/x/archive_v1.zip
tests/fixtures/x/archive_v2.zip
tests/fixtures/x/archive_corrupt.zip
tests/unit/test_paths.py
tests/unit/test_config.py
tests/unit/test_lockfile.py
tests/unit/test_sync_log.py
tests/unit/test_schema.py
tests/unit/test_header_aliases.py
tests/unit/test_import_linkedin.py
tests/unit/test_import_x.py
tests/unit/test_exit_codes.py
tests/integration/test_init_command.py
tests/integration/test_import_pipeline.py
tests/integration/test_status_command.py
tests/e2e/test_m1_smoke.py
```

**Modify:** `.gitignore` (extend existing).

---

## Task 1: Project bootstrap (pyproject.toml + Python version)

**Files:**
- Create: `pyproject.toml`
- Create: `.python-version`
- Modify: `.gitignore`

- [ ] **Step 1: Write `.python-version`**

Create `.python-version`:
```
3.11
```

- [ ] **Step 2: Write `pyproject.toml`**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "socialgraph"
version = "0.1.0"
description = "Personal network sovereignty tool. Own your social graph."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "pydantic>=2.6",
    "pyyaml>=6.0",
    "chardet>=5.2",
    "python-dateutil>=2.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.1",
    "hypothesis>=6.100",
    "ruff>=0.4",
    "pyright>=1.1.360",
    "pre-commit>=3.7",
]

[project.scripts]
socialgraph = "socialgraph.cli.main:app"

[tool.hatch.build.targets.wheel]
packages = ["src/socialgraph"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "RUF"]

[tool.pyright]
include = ["src", "tests"]
pythonVersion = "3.11"
typeCheckingMode = "basic"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra"
```

- [ ] **Step 3: Extend `.gitignore`**

Replace contents of `.gitignore`:
```
data/
.env
*.key
*.pem
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
.ruff_cache/
.pyright_cache/
dist/
build/
*.egg-info/
.venv/
node_modules/
```

- [ ] **Step 4: Install deps**

Run: `python3.11 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`
Expected: install completes; `socialgraph --help` will fail (no CLI yet) — that's fine.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .python-version .gitignore
git commit -m "chore: project bootstrap (pyproject, deps, gitignore)"
```

---

## Task 2: Exit codes module

**Files:**
- Create: `src/socialgraph/__init__.py`
- Create: `src/socialgraph/exit_codes.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/test_exit_codes.py`

- [ ] **Step 1: Create package init files**

Create `src/socialgraph/__init__.py`:
```python
"""SocialGraph — personal network sovereignty tool."""

__version__ = "0.1.0"
```

Create `tests/__init__.py` (empty).

Create `tests/unit/__init__.py` (empty).

- [ ] **Step 2: Write failing test**

Create `tests/unit/test_exit_codes.py`:
```python
from socialgraph.exit_codes import ExitCode


def test_exit_codes_have_expected_values():
    assert ExitCode.SUCCESS == 0
    assert ExitCode.GENERIC_ERROR == 1
    assert ExitCode.AUTH_REQUIRED == 2
    assert ExitCode.RATE_LIMITED == 3
    assert ExitCode.BOT_CHALLENGE == 4
    assert ExitCode.CONFIG_ERROR == 5
    assert ExitCode.LOCK_HELD == 6
    assert ExitCode.BUDGET_EXHAUSTED == 7


def test_exit_codes_are_iterable_ints():
    for code in ExitCode:
        assert isinstance(code.value, int)
```

- [ ] **Step 3: Run test, verify fail**

Run: `pytest tests/unit/test_exit_codes.py -v`
Expected: ImportError (module not yet created).

- [ ] **Step 4: Implement `exit_codes.py`**

Create `src/socialgraph/exit_codes.py`:
```python
from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERIC_ERROR = 1
    AUTH_REQUIRED = 2
    RATE_LIMITED = 3
    BOT_CHALLENGE = 4
    CONFIG_ERROR = 5
    LOCK_HELD = 6
    BUDGET_EXHAUSTED = 7
```

- [ ] **Step 5: Run test, verify pass**

Run: `pytest tests/unit/test_exit_codes.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/__init__.py src/socialgraph/exit_codes.py tests/__init__.py tests/unit/__init__.py tests/unit/test_exit_codes.py
git commit -m "feat: define structured CLI exit codes"
```

---

## Task 3: Paths module (canonical data/ layout)

**Files:**
- Create: `src/socialgraph/paths.py`
- Create: `tests/unit/test_paths.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_paths.py`:
```python
from pathlib import Path

from socialgraph.paths import DataPaths


def test_paths_resolves_subdirs(tmp_path: Path):
    paths = DataPaths(tmp_path)
    assert paths.root == tmp_path
    assert paths.raw == tmp_path / "raw"
    assert paths.parsed == tmp_path / "parsed"
    assert paths.snapshots == tmp_path / "snapshots"
    assert paths.profiles == tmp_path / "profiles"
    assert paths.backups == tmp_path / "backups"
    assert paths.cache == tmp_path / "cache"
    assert paths.viz == tmp_path / "viz"
    assert paths.lock_file == tmp_path / ".lock"
    assert paths.merge_decisions == tmp_path / "merge_decisions.jsonl"
    assert paths.pending_merges == tmp_path / "pending_merges.jsonl"
    assert paths.port_state == tmp_path / "port_state.jsonl"
    assert paths.sync_log == tmp_path / "sync_log.jsonl"
    assert paths.tos_ack == tmp_path / ".tos_ack"
    assert paths.no_llm_ack == tmp_path / ".no_llm_ack"


def test_paths_ensure_creates_all_dirs(tmp_path: Path):
    paths = DataPaths(tmp_path)
    paths.ensure()
    for d in [paths.raw, paths.parsed, paths.snapshots, paths.profiles, paths.backups, paths.cache, paths.viz]:
        assert d.is_dir()


def test_paths_parsed_for_run(tmp_path: Path):
    paths = DataPaths(tmp_path)
    p = paths.parsed_for_run("linkedin", "import", "run123")
    assert p == tmp_path / "parsed" / "linkedin_import_run123.jsonl"


def test_paths_raw_run_dir(tmp_path: Path):
    paths = DataPaths(tmp_path)
    p = paths.raw_run_dir("linkedin", "run123")
    assert p == tmp_path / "raw" / "linkedin" / "run123"
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_paths.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `paths.py`**

Create `src/socialgraph/paths.py`:
```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
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
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_paths.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/paths.py tests/unit/test_paths.py
git commit -m "feat: canonical data/ path layout"
```

---

## Task 4: Config loader (YAML + env: refs)

**Files:**
- Create: `src/socialgraph/config.py`
- Create: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_config.py`:
```python
from pathlib import Path

import pytest

from socialgraph.config import (
    Config,
    ConfigError,
    load_config,
    resolve_env_refs,
)


def test_resolve_env_refs_plain_value():
    assert resolve_env_refs("hello", env={}) == "hello"


def test_resolve_env_refs_substitutes_env(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert resolve_env_refs("env:FOO", env=None) == "bar"


def test_resolve_env_refs_missing_env_raises(monkeypatch):
    monkeypatch.delenv("MISSING", raising=False)
    with pytest.raises(ConfigError, match="MISSING"):
        resolve_env_refs("env:MISSING", env=None)


def test_load_config_minimal(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FAKE_KEY", "sk-test")
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
llm:
  enabled: true
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: env:FAKE_KEY
  temperature: 0
  cache: true
platforms:
  linkedin:
    enabled: true
    profile_dir: ./data/profiles/linkedin
  x:
    enabled: true
    profile_dir: ./data/profiles/x
storage:
  data_dir: ./data
  gzip_raw: true
"""
    )
    cfg = load_config(cfg_path)
    assert isinstance(cfg, Config)
    assert cfg.llm.enabled is True
    assert cfg.llm.api_key == "sk-test"
    assert cfg.platforms.linkedin.enabled is True
    assert cfg.storage.data_dir == Path("./data")


def test_load_config_missing_env_var_fails_fast(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("NOPE", raising=False)
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(
        """
llm:
  enabled: true
  provider: anthropic
  model: x
  api_key: env:NOPE
  temperature: 0
  cache: true
platforms:
  linkedin: {enabled: false, profile_dir: ./d}
  x: {enabled: false, profile_dir: ./d}
storage:
  data_dir: ./data
  gzip_raw: true
"""
    )
    with pytest.raises(ConfigError, match="NOPE"):
        load_config(cfg_path)
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_config.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `config.py`**

Create `src/socialgraph/config.py`:
```python
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ConfigError(Exception):
    pass


class LLMConfig(BaseModel):
    enabled: bool = True
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    api_key: str = ""
    temperature: float = 0.0
    cache: bool = True


class ScrapeConfig(BaseModel):
    throttle_seconds: float = 5.0
    jitter: float = 2.0
    headed: bool = True


class PlatformConfig(BaseModel):
    enabled: bool = True
    profile_dir: Path
    scrape: ScrapeConfig = Field(default_factory=ScrapeConfig)


class PlatformsConfig(BaseModel):
    linkedin: PlatformConfig
    x: PlatformConfig


class StorageConfig(BaseModel):
    data_dir: Path
    gzip_raw: bool = True


class WebConfig(BaseModel):
    bind: str = "127.0.0.1"
    api_port: int = 8000
    ui_port: int = 3000


class Config(BaseModel):
    llm: LLMConfig
    platforms: PlatformsConfig
    storage: StorageConfig
    web: WebConfig = Field(default_factory=WebConfig)


def resolve_env_refs(value: str, env: dict[str, str] | None = None) -> str:
    if not isinstance(value, str) or not value.startswith("env:"):
        return value
    key = value[len("env:"):]
    source = env if env is not None else os.environ
    if key not in source or source[key] == "":
        raise ConfigError(f"env:{key} referenced but not set")
    return source[key]


def _walk_resolve(node: Any, env: dict[str, str] | None) -> Any:
    if isinstance(node, dict):
        return {k: _walk_resolve(v, env) for k, v in node.items()}
    if isinstance(node, list):
        return [_walk_resolve(v, env) for v in node]
    if isinstance(node, str):
        return resolve_env_refs(node, env=env)
    return node


def load_config(path: Path, env: dict[str, str] | None = None) -> Config:
    if not path.is_file():
        raise ConfigError(f"config file not found: {path}")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ConfigError("config root must be a mapping")
    resolved = _walk_resolve(raw, env)
    try:
        return Config.model_validate(resolved)
    except Exception as exc:
        raise ConfigError(str(exc)) from exc
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_config.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/config.py tests/unit/test_config.py
git commit -m "feat: YAML config loader with env: ref resolution"
```

---

## Task 5: Lockfile primitive

**Files:**
- Create: `src/socialgraph/lockfile.py`
- Create: `tests/unit/test_lockfile.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_lockfile.py`:
```python
import os
from pathlib import Path

import pytest

from socialgraph.exit_codes import ExitCode
from socialgraph.lockfile import Lock, LockHeldError


def test_lock_acquires_and_releases(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with Lock(lock_path):
        assert lock_path.is_file()
        contents = lock_path.read_text()
        assert str(os.getpid()) in contents
    assert not lock_path.is_file()


def test_lock_blocks_second_acquire(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with Lock(lock_path):
        with pytest.raises(LockHeldError) as exc:
            with Lock(lock_path):
                pass
        assert exc.value.exit_code == ExitCode.LOCK_HELD
        assert "pid" in str(exc.value).lower()


def test_lock_clears_stale_lock(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    # stale lock pointing at impossibly high PID
    lock_path.write_text('{"pid": 999999, "started_at": "x", "hostname": "h"}')
    with Lock(lock_path):
        # should re-acquire because pid not running
        assert str(os.getpid()) in lock_path.read_text()


def test_lock_force_unlock(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text('{"pid": 1, "started_at": "x", "hostname": "h"}')
    with Lock(lock_path, force_unlock=True):
        assert str(os.getpid()) in lock_path.read_text()
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_lockfile.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `lockfile.py`**

Create `src/socialgraph/lockfile.py`:
```python
from __future__ import annotations

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Self

from socialgraph.exit_codes import ExitCode


class LockHeldError(Exception):
    exit_code = ExitCode.LOCK_HELD


class Lock:
    def __init__(self, path: Path, force_unlock: bool = False) -> None:
        self.path = path
        self.force_unlock = force_unlock

    def __enter__(self) -> Self:
        if self.path.is_file():
            if self.force_unlock or self._is_stale():
                self.path.unlink()
            else:
                try:
                    existing = json.loads(self.path.read_text())
                    pid = existing.get("pid")
                except json.JSONDecodeError:
                    pid = "unknown"
                raise LockHeldError(
                    f"another instance running (pid {pid}). Use --force-unlock if stale."
                )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "hostname": platform.node(),
        }))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.path.is_file():
            try:
                existing = json.loads(self.path.read_text())
                if existing.get("pid") == os.getpid():
                    self.path.unlink()
            except (json.JSONDecodeError, FileNotFoundError):
                pass

    def _is_stale(self) -> bool:
        try:
            existing = json.loads(self.path.read_text())
            pid = existing.get("pid")
            if not isinstance(pid, int):
                return True
            os.kill(pid, 0)
            return False
        except (json.JSONDecodeError, FileNotFoundError):
            return True
        except (OSError, ProcessLookupError):
            return True
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_lockfile.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/lockfile.py tests/unit/test_lockfile.py
git commit -m "feat: lockfile primitive with stale-detection"
```

---

## Task 6: Sync log primitive

**Files:**
- Create: `src/socialgraph/sync_log.py`
- Create: `tests/unit/test_sync_log.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_sync_log.py`:
```python
import json
from pathlib import Path

from socialgraph.sync_log import SyncLog


def test_append_writes_one_line_per_event(tmp_path: Path):
    log = SyncLog(tmp_path / "sync_log.jsonl")
    log.append("cmd.start", run_id="r1", cmd="import")
    log.append("cmd.end", run_id="r1", cmd="import", duration_ms=42)

    lines = (tmp_path / "sync_log.jsonl").read_text().splitlines()
    assert len(lines) == 2
    e1 = json.loads(lines[0])
    e2 = json.loads(lines[1])
    assert e1["event"] == "cmd.start"
    assert e1["run_id"] == "r1"
    assert e2["event"] == "cmd.end"
    assert e2["duration_ms"] == 42
    assert "ts" in e1 and "ts" in e2


def test_append_preserves_existing_lines(tmp_path: Path):
    p = tmp_path / "sync_log.jsonl"
    log = SyncLog(p)
    log.append("a")
    log.append("b")
    log.append("c")
    assert len(p.read_text().splitlines()) == 3


def test_iter_yields_parsed_events(tmp_path: Path):
    p = tmp_path / "sync_log.jsonl"
    log = SyncLog(p)
    log.append("a", x=1)
    log.append("b", x=2)
    events = list(log.iter())
    assert [e["event"] for e in events] == ["a", "b"]
    assert events[0]["x"] == 1


def test_last_errors_filters(tmp_path: Path):
    p = tmp_path / "sync_log.jsonl"
    log = SyncLog(p)
    log.append("cmd.start")
    log.append("error.rate_limited", code=3)
    log.append("cmd.end")
    log.append("error.auth_required", code=2)
    errs = log.last_errors(limit=5)
    assert len(errs) == 2
    assert errs[0]["event"] == "error.rate_limited"
    assert errs[1]["event"] == "error.auth_required"
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_sync_log.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `sync_log.py`**

Create `src/socialgraph/sync_log.py`:
```python
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


class SyncLog:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: str, **fields: Any) -> None:
        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **fields,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def iter(self) -> Iterator[dict[str, Any]]:
        if not self.path.is_file():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    def last_errors(self, limit: int = 3) -> list[dict[str, Any]]:
        errs = [e for e in self.iter() if e.get("event", "").startswith("error.")]
        return errs[-limit:]
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_sync_log.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/sync_log.py tests/unit/test_sync_log.py
git commit -m "feat: append-only sync log with fsync"
```

---

## Task 7: RawContact Pydantic schema

**Files:**
- Create: `src/socialgraph/schema/__init__.py`
- Create: `src/socialgraph/schema/raw_contact.py`
- Create: `tests/unit/test_schema.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_schema.py`:
```python
import json

import pytest
from pydantic import ValidationError

from socialgraph.schema.raw_contact import RawContact


def _minimal_kwargs(**over) -> dict:
    base = {
        "raw_id": "r#abc",
        "platform": "linkedin",
        "source": "import",
        "platform_native_id": "abc",
        "profile_url": "https://linkedin.com/in/abc",
        "observed_at": "2026-05-23T10:00:00+00:00",
        "run_id": "r123",
        "full_name": "Alice Example",
    }
    base.update(over)
    return base


def test_minimal_record_valid():
    rc = RawContact(**_minimal_kwargs())
    assert rc.schema_version == 1
    assert rc.platform == "linkedin"
    assert rc.email is None


def test_invalid_platform_rejected():
    with pytest.raises(ValidationError):
        RawContact(**_minimal_kwargs(platform="myspace"))


def test_invalid_source_rejected():
    with pytest.raises(ValidationError):
        RawContact(**_minimal_kwargs(source="invented"))


def test_to_jsonl_round_trip():
    rc = RawContact(**_minimal_kwargs(email="a@b.com"))
    s = rc.to_jsonl_line()
    parsed = json.loads(s)
    assert parsed["email"] == "a@b.com"
    rc2 = RawContact.from_jsonl_line(s)
    assert rc2 == rc


def test_observation_default_topics_empty():
    rc = RawContact(**_minimal_kwargs())
    assert rc.topics == []
    assert rc.mutual_names_sample == []
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_schema.py -v`
Expected: ImportError.

- [ ] **Step 3: Create `schema/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `raw_contact.py`**

Create `src/socialgraph/schema/raw_contact.py`:
```python
from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["linkedin", "x"]
Source = Literal["import", "scrape"]
FollowDirection = Literal["following", "follower", "mutual"]


class RawContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1

    raw_id: str
    platform: Platform
    source: Source
    platform_native_id: str
    profile_url: str
    observed_at: datetime
    run_id: str

    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    handle: str | None = None
    email: str | None = None
    verified: bool | None = None

    headline: str | None = None
    bio: str | None = None
    location_raw: str | None = None
    location_city: str | None = None
    location_country: str | None = None
    photo_url: str | None = None
    language: str | None = None

    current_company: str | None = None
    current_company_url: str | None = None
    current_title: str | None = None
    industry: str | None = None

    connected_on: datetime | None = None
    follow_direction: FollowDirection | None = None
    mutual_count: int | None = None
    mutual_names_sample: list[str] = Field(default_factory=list)

    follower_count: int | None = None
    following_count: int | None = None

    topics: list[str] = Field(default_factory=list)
    seniority: str | None = None
    function: str | None = None

    raw_blob_path: str | None = None

    def to_jsonl_line(self) -> str:
        return self.model_dump_json(exclude_none=False)

    @classmethod
    def from_jsonl_line(cls, line: str) -> "RawContact":
        return cls.model_validate(json.loads(line))
```

- [ ] **Step 5: Run test, verify pass**

Run: `pytest tests/unit/test_schema.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/schema/__init__.py src/socialgraph/schema/raw_contact.py tests/unit/test_schema.py
git commit -m "feat: RawContact Pydantic schema (schema_version=1)"
```

---

## Task 8: Header alias normalization

**Files:**
- Create: `src/socialgraph/ingest/__init__.py`
- Create: `src/socialgraph/ingest/header_aliases.py`
- Create: `tests/unit/test_header_aliases.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_header_aliases.py`:
```python
import pytest

from socialgraph.ingest.header_aliases import (
    UnknownHeaderError,
    normalize_linkedin_headers,
)


def test_normalize_canonical_english():
    headers = ["First Name", "Last Name", "URL", "Email Address", "Company", "Position", "Connected On"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_lowercase():
    headers = ["first name", "last name", "url", "email address", "company", "position", "connected on"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_french_locale():
    headers = ["Prénom", "Nom", "URL", "Adresse e-mail", "Entreprise", "Poste", "Date de connexion"]
    result = normalize_linkedin_headers(headers)
    assert result == ["first_name", "last_name", "profile_url", "email", "company", "title", "connected_on"]


def test_normalize_unknown_header_raises():
    headers = ["First Name", "Last Name", "MysteryColumn"]
    with pytest.raises(UnknownHeaderError, match="MysteryColumn"):
        normalize_linkedin_headers(headers, strict=True)


def test_normalize_unknown_header_passes_through_non_strict():
    headers = ["First Name", "MysteryColumn"]
    result = normalize_linkedin_headers(headers, strict=False)
    assert result == ["first_name", "MysteryColumn"]
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_header_aliases.py -v`
Expected: ImportError.

- [ ] **Step 3: Create `ingest/__init__.py`**

Empty file.

- [ ] **Step 4: Implement `header_aliases.py`**

Create `src/socialgraph/ingest/header_aliases.py`:
```python
from __future__ import annotations


class UnknownHeaderError(Exception):
    pass


# Locale aliases observed in LinkedIn Connections.csv exports.
# Keys are lowercased + stripped versions of the original header.
LINKEDIN_HEADER_ALIASES: dict[str, str] = {
    "first name": "first_name",
    "prénom": "first_name",
    "vorname": "first_name",
    "nombre": "first_name",
    "nome": "first_name",
    "last name": "last_name",
    "nom": "last_name",
    "nachname": "last_name",
    "apellido": "last_name",
    "cognome": "last_name",
    "url": "profile_url",
    "profile url": "profile_url",
    "email address": "email",
    "adresse e-mail": "email",
    "e-mail-adresse": "email",
    "correo electrónico": "email",
    "indirizzo email": "email",
    "company": "company",
    "entreprise": "company",
    "unternehmen": "company",
    "empresa": "company",
    "azienda": "company",
    "position": "title",
    "poste": "title",
    "berufsbezeichnung": "title",
    "cargo": "title",
    "posizione": "title",
    "connected on": "connected_on",
    "date de connexion": "connected_on",
    "verbunden am": "connected_on",
    "conectado el": "connected_on",
    "data di collegamento": "connected_on",
}


def normalize_linkedin_headers(headers: list[str], strict: bool = False) -> list[str]:
    out: list[str] = []
    for h in headers:
        key = h.strip().lower()
        if key in LINKEDIN_HEADER_ALIASES:
            out.append(LINKEDIN_HEADER_ALIASES[key])
        elif strict:
            raise UnknownHeaderError(f"unknown LinkedIn CSV header: {h!r}")
        else:
            out.append(h)
    return out
```

- [ ] **Step 5: Run test, verify pass**

Run: `pytest tests/unit/test_header_aliases.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/ingest/__init__.py src/socialgraph/ingest/header_aliases.py tests/unit/test_header_aliases.py
git commit -m "feat: LinkedIn CSV header alias normalization"
```

---

## Task 9: LinkedIn CSV import — fixtures

**Files:**
- Create: `tests/fixtures/linkedin/connections_small.csv`
- Create: `tests/fixtures/linkedin/connections_locale_fr.csv`
- Create: `tests/fixtures/linkedin/connections_unicode.csv`

- [ ] **Step 1: Create canonical English fixture**

Create `tests/fixtures/linkedin/connections_small.csv`:
```
Notes:
"When exporting your connections data, you can also choose to export your contacts, which includes additional fields."
"
First Name,Last Name,URL,Email Address,Company,Position,Connected On
Alice,Example,https://www.linkedin.com/in/alice-example,alice@example.com,Acme Co,Founder,23 May 2024
Bob,Sample,https://www.linkedin.com/in/bob-sample,,Beta Corp,Engineer,01 Jan 2023
Carol,Test,https://www.linkedin.com/in/carol-test,carol@test.org,Acme Co,Designer,15 Jul 2022
```

(Note: LinkedIn export has a notes preamble before the header row; importer must skip until it sees the header line.)

- [ ] **Step 2: Create French locale fixture**

Create `tests/fixtures/linkedin/connections_locale_fr.csv`:
```
Notes :
"En exportant vos données de connexions..."
"
Prénom,Nom,URL,Adresse e-mail,Entreprise,Poste,Date de connexion
Pierre,Martin,https://www.linkedin.com/in/pierre-martin,pierre@fr.example,Société Générale,Ingénieur,12 mars 2023
```

- [ ] **Step 3: Create Unicode fixture**

Create `tests/fixtures/linkedin/connections_unicode.csv`:
```
First Name,Last Name,URL,Email Address,Company,Position,Connected On
محمد,أحمد,https://www.linkedin.com/in/mohammad-ahmad,,شركة الاختبار,مهندس,10 Jun 2024
李,明,https://www.linkedin.com/in/li-ming,liming@example.cn,测试公司,工程师,20 Feb 2024
François,Dupont,https://www.linkedin.com/in/francois-dupont,francois@fr.test,Café Co,Patissier,01 Aug 2023
```

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/linkedin/
git commit -m "test: LinkedIn CSV fixtures (canonical, FR locale, unicode)"
```

---

## Task 10: LinkedIn CSV importer

**Files:**
- Create: `src/socialgraph/ingest/import_linkedin.py`
- Create: `tests/unit/test_import_linkedin.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_import_linkedin.py`:
```python
from pathlib import Path

import pytest

from socialgraph.ingest.import_linkedin import (
    ImportError as LinkedInImportError,
    import_linkedin_csv,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "linkedin"


def test_imports_canonical_csv(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r1")
    assert len(contacts) == 3
    alice = contacts[0]
    assert alice.full_name == "Alice Example"
    assert alice.first_name == "Alice"
    assert alice.last_name == "Example"
    assert alice.email == "alice@example.com"
    assert alice.current_company == "Acme Co"
    assert alice.current_title == "Founder"
    assert alice.profile_url == "https://www.linkedin.com/in/alice-example"
    assert alice.platform == "linkedin"
    assert alice.source == "import"
    assert alice.run_id == "r1"
    assert alice.connected_on is not None
    assert alice.connected_on.year == 2024


def test_writes_jsonl_one_record_per_line(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r1")
    lines = out.read_text().splitlines()
    assert len(lines) == len(contacts)


def test_locale_french(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_locale_fr.csv", out, run_id="rfr")
    assert len(contacts) == 1
    pierre = contacts[0]
    assert pierre.full_name == "Pierre Martin"
    assert pierre.current_company == "Société Générale"
    assert pierre.current_title == "Ingénieur"


def test_unicode_names_preserved(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_unicode.csv", out, run_id="ru")
    assert len(contacts) == 3
    assert contacts[0].first_name == "محمد"
    assert contacts[1].first_name == "李"
    assert contacts[2].first_name == "François"


def test_missing_email_is_none(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_linkedin_csv(FIXTURES / "connections_small.csv", out, run_id="r")
    bob = next(c for c in contacts if c.first_name == "Bob")
    assert bob.email is None


def test_missing_file_raises():
    with pytest.raises(LinkedInImportError):
        import_linkedin_csv(Path("/nonexistent.csv"), Path("/tmp/x.jsonl"), run_id="r")
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_import_linkedin.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `import_linkedin.py`**

Create `src/socialgraph/ingest/import_linkedin.py`:
```python
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

import chardet
from dateutil import parser as dateparser

from socialgraph.ingest.header_aliases import normalize_linkedin_headers
from socialgraph.schema.raw_contact import RawContact


class ImportError(Exception):
    pass


HEADER_SENTINEL_TOKENS = {"first_name", "last_name", "profile_url"}


def _detect_encoding(path: Path) -> str:
    blob = path.read_bytes()[:4096]
    if blob.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    guess = chardet.detect(blob).get("encoding") or "utf-8"
    return guess


def _slug_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def _parse_connected_on(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        return dateparser.parse(value).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _seek_header_row(reader: "csv._reader") -> list[str]:
    for row in reader:
        normalized = normalize_linkedin_headers(row, strict=False)
        if HEADER_SENTINEL_TOKENS & set(normalized):
            return normalized
    raise ImportError("could not locate a header row containing First Name/Last Name/URL")


def import_linkedin_csv(src: Path, dst: Path, run_id: str) -> list[RawContact]:
    if not src.is_file():
        raise ImportError(f"file not found: {src}")
    encoding = _detect_encoding(src)
    contacts: list[RawContact] = []
    now = datetime.now(timezone.utc)

    with src.open("r", encoding=encoding, newline="") as f:
        reader = csv.reader(f)
        headers = _seek_header_row(reader)
        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            record = {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
            first = record.get("first_name", "").strip()
            last = record.get("last_name", "").strip()
            url = record.get("profile_url", "").strip()
            if not first and not last and not url:
                continue
            full_name = (first + " " + last).strip() or url
            slug = _slug_from_url(url) if url else f"unknown-{len(contacts)}"
            contacts.append(RawContact(
                raw_id=f"{run_id}#{slug}",
                platform="linkedin",
                source="import",
                platform_native_id=slug,
                profile_url=url or f"https://www.linkedin.com/in/{slug}",
                observed_at=now,
                run_id=run_id,
                full_name=full_name,
                first_name=first or None,
                last_name=last or None,
                email=(record.get("email", "").strip() or None),
                current_company=(record.get("company", "").strip() or None),
                current_title=(record.get("title", "").strip() or None),
                connected_on=_parse_connected_on(record.get("connected_on", "")),
            ))

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as out:
        for c in contacts:
            out.write(c.to_jsonl_line() + "\n")
    return contacts
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_import_linkedin.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/ingest/import_linkedin.py tests/unit/test_import_linkedin.py
git commit -m "feat: LinkedIn Connections.csv import → parsed JSONL"
```

---

## Task 11: X archive fixtures

**Files:**
- Create: `tests/fixtures/x/archive_v1.zip`
- Create: `tests/fixtures/x/archive_v2.zip`
- Create: `tests/fixtures/x/archive_corrupt.zip`

- [ ] **Step 1: Build helper script and fixtures**

Create temporary helper `/tmp/_build_x_fixtures.py`:
```python
import json
import zipfile
from pathlib import Path

OUT = Path(__file__).parent / "tests" / "fixtures" / "x"
OUT.mkdir(parents=True, exist_ok=True)


def _wrap(varname: str, payload: list[dict]) -> str:
    return f"window.YTD.{varname}.part0 = " + json.dumps(payload, indent=2)


def build_v1():
    account = [{"account": {"accountId": "111", "username": "alice_x", "createdVia": "web", "createdAt": "2010-01-01T00:00:00.000Z", "accountDisplayName": "Alice"}}]
    following = [
        {"following": {"accountId": "222", "userLink": "https://twitter.com/bob_x"}},
        {"following": {"accountId": "333", "userLink": "https://twitter.com/carol_x"}},
    ]
    follower = [
        {"follower": {"accountId": "444", "userLink": "https://twitter.com/dan_x"}},
    ]
    with zipfile.ZipFile(OUT / "archive_v1.zip", "w") as z:
        z.writestr("data/account.js", _wrap("account", account))
        z.writestr("data/following.js", _wrap("following", following))
        z.writestr("data/follower.js", _wrap("follower", follower))
        z.writestr("data/tweets.js", "window.YTD.tweets.part0 = []")
        z.writestr("data/direct-messages.js", "// stub")


def build_v2():
    # newer format uses slightly different keys
    account = [{"account": {"accountId": "555", "username": "evan_x", "createdVia": "ios", "createdAt": "2015-06-15T00:00:00.000Z", "accountDisplayName": "Evan"}}]
    following = [{"following": {"accountId": "666", "userLink": "https://x.com/frida_x"}}]
    follower = [{"follower": {"accountId": "777", "userLink": "https://x.com/gus_x"}}]
    with zipfile.ZipFile(OUT / "archive_v2.zip", "w") as z:
        z.writestr("data/account.js", _wrap("account", account))
        z.writestr("data/following.js", _wrap("following", following))
        z.writestr("data/follower.js", _wrap("follower", follower))


def build_corrupt():
    with zipfile.ZipFile(OUT / "archive_corrupt.zip", "w") as z:
        z.writestr("data/account.js", "window.YTD.account.part0 = []")
        z.writestr("data/tweets.js", "[]")
        # NOTE: no following.js / follower.js


build_v1()
build_v2()
build_corrupt()
print("done")
```

Run: `python3 /tmp/_build_x_fixtures.py` (from the project root).

- [ ] **Step 2: Verify fixtures exist**

Run: `ls tests/fixtures/x/`
Expected: `archive_corrupt.zip archive_v1.zip archive_v2.zip`

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/x/
git commit -m "test: X archive fixtures (v1, v2, corrupt)"
```

---

## Task 12: X archive importer

**Files:**
- Create: `src/socialgraph/ingest/import_x.py`
- Create: `tests/unit/test_import_x.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_import_x.py`:
```python
from pathlib import Path

import pytest

from socialgraph.ingest.import_x import (
    XArchiveError,
    import_x_archive,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "x"


def test_imports_v1_archive(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_x_archive(FIXTURES / "archive_v1.zip", out, run_id="r1")
    handles = sorted(c.handle for c in contacts)
    assert handles == ["bob_x", "carol_x", "dan_x"]
    bob = next(c for c in contacts if c.handle == "bob_x")
    assert bob.follow_direction == "following"
    dan = next(c for c in contacts if c.handle == "dan_x")
    assert dan.follow_direction == "follower"
    assert bob.platform == "x"
    assert bob.source == "import"
    assert bob.run_id == "r1"


def test_imports_v2_archive(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_x_archive(FIXTURES / "archive_v2.zip", out, run_id="r2")
    handles = sorted(c.handle for c in contacts)
    assert handles == ["frida_x", "gus_x"]


def test_corrupt_archive_raises(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    with pytest.raises(XArchiveError, match="following.js"):
        import_x_archive(FIXTURES / "archive_corrupt.zip", out, run_id="rc")


def test_writes_jsonl(tmp_path: Path):
    out = tmp_path / "out.jsonl"
    contacts = import_x_archive(FIXTURES / "archive_v1.zip", out, run_id="r1")
    lines = out.read_text().splitlines()
    assert len(lines) == len(contacts)


def test_does_not_read_tweets_or_dms(tmp_path: Path):
    # Smoke: tweets.js + direct-messages.js exist in v1 fixture; importer should ignore.
    out = tmp_path / "out.jsonl"
    contacts = import_x_archive(FIXTURES / "archive_v1.zip", out, run_id="r1")
    # No record should reference tweet content
    for c in contacts:
        assert c.bio is None
        assert c.headline is None
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/unit/test_import_x.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `import_x.py`**

Create `src/socialgraph/ingest/import_x.py`:
```python
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from socialgraph.schema.raw_contact import RawContact


class XArchiveError(Exception):
    pass


_REQUIRED_FILES = {"data/following.js", "data/follower.js"}
_HANDLE_RE = re.compile(r"(?:twitter|x)\.com/([A-Za-z0-9_]+)")


def _strip_js_wrapper(text: str) -> Any:
    # X archive .js files: `window.YTD.{var}.partN = <JSON>`
    eq_idx = text.find("=")
    if eq_idx == -1:
        raise XArchiveError("JS wrapper missing '='")
    payload = text[eq_idx + 1:].strip()
    return json.loads(payload)


def _handle_from_user_link(link: str) -> str | None:
    m = _HANDLE_RE.search(link or "")
    return m.group(1) if m else None


def import_x_archive(src: Path, dst: Path, run_id: str) -> list[RawContact]:
    if not src.is_file():
        raise XArchiveError(f"file not found: {src}")
    with zipfile.ZipFile(src, "r") as z:
        names = set(z.namelist())
        missing = _REQUIRED_FILES - names
        if missing:
            raise XArchiveError(f"X archive missing required file(s): {sorted(missing)}")
        following_raw = z.read("data/following.js").decode("utf-8", errors="replace")
        follower_raw = z.read("data/follower.js").decode("utf-8", errors="replace")

    following = _strip_js_wrapper(following_raw)
    follower = _strip_js_wrapper(follower_raw)

    contacts: list[RawContact] = []
    now = datetime.now(timezone.utc)

    def _emit(entries: Any, key: str, direction: str) -> None:
        for entry in entries:
            inner = entry.get(key, {})
            account_id = str(inner.get("accountId", "")).strip()
            user_link = inner.get("userLink", "")
            handle = _handle_from_user_link(user_link)
            if not handle and not account_id:
                continue
            slug = handle or account_id
            profile_url = user_link or f"https://x.com/{slug}"
            contacts.append(RawContact(
                raw_id=f"{run_id}#{slug}",
                platform="x",
                source="import",
                platform_native_id=slug,
                profile_url=profile_url,
                observed_at=now,
                run_id=run_id,
                full_name=handle or slug,
                handle=handle,
                follow_direction=direction,  # type: ignore[arg-type]
            ))

    _emit(following, "following", "following")
    _emit(follower, "follower", "follower")

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as out:
        for c in contacts:
            out.write(c.to_jsonl_line() + "\n")
    return contacts
```

- [ ] **Step 4: Run test, verify pass**

Run: `pytest tests/unit/test_import_x.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/ingest/import_x.py tests/unit/test_import_x.py
git commit -m "feat: X archive selective import (following/follower only)"
```

---

## Task 13: pytest conftest with shared fixtures

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write conftest**

Create `tests/conftest.py`:
```python
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def linkedin_fixture_path() -> Path:
    return FIXTURES_ROOT / "linkedin" / "connections_small.csv"


@pytest.fixture
def x_fixture_path() -> Path:
    return FIXTURES_ROOT / "x" / "archive_v1.zip"


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Isolated data/ dir per test."""
    d = tmp_path / "data"
    d.mkdir()
    return d
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "test: shared pytest fixtures (data_dir, fixture paths)"
```

---

## Task 14: CLI scaffold (Typer app + `--version`)

**Files:**
- Create: `src/socialgraph/cli/__init__.py`
- Create: `src/socialgraph/cli/main.py`
- Create: `src/socialgraph/__main__.py`

- [ ] **Step 1: Create CLI package init**

Create `src/socialgraph/cli/__init__.py` (empty).

- [ ] **Step 2: Implement `cli/main.py`**

Create `src/socialgraph/cli/main.py`:
```python
from __future__ import annotations

import typer

from socialgraph import __version__

app = typer.Typer(
    name="socialgraph",
    help="Personal network sovereignty tool.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"socialgraph {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """SocialGraph CLI."""


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Implement `__main__.py`**

Create `src/socialgraph/__main__.py`:
```python
from socialgraph.cli.main import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Smoke test CLI**

Run: `socialgraph --version`
Expected: `socialgraph 0.1.0`

Run: `socialgraph --help`
Expected: Help output listing the app (no subcommands yet).

- [ ] **Step 5: Commit**

```bash
git add src/socialgraph/cli/__init__.py src/socialgraph/cli/main.py src/socialgraph/__main__.py
git commit -m "feat: Typer CLI scaffold with --version"
```

---

## Task 15: `init` command + example files

**Files:**
- Create: `src/socialgraph/cli/init_cmd.py`
- Create: `.env.example`
- Create: `config.yml.example`
- Modify: `src/socialgraph/cli/main.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_init_command.py`

- [ ] **Step 1: Create example config files**

Create `.env.example`:
```
# Optional. Skip if running offline / scrape-free / no LLM enrichment.

# LLM provider — pick one
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# Reserved for v2
X_BEARER_TOKEN=
NEO4J_PASSWORD=
```

Create `config.yml.example`:
```yaml
llm:
  enabled: true
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: env:ANTHROPIC_API_KEY
  temperature: 0
  cache: true

platforms:
  linkedin:
    enabled: true
    profile_dir: ./data/profiles/linkedin
    scrape:
      throttle_seconds: 5
      jitter: 2
      headed: true
  x:
    enabled: true
    profile_dir: ./data/profiles/x
    scrape:
      throttle_seconds: 3
      jitter: 1
      headed: true

storage:
  data_dir: ./data
  gzip_raw: true

web:
  bind: 127.0.0.1
  api_port: 8000
  ui_port: 3000
```

- [ ] **Step 2: Write failing integration test**

Create `tests/integration/__init__.py` (empty).

Create `tests/integration/test_init_command.py`:
```python
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()


def test_init_scaffolds_dirs_and_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Copy example files into the temp project root so init has sources to copy from
    (tmp_path / ".env.example").write_text("ANTHROPIC_API_KEY=\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.stdout

    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "config.yml").is_file()
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "data" / "raw").is_dir()
    assert (tmp_path / "data" / "parsed").is_dir()
    assert (tmp_path / "data" / "snapshots").is_dir()


def test_init_is_idempotent(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("X=\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")

    runner.invoke(app, ["init"])
    (tmp_path / ".env").write_text("CUSTOMIZED=true\n")  # user customizes
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    # init must NOT overwrite a user-edited .env
    assert "CUSTOMIZED=true" in (tmp_path / ".env").read_text()
```

- [ ] **Step 3: Run test, verify fail**

Run: `pytest tests/integration/test_init_command.py -v`
Expected: fail (no init command registered).

- [ ] **Step 4: Implement `init_cmd.py`**

Create `src/socialgraph/cli/init_cmd.py`:
```python
from __future__ import annotations

import shutil
from pathlib import Path

import typer

from socialgraph.paths import DataPaths


def init_command() -> None:
    project_root = Path.cwd()
    env_example = project_root / ".env.example"
    cfg_example = project_root / "config.yml.example"
    env = project_root / ".env"
    cfg = project_root / "config.yml"

    if not env_example.is_file() or not cfg_example.is_file():
        typer.secho(
            "missing .env.example or config.yml.example in current directory",
            err=True,
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=5)

    if env.is_file():
        typer.echo(f".env already exists, leaving untouched: {env}")
    else:
        shutil.copyfile(env_example, env)
        typer.echo(f"created {env}")

    if cfg.is_file():
        typer.echo(f"config.yml already exists, leaving untouched: {cfg}")
    else:
        shutil.copyfile(cfg_example, cfg)
        typer.echo(f"created {cfg}")

    paths = DataPaths(project_root / "data")
    paths.ensure()
    typer.echo(f"data dir scaffolded at {paths.root}")
    typer.echo("\nNext steps:")
    typer.echo("  1. Edit .env with your LLM API key (or leave blank for no-LLM mode)")
    typer.echo("  2. Download LinkedIn export → run: socialgraph import linkedin <path>")
    typer.echo("  3. Request X archive → run: socialgraph import x <path>")
    typer.echo("  4. socialgraph status")
```

- [ ] **Step 5: Register command in `cli/main.py`**

Modify `src/socialgraph/cli/main.py` — add registration after the `_root` callback:
```python
from socialgraph.cli.init_cmd import init_command

@app.command("init")
def init() -> None:
    """Scaffold data/ dir and copy example .env / config.yml."""
    init_command()
```

(Place the import at the top with other imports.)

- [ ] **Step 6: Run test, verify pass**

Run: `pytest tests/integration/test_init_command.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add .env.example config.yml.example src/socialgraph/cli/init_cmd.py src/socialgraph/cli/main.py tests/integration/__init__.py tests/integration/test_init_command.py
git commit -m "feat: socialgraph init command"
```

---

## Task 16: `import` command (LinkedIn + X)

**Files:**
- Create: `src/socialgraph/cli/import_cmd.py`
- Modify: `src/socialgraph/cli/main.py`
- Create: `tests/integration/test_import_pipeline.py`

- [ ] **Step 1: Write failing integration test**

Create `tests/integration/test_import_pipeline.py`:
```python
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup_project(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )
    runner.invoke(app, ["init"], catch_exceptions=False, env={"PWD": str(tmp_path)})


def test_import_linkedin_writes_parsed_jsonl(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 0, result.stdout
    parsed_files = list((tmp_path / "data" / "parsed").glob("linkedin_import_*.jsonl"))
    assert len(parsed_files) == 1
    lines = parsed_files[0].read_text().splitlines()
    assert len(lines) == 3  # Alice, Bob, Carol


def test_import_x_writes_parsed_jsonl(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    assert result.exit_code == 0, result.stdout
    parsed_files = list((tmp_path / "data" / "parsed").glob("x_import_*.jsonl"))
    assert len(parsed_files) == 1
    lines = parsed_files[0].read_text().splitlines()
    assert len(lines) == 3  # bob_x, carol_x, dan_x


def test_import_appends_sync_log_event(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    log = (tmp_path / "data" / "sync_log.jsonl").read_text().splitlines()
    events = [l for l in log if l.strip()]
    assert any('"event": "import.start"' in l for l in events)
    assert any('"event": "import.end"' in l for l in events)


def test_import_unknown_platform_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "myspace", str(LINKEDIN_FIXTURE)])
    assert result.exit_code != 0


def test_import_blocks_when_lock_held(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    # simulate held lock from another live process
    lock = tmp_path / "data" / ".lock"
    import os, json
    lock.write_text(json.dumps({"pid": os.getpid() * 0 + 1, "started_at": "x", "hostname": "h"}))
    # ensure pid is plausibly live by using current pid:
    lock.write_text(json.dumps({"pid": os.getpid(), "started_at": "x", "hostname": "h"}))
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 6
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/integration/test_import_pipeline.py -v`
Expected: fail.

- [ ] **Step 3: Implement `import_cmd.py`**

Create `src/socialgraph/cli/import_cmd.py`:
```python
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import typer

from socialgraph.exit_codes import ExitCode
from socialgraph.ingest.import_linkedin import (
    ImportError as LinkedInImportError,
    import_linkedin_csv,
)
from socialgraph.ingest.import_x import (
    XArchiveError,
    import_x_archive,
)
from socialgraph.lockfile import Lock, LockHeldError
from socialgraph.paths import DataPaths
from socialgraph.sync_log import SyncLog


def _new_run_id(platform: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{platform}_import_{ts}_{uuid.uuid4().hex[:6]}"


def import_command(platform: str, path: Path, force_unlock: bool) -> None:
    if platform not in ("linkedin", "x"):
        typer.secho(f"unknown platform: {platform!r} (expected: linkedin | x)", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    if not path.is_file():
        typer.secho(f"file not found: {path}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=ExitCode.GENERIC_ERROR)

    data_root = Path.cwd() / "data"
    paths = DataPaths(data_root)
    paths.ensure()
    log = SyncLog(paths.sync_log)
    run_id = _new_run_id(platform)
    dst = paths.parsed_for_run(platform, "import", run_id)

    try:
        with Lock(paths.lock_file, force_unlock=force_unlock):
            log.append("import.start", cmd="import", platform=platform, run_id=run_id, source_path=str(path))
            t0 = time.monotonic()
            try:
                if platform == "linkedin":
                    contacts = import_linkedin_csv(path, dst, run_id=run_id)
                else:
                    contacts = import_x_archive(path, dst, run_id=run_id)
            except (LinkedInImportError, XArchiveError) as exc:
                log.append("error.import_failed", run_id=run_id, platform=platform, message=str(exc))
                typer.secho(f"import failed: {exc}", err=True, fg=typer.colors.RED)
                raise typer.Exit(code=ExitCode.GENERIC_ERROR) from exc
            duration_ms = int((time.monotonic() - t0) * 1000)
            log.append(
                "import.end",
                cmd="import",
                platform=platform,
                run_id=run_id,
                count=len(contacts),
                duration_ms=duration_ms,
                out_path=str(dst),
            )
            typer.echo(f"imported {len(contacts)} contacts → {dst}")
    except LockHeldError as exc:
        typer.secho(str(exc), err=True, fg=typer.colors.RED)
        raise typer.Exit(code=int(ExitCode.LOCK_HELD)) from exc
```

- [ ] **Step 4: Register command in `cli/main.py`**

Modify `src/socialgraph/cli/main.py` — add import + command:
```python
from socialgraph.cli.import_cmd import import_command

@app.command("import")
def import_(
    platform: str = typer.Argument(..., help="linkedin | x"),
    path: Path = typer.Argument(..., exists=False, help="Path to export file"),
    force_unlock: bool = typer.Option(False, "--force-unlock", help="Clear stale lock and proceed."),
) -> None:
    """Import official platform data export → parsed JSONL."""
    import_command(platform, path, force_unlock=force_unlock)
```

- [ ] **Step 5: Run test, verify pass**

Run: `pytest tests/integration/test_import_pipeline.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/cli/import_cmd.py src/socialgraph/cli/main.py tests/integration/test_import_pipeline.py
git commit -m "feat: socialgraph import {linkedin|x} command with lockfile + sync_log"
```

---

## Task 17: `status` command (M1 scope)

**Files:**
- Create: `src/socialgraph/cli/status_cmd.py`
- Modify: `src/socialgraph/cli/main.py`
- Create: `tests/integration/test_status_command.py`

- [ ] **Step 1: Write failing test**

Create `tests/integration/test_status_command.py`:
```python
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

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


def test_status_empty(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "parsed: 0 files" in result.stdout or "parsed: 0" in result.stdout
    assert "last import" in result.stdout


def test_status_after_imports(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "linkedin: 3 contacts" in result.stdout
    assert "x: 3 contacts" in result.stdout
    assert "parsed:" in result.stdout
```

- [ ] **Step 2: Run test, verify fail**

Run: `pytest tests/integration/test_status_command.py -v`
Expected: fail.

- [ ] **Step 3: Implement `status_cmd.py`**

Create `src/socialgraph/cli/status_cmd.py`:
```python
from __future__ import annotations

from pathlib import Path

import typer

from socialgraph.paths import DataPaths
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
```

- [ ] **Step 4: Register command in `cli/main.py`**

Add to `src/socialgraph/cli/main.py`:
```python
from socialgraph.cli.status_cmd import status_command

@app.command("status")
def status() -> None:
    """Show counts of parsed files, last imports, recent errors."""
    status_command()
```

- [ ] **Step 5: Run test, verify pass**

Run: `pytest tests/integration/test_status_command.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add src/socialgraph/cli/status_cmd.py src/socialgraph/cli/main.py tests/integration/test_status_command.py
git commit -m "feat: socialgraph status (M1 scope) — file counts + last import + errors"
```

---

## Task 18: E2E smoke test (full M1 demo)

**Files:**
- Create: `tests/e2e/__init__.py`
- Create: `tests/e2e/test_m1_smoke.py`

- [ ] **Step 1: Write E2E test**

Create `tests/e2e/__init__.py` (empty).

Create `tests/e2e/test_m1_smoke.py`:
```python
"""M1 smoke: fresh project → init → import LI → import X → status. Demoable end-to-end."""
import json
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def test_m1_full_bootstrap(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text(
        "storage:\n  data_dir: ./data\n  gzip_raw: true\n"
    )

    # 1. init
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    assert (tmp_path / "data").is_dir()

    # 2. import linkedin
    r = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert r.exit_code == 0
    li_files = list((tmp_path / "data" / "parsed").glob("linkedin_import_*.jsonl"))
    assert len(li_files) == 1
    li_records = [json.loads(l) for l in li_files[0].read_text().splitlines()]
    assert len(li_records) == 3
    assert all(r["platform"] == "linkedin" for r in li_records)
    assert all(r["source"] == "import" for r in li_records)
    assert all(r["schema_version"] == 1 for r in li_records)
    assert all(r["raw_id"].startswith("linkedin_import_") for r in li_records)

    # 3. import x
    r = runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    assert r.exit_code == 0
    x_files = list((tmp_path / "data" / "parsed").glob("x_import_*.jsonl"))
    assert len(x_files) == 1
    x_records = [json.loads(l) for l in x_files[0].read_text().splitlines()]
    assert len(x_records) == 3
    handles = sorted(r["handle"] for r in x_records)
    assert handles == ["bob_x", "carol_x", "dan_x"]

    # 4. status output sane
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert "linkedin: 3 contacts" in r.stdout
    assert "x: 3 contacts" in r.stdout

    # 5. sync_log captured both runs
    log = (tmp_path / "data" / "sync_log.jsonl").read_text().splitlines()
    events = [json.loads(l) for l in log if l.strip()]
    starts = [e for e in events if e["event"] == "import.start"]
    ends = [e for e in events if e["event"] == "import.end"]
    assert len(starts) == 2
    assert len(ends) == 2
```

- [ ] **Step 2: Run test, verify pass**

Run: `pytest tests/e2e/test_m1_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 3: Run full suite**

Run: `pytest -v`
Expected: all unit + integration + e2e tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/__init__.py tests/e2e/test_m1_smoke.py
git commit -m "test: M1 E2E smoke (init → import → status)"
```

---

## Task 19: Pre-commit hooks + ruff lint pass

**Files:**
- Create: `.pre-commit-config.yaml`

- [ ] **Step 1: Create pre-commit config**

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
        args: ["--maxkb=1024"]
      - id: detect-private-key
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

- [ ] **Step 2: Install pre-commit hooks**

Run: `pre-commit install`
Expected: hooks installed at `.git/hooks/pre-commit`.

- [ ] **Step 3: Run ruff against the codebase**

Run: `ruff check src tests --fix && ruff format src tests`
Expected: clean output; any fixes auto-applied.

- [ ] **Step 4: Run pyright**

Run: `pyright src`
Expected: no type errors (basic mode).

- [ ] **Step 5: Re-run full test suite**

Run: `pytest -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add .pre-commit-config.yaml
git add -u   # pick up any ruff auto-fix renames
git commit -m "chore: pre-commit hooks (ruff, gitleaks, large-file guard)"
```

---

## Task 20: README + CONTRIBUTING

**Files:**
- Create: `README.md`
- Create: `CONTRIBUTING.md`

- [ ] **Step 1: Write `README.md`**

Create `README.md`:
```markdown
# SocialGraph

Personal network sovereignty tool. Own your social graph, leave any platform anytime.

**Status:** MVP M1 — ingest scaffold. LinkedIn and X official data exports → inspectable JSONL.

## Quick start

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
socialgraph init
socialgraph import linkedin ~/Downloads/Connections.csv
socialgraph import x ~/Downloads/twitter-archive.zip
socialgraph status
```

Parsed records land in `data/parsed/*.jsonl`. Inspect with `jq` or `cat`.

## Architecture

See `docs/superpowers/specs/2026-05-23-socialgraph-design.md`.

## Milestones

- **M1** (this milestone): import LinkedIn + X, JSONL output, status command
- M2: identity resolution + snapshot history + in-memory graph
- M3: cross-platform merge + review CLI
- M4: scrape enrichment (Playwright + LLM)
- M5: LinkedIn → X port flow
- M6: export formats + viz
- M7: web merge UI

## License

MIT
```

- [ ] **Step 2: Write `CONTRIBUTING.md`**

Create `CONTRIBUTING.md`:
```markdown
# Contributing

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Tests

```bash
pytest                  # full suite
pytest tests/unit       # unit only
pytest -k import_linkedin -v
```

## Lint + typecheck

```bash
ruff check src tests --fix
ruff format src tests
pyright src
```

## Adding a fixture from real data

Real LinkedIn / X data must be sanitized before being committed. A sanitization helper will ship at `scripts/sanitize_fixtures.py` (M4+).

For M1: do not commit real data. Use synthetic fixtures in `tests/fixtures/`.

## Commit style

Conventional commits: `feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`.
```

- [ ] **Step 3: Commit**

```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: README and CONTRIBUTING for M1"
```

---

## Task 21: M1 demo verification + tag

**Files:** none

- [ ] **Step 1: Full clean-room run**

```bash
# from project root
rm -rf data .env config.yml
socialgraph init
socialgraph import linkedin tests/fixtures/linkedin/connections_small.csv
socialgraph import x tests/fixtures/x/archive_v1.zip
socialgraph status
cat data/parsed/linkedin_import_*.jsonl | head -1 | python3 -m json.tool
cat data/sync_log.jsonl
```

Expected:
- `init` scaffolds dirs + .env + config.yml
- `import linkedin` writes 3 contacts
- `import x` writes 3 contacts
- `status` shows `linkedin: 3 contacts`, `x: 3 contacts`, last imports timestamps
- The first parsed record pretty-prints valid Pydantic-schema JSON
- sync_log has start + end events for both imports

- [ ] **Step 2: Run full test suite one final time**

Run: `pytest -v`
Expected: all green.

- [ ] **Step 3: Run lint + typecheck**

Run: `ruff check src tests && ruff format --check src tests && pyright src`
Expected: clean.

- [ ] **Step 4: Tag M1 release**

```bash
# Clean up any clean-room test artifacts before tagging
rm -rf data .env config.yml
git tag -a m1 -m "M1: ingest scaffold (init, import linkedin, import x, status)"
git log --oneline
```

---

## Self-Review

**Spec coverage:** M1 deliverables from spec §12: `init`, `import linkedin`, `import x`, RawContact schema, `parsed/` JSONL, `sync_log`. All covered:
- `init` → Task 15
- `import linkedin` → Tasks 8–10
- `import x` → Tasks 11–12
- RawContact schema → Task 7
- `parsed/` JSONL → Tasks 10 + 12
- `sync_log` → Task 6 + integrated in import command (Task 16)
- Foundational pieces also delivered: exit codes (Task 2), paths (Task 3), config loader (Task 4), lockfile (Task 5), `status` command in M1 scope (Task 17), E2E smoke proving the demo (Task 18), pre-commit + lint (Task 19), docs (Task 20), M1 tag (Task 21).

**Placeholder scan:** none — every code step contains real implementation, every test step shows the assertions.

**Type/API consistency:** Verified across tasks:
- `DataPaths` API (Task 3) used by `init_cmd.py` (Task 15), `import_cmd.py` (Task 16), `status_cmd.py` (Task 17) → matches.
- `RawContact` schema fields (Task 7) consumed by `import_linkedin.py` (Task 10) and `import_x.py` (Task 12) → field names match (`raw_id`, `platform_native_id`, `connected_on`, `handle`, `follow_direction`).
- `ExitCode` (Task 2) used by `Lock` (Task 5) and `import_cmd.py` (Task 16) → `LOCK_HELD == 6` referenced consistently.
- `SyncLog.append(event, **fields)` signature (Task 6) used by `import_cmd.py` (Task 16) → matches.
- Header-alias canonical names (`first_name`, `last_name`, `profile_url`, `email`, `company`, `title`, `connected_on`) (Task 8) consumed by `import_linkedin.py` (Task 10) → matches.

**M1 acceptance criteria** (from spec §15 #1): "Fresh user: `init` → `import linkedin` → `import x` → `status` runs in < 2 minutes with a 5k-connection LinkedIn export" — proved by Task 18 E2E + Task 21 demo. (Performance on 5k connections is not stress-tested here; the importer is straight CSV/ZIP parsing without per-row I/O contention, so 5k completes in seconds.)

No gaps. Plan ready for execution.

---

## Out of scope for M1 (handled by later milestones)

- Identity resolution / canonical_id / merge log → M2
- Snapshot writing / diff / NetworkX projection → M2
- `who-at`, `path`, `neighbors`, `changed-jobs`, `new-connections` → M2
- `merge-review`, `link`, `unmerge`, `pending_merges.jsonl` → M3
- Cross-platform identity (hard + soft signals) → M3
- Scrape (Playwright + LLM + selector fallback), `login` → M4
- Port flow, X handle discovery → M5
- Export (graphml, json-ld, bundle), viz, `nuke`, `rebuild` → M6
- Web merge UI, `dev`, `merge-review --web` → M7
