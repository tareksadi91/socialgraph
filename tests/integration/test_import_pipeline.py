from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def _setup_project(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")
    runner.invoke(app, ["init"], catch_exceptions=False)


def test_import_linkedin_writes_parsed_jsonl(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 0, result.stdout
    parsed_files = list((tmp_path / "data" / "parsed").glob("linkedin_import_*.jsonl"))
    assert len(parsed_files) == 1
    lines = parsed_files[0].read_text().splitlines()
    assert len(lines) == 3  # Alice, Bob, Carol


def test_import_x_writes_parsed_jsonl(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    assert result.exit_code == 0, result.stdout
    parsed_files = list((tmp_path / "data" / "parsed").glob("x_import_*.jsonl"))
    assert len(parsed_files) == 1
    lines = parsed_files[0].read_text().splitlines()
    assert len(lines) == 3  # bob_x, carol_x, dan_x


def test_import_appends_sync_log_event(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    log = (tmp_path / "data" / "sync_log.jsonl").read_text().splitlines()
    events = [line for line in log if line.strip()]
    assert any('"event": "import.start"' in line for line in events)
    assert any('"event": "import.end"' in line for line in events)


def test_import_unknown_platform_exits_nonzero(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    result = runner.invoke(app, ["import", "myspace", str(LINKEDIN_FIXTURE)])
    assert result.exit_code != 0


def test_import_blocks_when_lock_held(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_project(tmp_path)
    # simulate held lock from current process (which IS alive, so not stale)
    lock = tmp_path / "data" / ".lock"
    import json
    import os

    lock.write_text(json.dumps({"pid": os.getpid(), "started_at": "x", "hostname": "h"}))
    result = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert result.exit_code == 6
