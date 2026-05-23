from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
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


def test_status_shows_graph_counts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "persons" in result.stdout
    assert "companies" in result.stdout


def test_status_shows_pending_merges_count(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Should show pending merges section (count may be 0 with fixture data)
    assert "pending" in result.stdout.lower() or "merge" in result.stdout.lower()
