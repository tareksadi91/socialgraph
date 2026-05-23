# SocialGraph — Personal Network Sovereignty Tool

**Status:** Design spec, MVP
**Date:** 2026-05-23
**Stack:** Python 3.11+ · Playwright · NetworkX (in-memory) · Typer · FastAPI · Next.js · Anthropic/OpenAI/Ollama LLM (optional)
**License:** MIT

---

## 1. Problem & Wedge

Professional networks are fragmented across LinkedIn, X, and others. Each platform is a walled garden — flat lists, algorithmic feeds, no portability, no programmatic access. Users can't:

- Own a canonical, queryable view of their own network
- Port their graph between platforms
- Detect change (job moves, dormancy, new mutuals) over time
- Run cross-platform analytics

**MVP wedge: bidirectional graph portability with sovereignty as the foundation.**

Sovereignty (own your data, leave anytime, round-trip lossless) is necessary but not sufficient. Differentiation comes from **porting** — using your owned graph to populate a network on another platform you join. Read-only sovereignty alone is just a fancy downloader.

---

## 2. Goals & Non-Goals

### MVP goals

1. **Ingest** LinkedIn + X via official data exports (ToS-clean primary path) and optional Playwright + LLM scrape enrichment
2. **Resolve identity** within and across platforms with conservative auto-merge + manual review queue
3. **Persist** as flat files on disk (source of truth); in-memory NetworkX projection for queries
4. **Track change** via append-only snapshot history; diff function reveals job changes, new connections, dormancy
5. **Port** LinkedIn graph → X follow queue with manual click-through follow flow (state machine ready for `--auto` later)
6. **Export** GraphML, JSON-LD, and full-bundle archives (with secret exclusion)
7. **Round-trip sovereignty**: `tar -czf backup.tgz data/ && nuke && tar -xzf backup.tgz && rebuild → identical graph`

### Non-goals (v2 backlog)

- NL query agent (LangGraph + Graphiti tools)
- Graph analytics (PageRank, Louvain, decay scoring) + Neo4j projection
- Graphiti layered on Neo4j (temporal queries, NL search)
- Scheduled sync (cron / APScheduler)
- X→LinkedIn port direction
- Semi-auto follow mode (`--auto` flag on follow queue)
- Web chat interface
- Interactive web dashboard (live graph viz, timeline, analytics)
- Engagement signals ingest (post likes, comments) → real decay measurement
- Bluesky, GitHub, other platform connectors
- Additional export formats (RDF, GEXF)
- Full temporal model (`valid_from`/`valid_until` edges) if snapshot diff proves insufficient
- Photo-hash merge signals (requires binary photo cache)
- Performance work for 100k+ node graphs
- Tiered LLM (Haiku for bulk, Sonnet for reasoning, in one config)

---

## 3. Architecture

