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
    with pytest.raises(XArchiveError, match=r"following\.js"):
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
