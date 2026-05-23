import uuid
from pathlib import Path

from socialgraph.identity.cross_platform import CandidatePair
from socialgraph.identity.pending import PendingMergeQueue


def _pair(li_rid: str = "linkedin#alice", x_rid: str = "x#alice_x") -> CandidatePair:
    return CandidatePair(
        linkedin_raw_id=li_rid,
        x_raw_id=x_rid,
        linkedin_canonical_id=str(uuid.uuid4()),
        x_canonical_id=str(uuid.uuid4()),
        signals=["name_exact"],
        linkedin_attrs={"full_name": "Alice Example"},
        x_attrs={"full_name": "alice_x", "handle": "alice_x"},
    )


def test_add_and_list_pending(tmp_path: Path):
    q = PendingMergeQueue(tmp_path / "pending_merges.jsonl")
    q.add(_pair())
    pending = q.list_pending()
    assert len(pending) == 1
    assert pending[0].status == "pending"
    assert pending[0].linkedin_raw_id == "linkedin#alice"


def test_add_skips_duplicate_pair(tmp_path: Path):
    q = PendingMergeQueue(tmp_path / "pending_merges.jsonl")
    q.add(_pair())
    q.add(_pair())
    assert len(q.list_pending()) == 1


def test_paired_raw_ids_returns_known_pairs(tmp_path: Path):
    q = PendingMergeQueue(tmp_path / "pending_merges.jsonl")
    q.add(_pair("linkedin#alice", "x#alice_x"))
    q.add(_pair("linkedin#bob", "x#bob_x"))
    pairs = q.paired_raw_ids()
    assert ("linkedin#alice", "x#alice_x") in pairs
    assert ("linkedin#bob", "x#bob_x") in pairs


def test_reject_marks_rejected(tmp_path: Path):
    q = PendingMergeQueue(tmp_path / "pending_merges.jsonl")
    q.add(_pair())
    pending = q.list_pending()
    q.reject(pending[0].candidate_id)
    assert len(q.list_pending()) == 0
    all_merges = q.list_all()
    assert all_merges[0].status == "rejected"


def test_count_pending(tmp_path: Path):
    q = PendingMergeQueue(tmp_path / "pending_merges.jsonl")
    q.add(_pair("linkedin#alice", "x#alice_x"))
    q.add(_pair("linkedin#bob", "x#bob_x"))
    assert q.count_pending() == 2
