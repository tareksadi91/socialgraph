from socialgraph.exit_codes import ExitCode


def test_exit_codes_have_expected_values():
    assert ExitCode.SUCCESS == 0
    assert ExitCode.GENERIC_ERROR == 1
    assert ExitCode.AUTH_REQUIRED == 2
    assert ExitCode.RATE_LIMITED == 3
    assert ExitCode.BOT_CHALLENGE == 4
    assert ExitCode.CONFIG_ERROR == 5
    assert ExitCode.LOCK_HELD == 6
    assert ExitCode.BUDGET_EXHAUSTED == 7


def test_exit_codes_have_no_duplicate_values():
    values = [c.value for c in ExitCode]
    assert len(set(values)) == len(values), "exit codes must be unique"
