# SocialGraph

Personal network sovereignty tool. Own your social graph, leave any platform anytime.

**Status:** MVP M1 — ingest scaffold. LinkedIn and X official data exports → inspectable JSONL.

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
socialgraph init
socialgraph import linkedin ~/Downloads/Connections.csv
socialgraph import x ~/Downloads/twitter-archive.zip
socialgraph status
```

Parsed records land in `data/parsed/*.jsonl`. Inspect with `jq` or `cat`.

## Architecture

See `docs/superpowers/specs/2026-05-23-socialgraph-design.md`.

## Milestones

- **M1** (this milestone): import LinkedIn + X, JSONL output, status command
- M2: identity resolution + snapshot history + in-memory graph
- M3: cross-platform merge + review CLI
- M4: scrape enrichment (Playwright + LLM)
- M5: LinkedIn → X port flow
- M6: export formats + viz
- M7: web merge UI

## License

MIT
