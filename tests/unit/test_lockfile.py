import os
from pathlib import Path

import pytest

from socialgraph.exit_codes import ExitCode
from socialgraph.lockfile import Lock, LockHeldError


def test_lock_acquires_and_releases(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with Lock(lock_path):
        assert lock_path.is_file()
        contents = lock_path.read_text()
        assert str(os.getpid()) in contents
    assert not lock_path.is_file()


def test_lock_blocks_second_acquire(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    with Lock(lock_path):
        with pytest.raises(LockHeldError) as exc:
            with Lock(lock_path):
                pass
        assert exc.value.exit_code == ExitCode.LOCK_HELD
        assert "pid" in str(exc.value).lower()


def test_lock_clears_stale_lock(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    # stale lock pointing at impossibly high PID
    lock_path.write_text('{"pid": 999999, "started_at": "x", "hostname": "h"}')
    with Lock(lock_path):
        # should re-acquire because pid not running
        assert str(os.getpid()) in lock_path.read_text()


def test_lock_force_unlock(tmp_path: Path):
    lock_path = tmp_path / ".lock"
    lock_path.write_text('{"pid": 1, "started_at": "x", "hostname": "h"}')
    with Lock(lock_path, force_unlock=True):
        assert str(os.getpid()) in lock_path.read_text()
