from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERIC_ERROR = 1
    AUTH_REQUIRED = 2
    RATE_LIMITED = 3
    BOT_CHALLENGE = 4
    CONFIG_ERROR = 5
    LOCK_HELD = 6
    BUDGET_EXHAUSTED = 7
