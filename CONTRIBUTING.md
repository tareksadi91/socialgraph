# Contributing

## Setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
```

## Tests

```bash
pytest                  # full suite
pytest tests/unit       # unit only
pytest -k import_linkedin -v
```

## Lint + typecheck

```bash
ruff check src tests --fix
ruff format src tests
pyright src
```

## Adding a fixture from real data

Real LinkedIn / X data must be sanitized before being committed. A sanitization helper will ship at `scripts/sanitize_fixtures.py` (M4+).

For M1: do not commit real data. Use synthetic fixtures in `tests/fixtures/`.

## Commit style

Conventional commits: `feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`.
