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
