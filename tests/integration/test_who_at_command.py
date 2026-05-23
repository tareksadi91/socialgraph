from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"


def _setup_with_import(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])


def test_who_at_finds_connections(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    result = runner.invoke(app, ["who-at", "Acme Co"])
    assert result.exit_code == 0, result.stdout
    assert "Alice Example" in result.stdout
    assert "Carol Test" in result.stdout
    assert "Bob Sample" not in result.stdout  # Bob is at Beta Corp


def test_who_at_no_results(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_with_import(tmp_path)
    result = runner.invoke(app, ["who-at", "Nonexistent Corp"])
    assert result.exit_code == 0
    assert "no connections" in result.stdout.lower() or "0" in result.stdout


def test_who_at_no_graph(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["who-at", "Acme"])
    assert result.exit_code == 0
    assert "no graph" in result.stdout.lower() or "import" in result.stdout.lower()
