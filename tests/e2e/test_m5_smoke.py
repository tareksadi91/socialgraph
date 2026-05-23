"""M5 smoke: import LI -> discover X handles (fake) -> review -> queue -> next -> round-trip."""

import shutil
import tarfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.scoring import XSearchResult
from socialgraph.port.state import PortState
from socialgraph.port.x_search import FakeXSearchClient

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def _fake_with_alice_match() -> FakeXSearchClient:
    return FakeXSearchClient(
        responses={
            '"Alice Example" Acme Co': [
                XSearchResult(
                    handle="alice_example",
                    display_name="Alice Example",
                    bio_preview="Founder @ Acme Co",
                ),
            ],
        },
    )


def test_m5_full_port_flow(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    fake = _fake_with_alice_match()

    with patch("socialgraph.cli.port_discover_cmd._make_search_client", return_value=fake):
        r = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert r.exit_code == 0

    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    needs = state.list_needs_review()
    assert len(needs) >= 1

    # Build input: pick "1" for entries with candidates, "n" for without
    review_input = ""
    for entry in needs:
        if entry.candidates:
            review_input += "1\n"
        else:
            review_input += "n\n"
    r = runner.invoke(app, ["port", "review"], input=review_input)
    assert r.exit_code == 0

    state = PortState(paths.port_state)
    queued = state.list_queued()
    assert len(queued) >= 1

    next_input = "f\n" * len(queued) + "q\n"
    with patch("socialgraph.cli.port_next_cmd._open_url"):
        r = runner.invoke(app, ["port", "next"], input=next_input)
    assert r.exit_code == 0

    state = PortState(paths.port_state)
    assert len(state.list_followed()) >= 1


def test_m5_round_trip_sovereignty(tmp_path: Path, monkeypatch):
    """Backup -> nuke -> restore -> port_state.jsonl replays correctly."""
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    fake = _fake_with_alice_match()
    with patch("socialgraph.cli.port_discover_cmd._make_search_client", return_value=fake):
        runner.invoke(app, ["port", "discover", "--limit", "3"])

    paths = DataPaths(tmp_path / "data")
    state_before = PortState(paths.port_state)
    counts_before = state_before.counts()

    backup = tmp_path / "backup.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        tar.add(paths.root, arcname="data")
    shutil.rmtree(paths.root)
    with tarfile.open(backup, "r:gz") as tar:
        tar.extractall(tmp_path)

    state_after = PortState(paths.port_state)
    assert state_after.counts() == counts_before
