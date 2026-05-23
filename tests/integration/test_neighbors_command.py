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
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
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
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["neighbors", "any-id"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()
