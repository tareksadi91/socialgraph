"""Process exit codes for the socialgraph CLI."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Structured exit codes returned by every CLI command.

    These form a stable contract with shell scripts and CI:

    - SUCCESS:           Command completed normally
    - GENERIC_ERROR:     Unclassified failure
    - AUTH_REQUIRED:     Platform session expired; run `socialgraph login`
    - RATE_LIMITED:      Platform throttled us; back off and retry later
    - BOT_CHALLENGE:     Anti-bot interstitial detected; user must intervene
    - CONFIG_ERROR:      Missing/invalid config or env var
    - LOCK_HELD:         Another `socialgraph` instance is running
    - BUDGET_EXHAUSTED:  LLM token budget cap hit; raise limit or switch model
    """

    SUCCESS = 0
    GENERIC_ERROR = 1
    AUTH_REQUIRED = 2
    RATE_LIMITED = 3
    BOT_CHALLENGE = 4
    CONFIG_ERROR = 5
    LOCK_HELD = 6
    BUDGET_EXHAUSTED = 7
