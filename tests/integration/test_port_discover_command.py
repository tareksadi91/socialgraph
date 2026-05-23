"""port discover tests — all tiers mocked via _make_tiers() injection."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from socialgraph.cli.main import app
from socialgraph.paths import DataPaths
from socialgraph.port.discovery import DiscoveryResult
from socialgraph.port.state import PortCandidate, PortState

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_li_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


class FakeTierWithCandidate:
    """Always returns a candidate for any person."""

    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(
            handle=None,
            confidence=0.7,
            source="fake",
            candidates=[
                PortCandidate(
                    handle=f"{name.split()[0].lower()}_x",
                    display_name=name,
                    bio_preview="",
                    score=0.7,
                    rationale="",
                    source="fake",
                )
            ],
        )


class FakeTierAutoResolve:
    """Always auto-resolves (confidence >= 1.0)."""

    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(
            handle=f"{name.split()[0].lower()}_auto",
            confidence=1.0,
            source="fake_auto",
            candidates=[],
        )


class FakeTierMiss:
    """Never finds anything."""

    def discover(self, name, company, profile_url) -> DiscoveryResult:
        return DiscoveryResult(handle=None, confidence=0.0, source="fake_miss", candidates=[])


def test_port_discover_tier1_auto_resolves(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    _patch = "socialgraph.cli.port_discover_cmd._make_tiers"
    with patch(_patch, return_value=[FakeTierAutoResolve()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0, result.stdout
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    # Auto-resolved → queued directly, no needs_review
    assert state.counts()["queued"] >= 1
    assert state.counts()["needs_review"] == 0


def test_port_discover_tier2_sends_to_review(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    _patch = "socialgraph.cli.port_discover_cmd._make_tiers"
    with patch(_patch, return_value=[FakeTierWithCandidate()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    assert state.counts()["needs_review"] >= 1
    assert state.counts()["queued"] == 0


def test_port_discover_all_miss_marks_unresolved(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[FakeTierMiss()]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0
    paths = DataPaths(tmp_path / "data")
    state = PortState(paths.port_state)
    counts = state.counts()
    # All unresolved — MUST land in needs_review (with empty candidates) so they
    # surface in `port review` with the [t]ype handle manually option.
    # NOT in rejected (rejected = explicit user "no thanks" only).
    # connections_small.csv has 3 LinkedIn contacts; --limit 3 processes all of them
    assert counts["needs_review"] == 3
    assert counts["rejected"] == 0
    # Each unresolved entry has 0 candidates
    for entry in state.list_needs_review():
        assert entry.candidates == []


def test_port_discover_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["port", "discover", "--limit", "5"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()


def test_port_discover_skips_already_processed(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    _patch = "socialgraph.cli.port_discover_cmd._make_tiers"

    def _needs_review_count() -> int:
        return PortState(DataPaths(tmp_path / "data").port_state).counts()["needs_review"]

    with patch(_patch, return_value=[FakeTierWithCandidate()]):
        runner.invoke(app, ["port", "discover", "--limit", "3"])
        count_after_first = _needs_review_count()
        runner.invoke(app, ["port", "discover", "--limit", "3"])
        count_after_second = _needs_review_count()
    # Second run should not add new entries — already-processed persons are skipped
    assert count_after_second == count_after_first


def test_port_discover_no_tiers_configured(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_li_import(tmp_path)
    with patch("socialgraph.cli.port_discover_cmd._make_tiers", return_value=[]):
        result = runner.invoke(app, ["port", "discover", "--limit", "3"])
    assert result.exit_code == 0
    assert "no discovery tiers configured" in result.stdout.lower()
