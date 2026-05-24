# SocialGraph

Personal network sovereignty tool. Own your social graph, leave any platform anytime.

**Status:** M5 complete — LinkedIn → X handle discovery + follow queue.

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env        # fill in API keys
socialgraph init
socialgraph login linkedin  # one-time browser login
socialgraph import linkedin ~/Downloads/Connections.csv
socialgraph port discover   # find X handles for LinkedIn contacts
socialgraph port review     # pick the right handle per person
socialgraph port queue      # see upcoming follow list
socialgraph port next       # walk through follow queue one by one
```

## Port discovery tiers

Handle discovery runs up to 3 tiers in order, stopping as soon as one resolves:

| Tier | Source | Requires |
|------|--------|----------|
| 1 | LinkedIn contact-info overlay (Playwright scrape) | `socialgraph login linkedin` |
| 2 | Google Custom Search Engine (`*.x.com/*`) | `GOOGLE_CSE_API_KEY` + `GOOGLE_CSE_ID` in `.env` |
| 3 | Apollo People Match | `APOLLO_API_KEY` in `.env` |

Tier 1 auto-resolves (confidence 1.0) — skips manual review. Tiers 2–3 put candidates in the review queue for `port review`.

## Setup

```bash
# .env keys (copy from .env.example)
GOOGLE_CSE_API_KEY=   # Google Cloud → Credentials → API key (needs Custom Search API enabled)
GOOGLE_CSE_ID=        # programmablesearch.google.com → CSE cx value
APOLLO_API_KEY=       # app.apollo.io → Settings → API Keys (10K free req/month)
```

## All commands

```
socialgraph import linkedin <path>   # import Connections.csv or archive zip
socialgraph import x <path>          # import X archive zip
socialgraph status                   # counts, last imports, errors
socialgraph rebuild                  # rebuild graph from parsed JSONL
socialgraph who-at <company>         # list connections at a company
socialgraph neighbors <id>           # company colleagues of a person
socialgraph merge-review             # interactive cross-platform merge
socialgraph link <id-a> <id-b>       # explicitly link two identities
socialgraph unmerge <id>             # split wrongly-merged person
socialgraph login <platform>         # persist browser session (linkedin | x)
socialgraph port discover            # run handle discovery
socialgraph port review              # review candidates, pick or type handle
socialgraph port queue               # show follow queue
socialgraph port next                # walk follow queue one profile at a time
```

## Architecture

See `docs/superpowers/specs/`.

## Milestones

- **M1** done: import LinkedIn + X, JSONL output, status command
- **M2** done: identity resolution + snapshot history + in-memory graph
- **M3** done: cross-platform merge + review CLI
- **M4** done: scrape enrichment (Playwright)
- **M5** done: LinkedIn → X port flow (4-tier discovery + follow queue)
- M6: export formats + viz
- M7: web merge UI

## License

MIT