```
                                ┌─────────────┐
                                │  config.yml │
                                │  env: refs  │
                                └──────┬──────┘
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│                              CLI (Typer)                                  │
│  init · import · scrape · login · merge-review · diff · port · export    │
│  viz · rebuild · status · link · unmerge · nuke · dev                    │
└────────────┬──────────────────────────────────────────┬──────────────────┘
             │                                          │
             │                                ┌─────────▼──────────┐
             │                                │  Next.js merge UI  │
             │                                │  FastAPI on 127.1  │
             │                                │  opt-in, no auth   │
             │                                └─────────┬──────────┘
             │                                          │
             │            both read/write same JSONL ───┘
             │                                          │
┌────────────▼──────────────────────────────────────────▼──────────────────┐
│                         Core (Python modules)                             │
│                                                                           │
│  ingest/                identity/             snapshot/        port/      │
│  ├ import_linkedin      ├ resolve             ├ write          ├ x_discover│
│  │  (Connections.csv)   ├ merge_score (LLM)   ├ diff (skip if  │ (needs   │
│  ├ import_x             ├ pending_queue       │  empty)        │  scrape) │
│  │  (following/         └ canonical_id        └ replay         ├ queue    │
│  │   follower.js only)                                          └ state_mach│
│  └ scrape/                                                                │
│    ├ playwright (card-boundary selectors)                                 │
│    ├ llm_postprocess (HTML chunk → fields)                                │
│    └ fallback_selectors (no-LLM path)                                     │
│                                                                           │
│  graph/ (in-memory NetworkX)      viz/        export/                     │
│  ├ load_from_snapshots            └ render_   ├ graphml                   │
│  ├ apply_merge_decisions             static_  ├ json_ld                   │
│  └ query (paths, neighbors)          html     └ bundle (secret-exclude)   │
└──────┬────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Flat files (source of truth)                          │
│                                                                          │
│  data/                                                                   │
│  ├ raw/                  ← gzipped HTML cache, CSVs, scoped X archive   │
│  │  └ {platform}/{run_id}/{card_i.html.gz, progress.json}               │
│  ├ parsed/               ← RawContact JSONL per ingest run              │
│  │  └ {platform}_{source}_{run_id}.jsonl                                │
│  ├ snapshots/            ← Immutable graph snapshots (full state)       │
│  │  └ {ts}.jsonl  (only written if diff != empty)                       │
│  ├ merge_decisions.jsonl ← Append-only audit; replay-deterministic IDs  │
│  ├ pending_merges.jsonl  ← Shared state for CLI prompt + web UI         │
│  ├ port_state.jsonl      ← Follow queue state machine                   │
│  ├ sync_log.jsonl        ← Operational events (start/end/errors)        │
│  ├ profiles/             ← Isolated Chromium profiles per platform      │
│  ├ backups/              ← Rolling N-day backups of merge log + index   │
│  ├ cache/                ← Optional pickled NetworkX projection         │
│  └ viz/                  ← Static HTML output (self-contained)          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Design principles

1. **Source of truth = flat files.** NetworkX projection is rebuildable; if it's lost, nothing real is lost.
2. **Raw → Parsed → Snapshot → Projection** is one-way. Edits to the in-memory graph never write back to flat files.
3. **All writes are JSONL appends or atomic file replaces.** No in-place mutation.
4. **Provenance per fact.** Each attribute traceable via `raw_id` → parsed JSONL → `raw_blob_path` → gzipped raw source.
5. **State machines persist.** Long flows (merge review, port follow) resume cleanly across interruptions.
6. **No daemon required for MVP.** Every command is one-shot. Optional web UI = opt-in subprocess.

---

## 4. Component Design

### 4.1 `ingest/`

**`import_linkedin`** — parse LinkedIn `Connections.csv` from official data export
- Input: CSV path
- Output: `parsed/linkedin_import_{run_id}.jsonl`
- Normalizes locale-varying headers via alias table (`"First Name" | "first name" | "Vorname"` → `first_name`)
- BOM-aware UTF-8; detects via `chardet`, transcodes to canonical UTF-8
- Records: `{schema_version, source: import, platform: linkedin, observed_at, ...}`

**`import_x`** — parse X archive ZIP
- Input: archive path
- Output: `parsed/x_import_{run_id}.jsonl`
- Selectively extracts: `following.js`, `follower.js`, `account.js` only. Tweets, DMs, likes discarded (privacy + scope)
- Strips JS-wrapper to JSON, version-detects archive format defensively
- Bails loudly on unknown format with detected version in error

**`scrape/`** — Playwright + LLM post-process pipeline (opt-in enrichment)
- `playwright_driver`: launches Chromium with isolated `data/profiles/{platform}/` user-data-dir (set up via `socialgraph login`). Headed by default so user can intervene on bot challenges. Paginates connections list, writes each card chunk to `raw/{platform}/{run_id}/card_{i}.html.gz`. Updates `progress.json` per card.
- `llm_postprocess`: streams cards from raw/, sends to LLM with `temp=0` + prompt cache, extracts RawContact fields → `parsed/{platform}_scrape_{run_id}.jsonl`. Per-card failure falls back to `fallback_selectors`.
- `fallback_selectors`: hardcoded selectors for known fields. Used when `--no-llm` flag set or per-card LLM failure. Lower coverage, deterministic.
- Rate-limit defaults: LinkedIn 5s + 2s jitter, X 3s + 1s jitter.

### 4.2 `identity/`

**`resolve`** — pure function: `list[RawContact] → list[(canonical_id, action)]`
- Within-platform: group by `platform_native_id` (URL slug / handle). Deterministic.
- Cross-platform candidates:
  - **Hard signals** (auto-merge + log with signal): bio cross-link (`x.com/` URL in LinkedIn bio, or vice versa); identical email.
  - **Soft signals** (push to `pending_merges.jsonl`): fuzzy name (Jaro-Winkler ≥ 0.94) + overlapping current company.
- All merge actions — auto and manual — appended to `merge_decisions.jsonl` with full signal set so replay reproduces.

**`merge_score`** — optional LLM scorer for ambiguous merges
- Input: two RawContacts
- Output: `{score: 0–1, rationale: str}`
- Used to rank pending queue only; never to auto-merge
- Score cached in `pending_merges.jsonl`; never re-queried on UI refresh
- Skipped entirely if LLM disabled

**`pending_queue`** — append-only JSONL
```
{candidate_id, person_a_raw_ids, person_b_raw_ids, signals: [...], score, rationale,
 status: "pending"|"confirmed"|"rejected", decided_at, decided_by}
