from pathlib import Path

from socialgraph.paths import DataPaths


def test_paths_resolves_subdirs(tmp_path: Path):
    paths = DataPaths(tmp_path)
    assert paths.root == tmp_path
    assert paths.raw == tmp_path / "raw"
    assert paths.parsed == tmp_path / "parsed"
    assert paths.snapshots == tmp_path / "snapshots"
    assert paths.profiles == tmp_path / "profiles"
    assert paths.backups == tmp_path / "backups"
    assert paths.cache == tmp_path / "cache"
    assert paths.viz == tmp_path / "viz"
    assert paths.lock_file == tmp_path / ".lock"
    assert paths.merge_decisions == tmp_path / "merge_decisions.jsonl"
    assert paths.pending_merges == tmp_path / "pending_merges.jsonl"
    assert paths.port_state == tmp_path / "port_state.jsonl"
    assert paths.sync_log == tmp_path / "sync_log.jsonl"
    assert paths.tos_ack == tmp_path / ".tos_ack"
    assert paths.no_llm_ack == tmp_path / ".no_llm_ack"


def test_paths_ensure_creates_all_dirs(tmp_path: Path):
    paths = DataPaths(tmp_path)
    paths.ensure()
    for d in [
        paths.raw,
        paths.parsed,
        paths.snapshots,
        paths.profiles,
        paths.backups,
        paths.cache,
        paths.viz,
    ]:
        assert d.is_dir()


def test_paths_parsed_for_run(tmp_path: Path):
    paths = DataPaths(tmp_path)
    p = paths.parsed_for_run("linkedin", "import", "run123")
    assert p == tmp_path / "parsed" / "linkedin_import_run123.jsonl"


def test_paths_raw_run_dir(tmp_path: Path):
    paths = DataPaths(tmp_path)
    p = paths.raw_run_dir("linkedin", "run123")
    assert p == tmp_path / "raw" / "linkedin" / "run123"
