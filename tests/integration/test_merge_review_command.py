import uuid
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.identity.cross_platform import CandidatePair
from socialgraph.identity.pending import PendingMergeQueue
from socialgraph.paths import DataPaths

runner = CliRunner()


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])


def _seed_pending(tmp_path: Path, count: int = 1) -> list[str]:
    paths = DataPaths(tmp_path / "data")
    queue = PendingMergeQueue(paths.pending_merges)
    ids = []
    for i in range(count):
        pair = CandidatePair(
            linkedin_raw_id=f"linkedin#alice-{i}",
            x_raw_id=f"x#alice-x-{i}",
            linkedin_canonical_id=str(uuid.uuid4()),
            x_canonical_id=str(uuid.uuid4()),
            signals=["name_exact"],
            linkedin_attrs={"full_name": f"Alice {i}", "current_company": "Acme"},
            x_attrs={"full_name": f"alice_x_{i}", "handle": f"alice_x_{i}"},
        )
        result = queue.add(pair)
        if result:
            ids.append(result.candidate_id)
    return ids


def test_merge_review_no_pending(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    result = runner.invoke(app, ["merge-review"])
    assert result.exit_code == 0
    assert "no pending" in result.stdout.lower()


def test_merge_review_shows_candidate_info(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_pending(tmp_path)
    result = runner.invoke(app, ["merge-review"], input="q\n")
    assert result.exit_code == 0
    assert "Alice 0" in result.stdout or "alice" in result.stdout.lower()


def test_merge_review_reject(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_pending(tmp_path)
    result = runner.invoke(app, ["merge-review"], input="n\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    queue = PendingMergeQueue(paths.pending_merges)
    assert queue.count_pending() == 0
    assert queue.list_all()[0].status == "rejected"


def test_merge_review_skip(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    _seed_pending(tmp_path)
    result = runner.invoke(app, ["merge-review"], input="s\n")
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    queue = PendingMergeQueue(paths.pending_merges)
    assert queue.count_pending() == 1  # still pending (skipped)