```
Rejection memory: once rejected, future runs skip this pair via cached rejection set.

**`canonical_id`** — UUID generator, stable via log replay
- Event types: `create`, `merge`, `unmerge`, `link` (manual cross-platform)
- UUID written into the `create` event itself (not regenerated on replay)
- Replay applies events in order → identical state every time

**Per-field merge rules** (when same field observed differently across sources):

| Field | Authoritative order (highest → lowest) |
|---|---|
| full_name | linkedin_scrape > linkedin_import > x_scrape |
| company | linkedin_scrape > linkedin_import > x_scrape (inferred) |
| title | linkedin_scrape > linkedin_import |
| location_* | linkedin_scrape > x_scrape > linkedin_import (null) |
| headline | linkedin_scrape (only source) |
| bio | x_scrape (only source) |
| email | linkedin_import (only source) |
| mutual_count | linkedin_scrape (only source) |
| photo_url | latest scrape from either platform |
| follower_count | x_scrape (only source) |
| topics | union across all sources (LLM-derived) |
| seniority / function | LLM-derived; latest scrape wins (any platform) |
| industry | linkedin_scrape > linkedin_import |
| handle | x_import / x_scrape |

### 4.3 `snapshot/`

**`write`** — serialize current graph state to `snapshots/{ts}.jsonl`
- Single JSONL with discriminator per line:
  - `{"type": "node", "node_type": "Person", "canonical_id": ..., "attrs": {...}, "observations": [raw_id, ...]}`
  - `{"type": "node", "node_type": "Company", ...}`
  - `{"type": "edge", "edge_type": "CONNECTED_ON", "src": ..., "dst": ..., "attrs": {...}}`
- Atomic write: `tmp.jsonl` → fsync → rename
- **Skip rule**: skip write if no node added/removed, no edge added/removed, no field changed. Observation-timestamp-only changes don't count.
- **One snapshot per CLI invocation** (coalesce internal operations), not per internal write.

**`diff`** — pure function over two snapshot files
- Output: `{added_people, removed_people, changed_people: [{canonical_id, field, before, after}], added_edges, removed_edges, added_companies, removed_companies}`
- Powers `changed-jobs`, `new-connections`, `dormant` queries
- Time-window lookups: scan `snapshots/` filenames sorted by ts, pick closest ≤ target

**`replay`** — load snapshots in order → in-memory state up to a given timestamp
- Foundation for "graph as of date X" queries

### 4.4 `graph/` (in-memory projection)

**`load_from_snapshots`** — read latest snapshot → NetworkX MultiDiGraph
- Nodes: Person, Company
- Edges: CONNECTED_ON, FOLLOWS, WORKS_AT, MUTUAL_WITH
- All edge/node attrs preserved

**`apply_merge_decisions`** — replay merge log to ensure canonical IDs align with current state

**`query` API** (used by CLI subcommands):
- `neighbors(canonical_id, depth=N)`
- `shortest_path(a, b)`
- `at_company(company_id) → list[Person]`
- `changed_jobs(since: timedelta) → list[(Person, old, new)]`
- `new_connections(since: timedelta)`
- `dormant(threshold: timedelta)` — proxy via headline-last-changed for MVP

### 4.5 `port/`

**`x_discover`** — for each LinkedIn-only Person, find X handle
- **Cheap path first**: scan LinkedIn bio/contact-info for `x.com/` URL → hard-signal auto-resolve. (Requires LinkedIn scrape data; import-only users skip this path.)
- **Search path**: Playwright X session, search `"{full_name}" {current_company}`. Top N results. Score via name match + bio company match (X search snippets typically include bio preview — no separate profile fetch needed unless ambiguous).
- LLM scoring optional; without LLM, name-match heuristic only
- Rate-limited harder than scrape (8s + 3s jitter) due to detection sensitivity on burst search
- Output appended to `port_state.jsonl`:
  ```
  {canonical_id, candidates: [{x_handle, score, rationale}],
   status: "needs_review"|"resolved"|"none_found"}
  ```

**`queue`** — produce ordered follow queue from resolved entries
- Sort by `mutual_count` desc (LinkedIn-side metric = who you share most connections with)

**`state_machine`** — track each candidate:
```
needs_review → resolved → queued → opened → followed | skipped | error_*
```
- Persisted in `port_state.jsonl`, append-only
- Idempotent on resume: `port next` re-reads, finds next pending

**Manual follow flow**: `port next` opens X profile URL in real browser (`open` on macOS, `xdg-open` on Linux), prompts user `[f]ollowed / [s]kipped / [e]rror / [q]uit`, appends event.

### 4.6 `viz/`

**`render_static_html`** — latest snapshot → self-contained HTML with D3 force layout
- All data inlined; no fetch, no backend
- Filter sidebar: platform, company, mutual_count threshold, recency
- Scale safety: filter to top-N by mutual_count or k-core decomposition when graph > 5k nodes (D3 force chokes beyond)
- Output: `data/viz/network-{ts}.html`

### 4.7 `export/`

**`graphml`** — emit GraphML conforming to spec; importable by Gephi, Cytoscape
**`json_ld`** — emit JSON-LD with schema.org Person/Organization vocab
**`bundle`** — tar+gzip entire `data/`, excluding `.env*`, `*.key`, `*.pem`, `*_secret*`, `*credentials*`, `*token*`. Includes `config.yml` (non-secret refs only).

### 4.8 `cli/` (Typer)

```
socialgraph init                        # scaffold data/, copy .env/config examples
socialgraph login {linkedin|x}          # opens Chromium with isolated profile_dir, persist session
socialgraph import {linkedin|x} <path>  # ingest export file
socialgraph scrape {linkedin|x} [--no-llm] [--resume <run_id>] [--max-cards N]
socialgraph merge-review [--web]        # CLI prompts OR open Next.js
socialgraph link <id_a> <id_b>          # manual cross-platform link
socialgraph unmerge <canonical_id>      # split a confirmed merge
socialgraph diff <ts_a> <ts_b>          # snapshot diff
socialgraph who-at "<company>"
socialgraph path <id_a> <id_b>
socialgraph neighbors <id> --depth 2
socialgraph changed-jobs --since 30d
socialgraph new-connections --since 7d
socialgraph dormant --threshold 6mo
socialgraph port discover [--limit N]
socialgraph port review
socialgraph port queue
socialgraph port next
socialgraph export {graphml|json-ld|bundle} <path>
socialgraph viz
socialgraph rebuild                     # force reload from disk (clear pickle cache)
socialgraph status [--disk]             # counts, last sync, pending, last 3 errors
socialgraph nuke --confirm              # wipe data/ (two-prompt confirm)
socialgraph dev                         # FastAPI + Next.js dev servers
```

Exit codes:
```
0  success           4  bot_challenge
1  generic error     5  config_error
2  auth_required     6  lock_held
3  rate_limited      7  budget_exhausted
```

### 4.9 `web/` (opt-in)

- FastAPI on `127.0.0.1:8000`, Next.js on `127.0.0.1:3000`
- Single endpoint group `/api/merges/*`: list pending, get detail, confirm, reject, unmerge
- No auth; loopback-only binding documented as boundary condition
- Started by `socialgraph merge-review --web` or `socialgraph dev`; killed on Ctrl-C

---

## 5. RawContact Schema

```json
{
  "schema_version": 1,
  "raw_id": "{run_id}#{platform_native_id}",
  "platform": "linkedin | x",
  "source": "import | scrape",
  "platform_native_id": "linkedin-url-slug | x-handle",
  "profile_url": "https://...",
  "observed_at": "2026-05-23T10:00:00Z",
  "run_id": "scrape_linkedin_20260523T100000Z",

  "full_name": "...",
  "first_name": "...",
  "last_name": "...",
  "display_name": "...",
  "handle": "...",
  "email": "... | null",
  "verified": "bool | null",

  "headline": "... | null",
  "bio": "... | null",
  "location_raw": "... | null",
  "location_city": "... | null",
  "location_country": "... | null",
  "photo_url": "... | null",
  "language": "... | null",

  "current_company": "... | null",
  "current_company_url": "... | null",
  "current_title": "... | null",
  "industry": "... | null",

  "connected_on": "... | null",
  "follow_direction": "following | follower | mutual | null",
  "mutual_count": "int | null",
  "mutual_names_sample": ["..."],

  "follower_count": "int | null",
  "following_count": "int | null",

  "topics": ["..."],
  "seniority": "founder | ic | exec | ... | null",
  "function": "engineering | product | investor | ... | null",

  "raw_blob_path": "raw/linkedin/2026-05-23T10:00:00Z/card_42.html.gz"
}
```

**Schema versioning:** Reader detects `schema_version`, applies migrations in memory. Disk stays as written. Every version bump ships with a migration in `ingest/migrations/`.

**Field coverage by source:**

| Field | LI import | LI scrape | X import | X scrape |
|---|---|---|---|---|
| name | ✓ | ✓ | handle only | ✓ |
| headline / bio | ✗ | ✓ | ✗ | ✓ |
| company / title | ✓ | ✓ | ✗ | inferred |
| location | ✗ | ✓ | ✗ | ✓ |
| mutuals | ✗ | ✓ | ✗ | ✗ |
| follow counts | ✗ | ✗ | ✗ | ✓ |
| connected_on | ✓ | partial | timestamp | timestamp |
| topics (LLM) | ✗ | ✓ | ✗ | ✓ |

Import-only path = sparse but ToS-clean. Scrape adds richness with tradeoffs.

**Reprocessing:** `raw_blob_path` always points to gzipped raw source. Fields not extracted today can be re-extracted later by re-parsing raw — no re-scrape needed.

---

## 6. Data Flow

### 6.1 Fresh bootstrap (import-only)

```
socialgraph init
socialgraph import linkedin ~/Downloads/Connections.csv
socialgraph import x ~/Downloads/twitter-archive.zip
socialgraph status
```

Pipeline: `CSV/ZIP → ingest/* → RawContact JSONL → identity/resolve → snapshot/write → sync_log event`.

### 6.2 Scrape enrichment

```
socialgraph login linkedin             # one-time
socialgraph scrape linkedin
```

Pipeline: Playwright captures cards → raw/ gzipped → LLM (or selector fallback) parses → parsed/ → identity/resolve merges attributes into existing canonical IDs → snapshot.

### 6.3 Merge review (CLI)

```
socialgraph merge-review
```

Iterates `pending_merges.jsonl` filtered to status=pending. Side-by-side display + cached LLM rationale. Per item: `[y/n/s/u/q]`. Confirmed merges append `merge` event to `merge_decisions.jsonl`. Snapshot written once at CLI exit.

### 6.4 Port LinkedIn → X

```
socialgraph port discover --limit 100
socialgraph port review
socialgraph port queue
socialgraph port next        # loops until user quits
```

State machine in `port_state.jsonl` drives the loop. Resumable.

### 6.5 Round-trip sovereignty test

```
tar -czf backup.tgz data/
socialgraph nuke --confirm
tar -xzf backup.tgz
socialgraph status     # identical counts to pre-nuke
# Stronger: dump in-memory graph to canonical sorted JSONL, SHA256 must match
```

---

## 7. Error Handling

### 7.1 Browser session failures

| Failure | Detection | Recovery |
|---|---|---|
| Auth expired mid-scrape | Redirect to login page | Halt, exit code 2. Run `socialgraph login`, then `--resume <run_id>`. |
| Rate-limit page | Combined signals: expected content missing + redirect to non-target | Halt, exit code 3. Back off per default policy (24h pause then retry; LinkedIn rarely serves `Retry-After`). |
| ToS / bot challenge | "Verify you're human" detect | Halt, exit code 4. User intervenes (headed mode), re-runs. |
| Playwright crash | Process exit | Resume from `progress.json`, retry last card. |
| Per-page network timeout | Playwright timeout | Retry 3x exponential. After 3 fails, skip card with `card_skipped` event. |

### 7.2 LLM failures

| Failure | Recovery |
|---|---|
| API key invalid | Halt with error pointing to `.env`. |
| Provider down | Retry 3x exponential. After fail, fall through to `fallback_selectors` per card. Partial enrichment allowed. |
| Per-card malformed output | Retry once with stricter prompt. If fail, write raw_response to `parsed/{run_id}_errors.jsonl`, fall through to selectors. |
| Token budget exceeded | Persist progress, exit code 7. |

### 7.3 Import failures

| Failure | Recovery |
|---|---|
| LinkedIn CSV missing required column | Fail fast with diff vs expected alias table. |
| Malformed UTF-8 | Detect, transcode to UTF-8, log warning. |
| X archive missing `following.js` | Hard fail; archive is corrupt. |
| X archive unknown version | Best-effort parse with warnings; emit `format_unknown` event. |

### 7.4 Identity edge cases

| Case | Resolution |
|---|---|
| Wrong merge confirmed | `socialgraph unmerge <id>` appends unmerge event. |
| Same name + company collision | Soft signal → pending → user rejects → rejection memory caches the pair. |
| Job change shifts soft-signal threshold | Identity sticks once canonically merged; identity ≠ attributes. |
| Pseudonym across platforms | No auto-merge possible. `socialgraph link <li_id> <x_id>`. |
| False-positive hard-signal merge | `unmerge` is escape hatch. |

### 7.5 Snapshot / replay

| Case | Resolution |
|---|---|
| `merge_decisions.jsonl` truncated | Loud parse fail; restore from `data/backups/`. |
| Snapshot truncated | Atomic rename prevents most cases. On read: if final line not valid JSON or `type` discriminator missing, reject loud with the offending byte offset. |
| Schema version mismatch | Reader applies migration in memory; disk untouched. |

### 7.6 Port flow

| Case | Resolution |
|---|---|
| User followed manually outside tool | Next `port discover` detects existing follow, marks `already_followed`. |
| X account suspended/deleted | Open lands on 404; user marks `[e]rror` → `error_404` event. |
| Same person, changed handle | Keyed by canonical_id; latest handle wins. |
| Daily follow limit hit | User stops manually; state persists. (Semi-auto mode = v2.) |

### 7.7 Filesystem / concurrency

| Case | Resolution |
|---|---|
| Two CLI runs at once | Single `data/.lock` with PID. Second exits code 6. `--force-unlock` for stale. |
| Disk full | Atomic rename prevents corruption. Append failures truncate to last valid newline. |
| Permission denied | Fail fast with path + chmod suggestion. |
| Network share | Document as unsupported; local disk only. |

### 7.8 Config

| Case | Resolution |
|---|---|
| Missing env var | Fail fast at startup: `env:KEY referenced but not set`. |
| Unsupported LLM provider | Fail fast. |
| Missing profile_dir | Suggest `socialgraph login <platform>`. |

### 7.9 Privacy

| Case | Resolution |
|---|---|
| Email PII in logs | Redact `\w+@[\w.-]+\.\w+` by default. `--allow-pii-logs` opt-in. |
| Secrets in repo | `.gitignore`: `data/`, `.env*`, `*.key`. Ship `pre-commit` hook config. |
| Bundle leak | `export bundle` excludes `.env*`, `*.key`, `*.pem`, `*_secret*`, `*credentials*`, `*token*`. Tested. |
| Leave the project | `socialgraph nuke --confirm` wipes data/. Two-prompt confirm + clears stale lock. |

### 7.10 Principles

1. Fail loud, fail early — no silent partial success
2. Resume always — long ops persist progress incrementally
3. Provenance never lost — partial failures still record what was observed
4. No undo by deletion — all corrections are append-only events (unmerge, reject)
5. Errors are events — all failures append structured codes to `sync_log.jsonl`

---

## 8. Testing

### 8.1 Pyramid

70% unit, 25% integration, 5% E2E.

### 8.2 Unit (pure functions)

- `identity/resolve` — within-platform dedup, hard/soft signals, replay determinism
- `identity/canonical_id` — UUID stability across replays, create/merge/unmerge sequences
- `snapshot/diff` — added/removed/changed extraction; empty-diff detection
- `snapshot/replay` — log order matters; merge→unmerge→remerge correctness
- `ingest/import_linkedin` — header aliasing, locale variants, malformed rows
- `ingest/import_x` — version detection, JS-wrapper stripping, non-graph file exclusion
- `graph/load_from_snapshots` — NetworkX projection matches snapshot exactly
- `port/state_machine` — transition validity, idempotent replay
- `export/graphml` — schema validation, round-trip via `xml.etree`
- `export/bundle` — secret exclusion enforced

**Coverage targets:** 100% on `identity/`, `snapshot/replay`, `export/bundle`. 80% elsewhere.

### 8.3 Integration (full pipelines on fixtures)

Fixtures in `tests/fixtures/`:
```
linkedin/
  connections_small.csv
  connections_locale_fr.csv
  connections_unicode.csv
  scrape/
    card_normal.html.gz
    card_minimal.html.gz
    card_truncated.html.gz
    card_selectors_only.html.gz       # no-LLM mode test
    rate_limit_page.html.gz
    auth_redirect_page.html.gz
x/
  archive_v1.zip
  archive_v2.zip
  archive_corrupt.zip
  scrape/
    search_result_clean.html.gz
    search_result_ambiguous.html.gz
```

Golden files in `tests/golden/scrape/{name}.expected.json` — paired with each scrape fixture.

Tests cover: import-to-graph, cross-platform merge (hard + soft), scrape post-process, scrape resume, scrape auth/rate failures, field merge rules, provenance chain, pending merge round-trip, unmerge-then-remerge, port discover (bio-link + search paths), port state transitions, viz HTML validity.

### 8.4 E2E (CLI smoke + sovereignty)

- `test_e2e_fresh_install` — `init` scaffolds correctly
- `test_e2e_full_bootstrap` — import + import + status
- **`test_e2e_round_trip`** — **the sovereignty proof**
  - Run init + imports + scrape (mocked LLM via cassette)
  - Capture: in-memory graph dumped to canonical sorted JSONL + SHA256
  - Backup, nuke, restore, rebuild
  - Assert: SHA256 identical
- `test_e2e_lockfile_blocks_concurrent` — second process exits code 6
- `test_e2e_bundle_excludes_secrets` — wide pattern match: `.env*`, `*.key`, `*.pem`, `*_secret*`, `*credentials*`, `*token*`

### 8.5 Property-based (Hypothesis)

```
test_replay_deterministic               # arbitrary merge logs → same state every time
test_identity_resolve_idempotent        # duplicate inputs don't create extra IDs
test_diff_apply_invertible              # diff(s1, s2) applied to s1 == s2
test_scrape_resume_lossless             # random interruption + resume == full run
```

Budget: `max_examples=20, deadline=2000ms` in CI; local can crank higher.

### 8.6 LLM testing

- **Record/replay cassettes** in `tests/cassettes/`. CI replays; `--record` flag captures new ones. Recording guard: refuse if any path under `data/` matches files outside `tests/fixtures/`. Recording must point `data_dir` at a fixture directory only.
- **Mocked fallback mode** — selector-only path tested with `card_selectors_only.html.gz`.
- **Nightly with real LLM** — budget-capped (`LLM_NIGHTLY_BUDGET_USD=1.00`) on tiny fixture set. Catches prompt drift.

### 8.7 Browser testing

- No live LinkedIn/X traffic in default suite
- Playwright runs against `file://` URLs pointing to fixtures
- HTTP-level mocks via `playwright.route()` for redirect/error pages
- Real-browser smoke = `npm run smoke:real`, manual-only, pre-release

### 8.8 Chaos tests

`tests/chaos/`: inject random 500s, slow responses, mid-page disconnects via Playwright route mocks. Assert retry behavior + structured sync_log entries.

### 8.9 Schema migration tests

Every `schema_version` bump = fixture in OLD format + assertion that load produces correct NEW shape in memory. Disk untouched.

### 8.10 Pre-commit hooks

- `ruff format`/`check`
- `mypy` / `pyright`
- `gitleaks` (secret scan)
- Large-file guard (>1MB)
- Fixture PII scanner

### 8.11 CI matrix

| Job | When |
|---|---|
| Lint + typecheck (Python + TS) | every PR |
| Unit + integration + E2E (no live LLM, no live network) | every PR |
| Property-based (Hypothesis) | every PR |
| LLM cassettes replay | every PR |
| LLM live (tiny fixture set, budget-capped) | nightly |
| Chaos | nightly |
| Real browser smoke | manual pre-release |

### 8.12 Test deps

`pytest`, `pytest-cov`, `pytest-asyncio`, `hypothesis`, `playwright`, `vcrpy` (or custom cassette), `responses` (HTTP mocks).

---

## 9. Configuration

### 9.1 `.env.example`

```
# Optional. Skip if running offline / scrape-free / no LLM enrichment.

# LLM provider — pick one
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434     # local, no key

# Reserved for v2
X_BEARER_TOKEN=
NEO4J_PASSWORD=
```

### 9.2 `config.yml.example`

```yaml
llm:
  enabled: true

  # Recommended models by tier:
  #
  # CHEAP (best $/scrape):
  #   provider: anthropic, model: claude-haiku-4-5
  #   ≈ $5–10 for full LinkedIn scrape (5k connections)
  #
  # BALANCED (default):
  #   provider: anthropic, model: claude-sonnet-4-6
  #   ≈ $20–40 full scrape, stronger merge reasoning
  #
  # MAX QUALITY:
  #   provider: anthropic, model: claude-opus-4-7
  #   Overkill for bulk; use only if budget allows.
  #
  # OPENAI: provider: openai, model: gpt-4o-mini | gpt-4o
  #
  # OFFLINE (sovereignty-pure, slower, weaker on structured extraction):
  #   provider: ollama, model: qwen2.5:14b      # 8GB VRAM
  #   provider: ollama, model: llama3.3:70b     # 40GB VRAM
  #
  # NO LLM: set enabled: false. Uses selector-only scrape.
  provider: anthropic
  model: claude-sonnet-4-6
  api_key: env:ANTHROPIC_API_KEY
  temperature: 0
  cache: true

platforms:
  linkedin:
    enabled: true
    profile_dir: ./data/profiles/linkedin
    scrape:
      throttle_seconds: 5
      jitter: 2
      headed: true
  x:
    enabled: true
    profile_dir: ./data/profiles/x
    scrape:
      throttle_seconds: 3
      jitter: 1
      headed: true

port:
  x_discover:
    throttle_seconds: 8
    jitter: 3

storage:
  data_dir: ./data
  gzip_raw: true
  backups:
    rolling_days: 14

web:
  bind: 127.0.0.1
  api_port: 8000
  ui_port: 3000

privacy:
  allow_pii_logs: false
  strip_emails_on_import: false
```

---

## 10. Legal / Risk Notes

- **LinkedIn ToS** prohibits scraping even via your own logged-in browser session. Import path (official data export) is ToS-clean. Scrape path is at user's discretion; tool ships scrape disabled by default? *(See open question 11.1.)*
- **X ToS** grayer; X API access paywalled, manual follow flow (MVP) is just "you clicking follow," no automation risk in default mode.
- **PII**: LinkedIn export may include connections' emails (they consented to share). Stored locally only. No cloud sync, no telemetry. Bundle export and logs redact by default.
- **Single user**: MVP is solo-tool. Multi-user / SaaS is explicitly non-goal.

---

## 11. Open Questions

1. **Scrape disabled by default?** Should `socialgraph scrape` require an explicit `--i-understand-tos-risk` flag on first run? Recommend: yes, one-time persisted ack.
2. **Photo URL rot.** Store URL only in MVP. v2 cache toggle. Acceptable?
3. **`socialgraph dev`** scope: dev servers only, or include hot-reload watcher on FastAPI? Recommend: dev servers only for MVP.
4. **Test fixture sanitization script** — ship one? Recommend: yes, `scripts/sanitize_fixtures.py`.
5. **First-class no-LLM mode** UX — should `enabled: false` print a banner reminding which fields will be null on scrape? Recommend: yes, one-time.

---

## 12. Milestone plan

| M | Deliverables | Why |
|---|---|---|
| **M1** | `init`, `import linkedin`, `import x`, RawContact schema, parsed/ JSONL, sync_log | Prove ingest, ToS-clean path works end-to-end. *Demo:* `parsed/` files inspectable; no graph yet. |
| **M2** | `identity/resolve` (within-platform), `canonical_id` log, `snapshot/write` + `diff`, NetworkX projection, `status`, basic CLI queries (`who-at`, `neighbors`) | Sovereignty core: round-trip works. *Demo:* LinkedIn-only graph + round-trip E2E green. |
| **M3** | `merge-review` CLI (no web UI yet), cross-platform identity (hard + soft signals), `pending_merges.jsonl`, `unmerge`, `link` | Cross-platform merge correctness. *Demo:* merged LinkedIn+X graph; round-trip still green. |
| **M4** | `scrape/` (Playwright + LLM + selector fallback), `login`, resume, headed mode | Enrichment with no LLM lock-in. *Demo:* scraped headlines, locations, mutuals visible in `status`. |
| **M5** | `port discover`, `port review`, `port queue`, `port next`, `port_state.jsonl` | The wedge: portability. *Demo:* manual follow flow walked end-to-end against fixture network. |
| **M6** | `export graphml`, `export json-ld`, `export bundle`, `viz`, `nuke`, `rebuild` | Sovereignty UX polish. *Demo:* GraphML opens in Gephi; bundle restore reproduces SHA256. |
| **M7** | FastAPI + Next.js merge review web UI, `dev`, `merge-review --web` | Visual merge surface. *Demo:* side-by-side merge UI on localhost. |

Each milestone ships with its own unit + integration + E2E tests. Round-trip E2E lives at M2 and re-runs at every later milestone.

---

## 13. Open-source contribution surface

- **New ingest sources** — implement `ingest/` module conforming to `RawContact` schema, add migration if needed
- **New connectors** (Bluesky, GitHub, Mastodon) — implement Playwright + LLM postprocess pair in `scrape/`
- **LLM adapters** — extend config provider list
- **Export formats** — add modules to `export/`
- **UI themes** — Next.js component layer isolated

---

## 14. v2 Backlog (deferred from MVP)

- NL query agent (LangGraph + Graphiti tools)
- Graph analytics (PageRank, Louvain, decay) + Neo4j projection
- Graphiti layered on Neo4j (temporal queries, NL search)
- Scheduled sync (cron / APScheduler)
- X→LinkedIn port direction
- Semi-auto follow mode (`--auto` flag) with bot-detection backoff
- Web chat interface
- Interactive web dashboard (live graph viz, timeline, analytics)
- Engagement signals ingest (post likes, comments) → real decay
- Bluesky, GitHub, Mastodon connectors
- RDF, GEXF export formats
- Full temporal model (`valid_from`/`valid_until`) if snapshot diff proves insufficient
- Photo-hash merge signals (binary photo cache)
- Performance work for 100k+ node graphs
- Tiered LLM (Haiku bulk + Sonnet reasoning in one config)
- `socialgraph stats --disk` and snapshot pruning
- Cassette auto-update tooling
- Mutation testing on `identity/` module

---

## 15. Acceptance criteria for MVP

1. Fresh user: `init` → `import linkedin` → `import x` → `status` runs in < 2 minutes with a 5k-connection LinkedIn export
2. `scrape linkedin` on 100 connections completes successfully, fills headline/location/mutual_count, with LLM disabled it still fills headline/company via fallback selectors
3. Cross-platform identity resolution: from a fixture with 5 hard-signal pairs and 10 soft-signal pairs → 5 auto-merged, 10 in pending queue, deterministic replay
4. `merge-review` CLI: confirm one, reject one, unmerge one, all events visible in `merge_decisions.jsonl`
5. `port discover --limit 20` produces a queue with at least 10 resolved candidates on the fixture LinkedIn graph; manual click-through advances state machine correctly
6. `export bundle` produces a tar.gz that, when extracted to a fresh `data/` dir, allows the in-memory graph (loaded fresh from disk, dumped to canonical sorted JSONL) to produce an identical SHA256 vs the pre-export dump
7. Round-trip E2E test passes deterministically across 10 consecutive runs
8. `socialgraph status` after a crashed scrape shows the partial run + actionable next step
9. Concurrent CLI runs are blocked by lockfile with exit code 6
10. CI passes: lint, typecheck, unit, integration, E2E, property, cassette replay — all green on every PR
