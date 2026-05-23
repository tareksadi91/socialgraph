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


def test_merge_method_writes_event(tmp_path: Path):
    import json

    p = tmp_path / "merge_decisions.jsonl"
    log = CanonicalLog(p)
    c1 = log.get_or_create("linkedin#alice")
    log.get_or_create("x#alice-x")
    log.merge(["x#alice-x"], target_canonical_id=c1)
    # After merge, x#alice-x should map to c1
    assert log.get_or_create("x#alice-x") == c1
    events = [json.loads(line) for line in p.read_text().splitlines()]
    assert any(e["event"] == "merge" for e in events)


def test_unmerge_method_restores_separate_ids(tmp_path: Path):
    import uuid as _uuid

    p = tmp_path / "merge_decisions.jsonl"
    log = CanonicalLog(p)
    c1 = log.get_or_create("linkedin#alice")
    log.merge(["x#alice-x"], target_canonical_id=c1)
    fresh = str(_uuid.uuid4())
    log.unmerge(reassignments={"x#alice-x": fresh})
    assert log.get_or_create("x#alice-x") == fresh
    assert log.get_or_create("linkedin#alice") == c1  # unchanged


def test_raw_ids_for_canonical(tmp_path: Path):
    log = CanonicalLog(tmp_path / "merge_decisions.jsonl")
    c1 = log.get_or_create("linkedin#alice")
    log.get_or_create("x#alice-x")
    log.merge(["x#alice-x"], target_canonical_id=c1)
    raw_ids = log.raw_ids_for(c1)
    assert "linkedin#alice" in raw_ids
    assert "x#alice-x" in raw_ids
