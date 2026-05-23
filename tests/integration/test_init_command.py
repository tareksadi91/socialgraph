from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()


def test_init_scaffolds_dirs_and_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Copy example files into the temp project root so init has sources to copy from
    (tmp_path / ".env.example").write_text("ANTHROPIC_API_KEY=\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.stdout

    assert (tmp_path / ".env").is_file()
    assert (tmp_path / "config.yml").is_file()
    assert (tmp_path / "data").is_dir()
    assert (tmp_path / "data" / "raw").is_dir()
    assert (tmp_path / "data" / "parsed").is_dir()
    assert (tmp_path / "data" / "snapshots").is_dir()


def test_init_is_idempotent(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("X=\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")

    runner.invoke(app, ["init"])
    (tmp_path / ".env").write_text("CUSTOMIZED=true\n")  # user customizes
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    # init must NOT overwrite a user-edited .env
    assert "CUSTOMIZED=true" in (tmp_path / ".env").read_text()
