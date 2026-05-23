from pathlib import Path

from socialgraph.port.state import PortCandidate, PortState


def _seed_candidates() -> list[PortCandidate]:
    return [
        PortCandidate(
            handle="holger_seim",
            display_name="Holger Seim",
            bio_preview="CEO @ Blinkist",
            score=0.95,
            rationale="name=0.95,bio_company_match",
        ),
    ]


def test_record_discovered_creates_pending_entry(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    cid = "li-canonical-1"
    candidate_id = state.record_discovered(linkedin_canonical_id=cid, candidates=_seed_candidates())
    assert candidate_id is not None
    pending = state.list_needs_review()
    assert len(pending) == 1
    assert pending[0].linkedin_canonical_id == cid
    assert len(pending[0].candidates) == 1


def test_resolve_picks_handle(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    cid = state.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    state.resolve(candidate_id=cid, selected_handle="holger_seim")
    assert state.list_needs_review() == []
    queued = state.list_resolved_not_queued()
    assert len(queued) == 1
    assert queued[0].selected_handle == "holger_seim"


def test_reject_removes_from_review(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    cid = state.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    state.reject(candidate_id=cid)
    assert state.list_needs_review() == []
    assert state.list_resolved_not_queued() == []


def test_full_lifecycle(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    cid = state.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    state.resolve(candidate_id=cid, selected_handle="holger_seim")
    state.queue(candidate_id=cid, x_profile_url="https://x.com/holger_seim")
    assert len(state.list_queued()) == 1
    state.opened(candidate_id=cid)
    state.followed(candidate_id=cid)
    assert state.list_queued() == []
    assert state.list_needs_review() == []
    assert state.list_followed()[0].candidate_id == cid


def test_replay_restores_state(tmp_path: Path):
    p = tmp_path / "port_state.jsonl"
    state1 = PortState(p)
    cid = state1.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    state1.resolve(candidate_id=cid, selected_handle="holger_seim")
    state2 = PortState(p)
    queued_after_replay = state2.list_resolved_not_queued()
    assert len(queued_after_replay) == 1
    assert queued_after_replay[0].selected_handle == "holger_seim"


def test_skip_already_processed_linkedin_canonical_id(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    state.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    assert state.has_been_processed("li-1") is True
    assert state.has_been_processed("li-2") is False


def test_counts(tmp_path: Path):
    state = PortState(tmp_path / "port_state.jsonl")
    cid1 = state.record_discovered(linkedin_canonical_id="li-1", candidates=_seed_candidates())
    state.record_discovered(linkedin_canonical_id="li-2", candidates=_seed_candidates())
    state.resolve(candidate_id=cid1, selected_handle="h1")
    state.queue(candidate_id=cid1, x_profile_url="https://x.com/h1")
    state.opened(candidate_id=cid1)
    state.followed(candidate_id=cid1)
    counts = state.counts()
    assert counts["needs_review"] == 1
    assert counts["followed"] == 1
    assert counts["queued"] == 0
