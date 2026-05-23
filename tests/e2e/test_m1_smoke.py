"""M1 smoke: fresh project → init → import LI → import X → status. Demoable end-to-end."""

import json
from pathlib import Path

from typer.testing import CliRunner

from socialgraph.cli.main import app

runner = CliRunner()

PROJECT_ROOT = Path(__file__).parents[2]
LINKEDIN_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "linkedin" / "connections_small.csv"
X_FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "x" / "archive_v1.zip"


def test_m1_full_bootstrap(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env.example").write_text("\n")
    (tmp_path / "config.yml.example").write_text("storage:\n  data_dir: ./data\n  gzip_raw: true\n")

    # 1. init
    r = runner.invoke(app, ["init"])
    assert r.exit_code == 0
    assert (tmp_path / "data").is_dir()

    # 2. import linkedin
    r = runner.invoke(app, ["import", "linkedin", str(LINKEDIN_FIXTURE)])
    assert r.exit_code == 0
    li_files = list((tmp_path / "data" / "parsed").glob("linkedin_import_*.jsonl"))
    assert len(li_files) == 1
    li_records = [json.loads(line) for line in li_files[0].read_text().splitlines()]
    assert len(li_records) == 3
    assert all(r["platform"] == "linkedin" for r in li_records)
    assert all(r["source"] == "import" for r in li_records)
    assert all(r["schema_version"] == 1 for r in li_records)
    assert all(r["raw_id"].endswith(r["platform_native_id"]) for r in li_records)

    # 3. import x
    r = runner.invoke(app, ["import", "x", str(X_FIXTURE)])
    assert r.exit_code == 0
    x_files = list((tmp_path / "data" / "parsed").glob("x_import_*.jsonl"))
    assert len(x_files) == 1
    x_records = [json.loads(line) for line in x_files[0].read_text().splitlines()]
    assert len(x_records) == 3
    handles = sorted(r["handle"] for r in x_records)
    assert handles == ["bob_x", "carol_x", "dan_x"]

    # 4. status output sane
    r = runner.invoke(app, ["status"])
    assert r.exit_code == 0
    assert "linkedin: 3 contacts" in r.stdout
    assert "x: 3 contacts" in r.stdout

    # 5. sync_log captured both runs
    log = (tmp_path / "data" / "sync_log.jsonl").read_text().splitlines()
    events = [json.loads(line) for line in log if line.strip()]
    starts = [e for e in events if e["event"] == "import.start"]
    ends = [e for e in events if e["event"] == "import.end"]
    assert len(starts) == 2
    assert len(ends) == 2
