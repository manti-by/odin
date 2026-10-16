---
title: 'MCP server review and project-agnostic refactor'
date: '2026-10-11'
type: code-review
status: resolved
session_id: ses_ed37da56fffeLy1sBdZaanKdjG
services: [mcp-server, tools]
branch: master
tickets: []
tags: [mcp, review, refactor, caching, paths, project-agnostic, tests]
related: [2026-09-23-relay-mode-compute-on-read.md]
---

# MCP server review and project-agnostic refactor

## TL;DR

Reviewed an MCP server copied from another project, found **two silent data-corruption bugs** that
returned confidently wrong answers rather than errors, fixed them, then made the server project
agnostic. The worst bug: the wiki tools were reading a *different repository's* wiki because
`Path(__file__).resolve().parents[3]` was off by one after the package moved — every wiki query
answered from the umbrella repo's 2 pages instead of odin's 27, with no error. Added 208 tests and
replaced 10 loose module-global cache variables with one frozen `Corpus` snapshot. 603 tests pass.

**Later the same day** (see Update below): ran `wiki-dedup` (no duplicates), `wiki-consistency`
(fixed 2 superseded claims, repaired 24 one-way cross-links, rebuilt `INDEX.md`), an `AGENTS.md`
audit (2 wrong commands, 5 stale entries, 4 missing), and finally fixed all **8 unresolved CodeRabbit
threads on PR #41** — including replacing the database tool's column denylist with an allow-list and
a real off-by-one in `tail_file` that returned truncated log lines. 621 tests pass.

## Findings

Seven issues found, ordered by severity. The first two were live and silent; the rest were latent
or cleanup.

### 1. Wiki tools read the wrong repository — **critical**

**File:** `mcp_server/tools/wiki.py:18`
**Severity:** critical — silent, wrong data, no error

```python
PROJECT_ROOT = Path(__file__).resolve().parents[3]  # -> /home, not /home/odin
PAGES_ROOT = PROJECT_ROOT / "wiki" / "pages"
```

The package moved from `odin/tools/` to `mcp_server/tools/`, shifting the directory depth by one.
`parents[2]` is the repo root; `parents[3]` is its *parent*. So `wiki_search`, `wiki_list_pages` and
`wiki_get_page` all served `~/www/m2/home/wiki/pages` — 2 pages belonging to the umbrella repo —
instead of odin's own 27.

The nasty part: the wrong path **exists**, so `is_dir()` passed and nothing crashed. The tools just
answered from the wrong corpus with total confidence.

- **Fix:** `PROJECT_ROOT` corrected, and consolidated into `mcp_server/config.py` so there is exactly
  one place that resolves paths (see finding 6).

### 2. Docstring tool indexed only itself — **critical**

**File:** `mcp_server/tools/docstrings.py:19`
**Severity:** critical — tool could not answer any question

```python
DOCSTRING_ROOT = Path(__file__).resolve().parents[1]  # -> mcp_server/, not odin/
```

Same depth shift. `parents[1]` from `mcp_server/tools/docstrings.py` is the `mcp_server` package
itself, so the index covered only the MCP server and could say nothing about the odin app.

- **Fix:** index the `odin` package so qualified names stay `odin.apps...`, matching the example in
  the tool's own description.

### 3. `docstring_search` could not find functions by name — **high**

**File:** `mcp_server/tools/docstrings.py:153`
**Severity:** high — the tool's primary use case silently failed

The qualified name is tokenized with dots *inside* tokens, so `odin.apps.relays.models.Relay.get_target_state`
became a single token. A search for `get_target_state` matched nothing in the name field — which is
the *highest-weighted* field at boost 10.0.

```python
# query "get_target_state"        -> []           (no match)
# query "compute target state"    -> ranked fine  (matched the docstring prose instead)
```

Search worked only by accident, via prose in docstrings.

- **Fix:** expand dots to spaces in **both** the indexed name and the query, keeping the two
  symmetric:

```python
count_field(text=function.qualified_name.replace(".", " "))  # index
terms = tokenize(query=query.replace(".", " "))  # query
```

Both `get_target_state` and `Relay.get_target_state` now hit the name field.

### 4. Cache handed out its live internals — **medium, latent**

**File:** `mcp_server/tools/wiki.py` (five module globals per tool)
**Severity:** medium — not reachable today, but fragile

Ten globals (`_cached_fingerprint`, `_cached_pages`, `_cached_documents`, `_cached_stats`,
`_cached_pages_root`) had to be kept in lockstep, and `load_pages()` returned `_cached_pages`
*itself* on a cache hit. Reproduced:

```
2nd call returns the live global object? True
GHOST PERSISTED IN CACHE -> True     # 'injected.md' survived every reload
```

A caller appending to the result poisoned the cache permanently. Separately, `search_pages()` read
back three *different* globals after calling `load_pages()`, so a partial update caused
`ValueError: zip() argument 2 is shorter than argument 1` — and `zip(strict=True)` only catches
length mismatches, so a same-length mismatch would have scored against the wrong corpus.

To be fair to the original code: neither was reachable in production. Nothing mutated the list, and
`load_pages()` had no `await`, so the single-threaded anyio loop cannot interleave two calls
mid-sequence. It was safe *by accident* — correctness depended on a convention nothing enforced.

- **Fix:** one frozen dataclass, published in a single assignment (see "Cache refactor" below).

### 5. Database tools connected before validating arguments — **medium**

**File:** `mcp_server/tools/database.py:368`
**Severity:** medium — poor errors, needless I/O

```python
pool = await get_db_pool()        # opened first
if name == "query_table":
    table_name = args.get("table_name")
    if not table_name:            # validated second
```

A malformed call surfaced as the opaque `"Database operation failed"` instead of
`"table_name is required"`, and opened a connection for a request that could never succeed.

- **Fix:** validate arguments before touching the pool.

### 6. Project-specific values scattered across the server — **medium**

**File:** `mcp_server/tools/database.py:48`, plus both tool modules
**Severity:** medium — blocked reuse, one hard `odin` import

`from odin.settings.base import DATABASES` sat inside `get_db_pool()`, and each tool computed its own
`parents[N]` root — exactly the fragile pattern that caused findings 1 and 2.

- **Fix:** every project-specific value consolidated into `mcp_server/config.py`, each overridable by
  env var. See "Project-agnostic refactor".

### 7. Dead code carried over from the source project — **low**

**Severity:** low

The demetra path vocabulary (`WIKI_SERVICE_PACKAGES`, `WIKI_AREA_PREFIXES`, `WIKI_AREA_FILES`) came
across with the copy and was referenced by nothing; its comments pointed at a `demetra/services/`
tree and a test that did not exist here. Removed, along with unused `aiofiles`/`slugify` dependencies
(nothing imports them; `mcp` needs neither) and a redundant `_tokenize` passthrough.

## Summary

- **1** — critical — `mcp_server/tools/wiki.py` — wiki tools read the parent repo's wiki
- **2** — critical — `mcp_server/tools/docstrings.py` — docstring index covered only `mcp_server/`
- **3** — high — `mcp_server/tools/docstrings.py` — name search never matched the name field
- **4** — medium — wiki/docstrings — cache leaked its live list; globals could split-brain
- **5** — medium — `mcp_server/tools/database.py` — pool opened before argument validation
- **6** — medium — multiple — project values scattered; hard `odin.settings` import
- **7** — low — `mcp_server/config.py` — dead demetra vocabulary and unused deps

## Cache refactor

Replaced the ten globals with a single frozen snapshot in `mcp_server/corpus.py`:

- **`Corpus[T]`** — frozen dataclass holding `root`, `fingerprint`, `items`, `documents`, `stats`
  together. One assignment publishes it, so no reader can observe a half-updated corpus.
- **`CorpusCache[T]`** — generic, single-slot, invalidates on an mtime+size fingerprint.
- **`rank()`** — shared scoring, previously duplicated in both tools.
- **`Ranked[T]`** — frozen, replacing loose `(function, score, terms)` tuples.

Items are `tuple`, so callers cannot write through what they were handed. Re-verified against the
original reproductions:

```
append blocked  -> AttributeError
cache contents  -> ['a.md', 'b.md']      # ghost gone
all three agree? True                    # items == documents == stats.document_count
```

## Project-agnostic refactor

All project-specific values now live in one place, each env-overridable:

```python
PROJECT_NAME = os.getenv("MCP_PROJECT_NAME", "odin")
SERVER_NAME = os.getenv("MCP_SERVER_NAME", f"{PROJECT_NAME.upper()} MCP Server")
DJANGO_SETTINGS_MODULE = os.getenv("MCP_DJANGO_SETTINGS", f"{PROJECT_NAME}.settings.base")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = Path(os.getenv("MCP_SOURCE_ROOT", PROJECT_ROOT / PROJECT_NAME))
PAGES_ROOT = Path(os.getenv("MCP_PAGES_ROOT", PROJECT_ROOT / "wiki" / "pages"))
LOG_ROOT = Path(os.getenv("MCP_LOG_ROOT", f"/var/log/{PROJECT_NAME}"))
```

Three things collapsed into config rather than becoming new indirection:

- **Path math.** One `parents[1]`, resolved once — no per-module `parents[N]` to get wrong.
- **`from odin.settings.base import DATABASES`**, now `database_config()` in config.
- **The `docstring_get` description example**, derived from `SOURCE_ROOT.name` instead of hardcoded.

Verified by pointing the server at a throwaway project with a different package name, wiki and log
directory — only env vars changed:

```
server name: ACME MCP Server
docstring_search -> 1. mypkg.core.widget_count (score 0.565) | mypkg/core.py:L1
wiki_search      -> 1. notes.md (score 0.571) | Widget notes
```

Deliberately not done, to avoid overengineering: no plugin/registry layer for five constants, and
no env-fallback in `database_config()`. An earlier version of that function swallowed any import
error and fell back to `POSTGRES_*` — masking real misconfiguration behind a fallback that happened
to work. It now imports and fails loudly.

## Test Results

Added `mcp_server/tests/` — **208 tests**, no database required. Fakes the log/wiki/source roots via
`monkeypatch` and resets the corpus caches between tests.

The regression tests were verified by reintroducing each bug with `sed`: restoring `parents[3]` made
3 `test_paths.py` tests fail; reverting the name-tokenization fix made 4 `test_docstrings.py` tests
fail.

- **603 pass** total (395 pre-existing Django + 208 new) — `uv run pytest mcp_server/tests/ odin/`
- **ruff** — all checks passed
- **ty** — all checks passed
- **bandit** — passed
- **pre-commit** — all hooks passed
- **End-to-end** — verified over real stdio JSON-RPC: initialize handshake, `get_table_count` →
  `count: 10`, `docstring_search` and `wiki_search` returning correctly ranked results

---

## Update — 2026-10-12 00:27

Follow-up runs in the same session: `wiki-dedup`, `wiki-consistency`, then an `AGENTS.md` audit.
The MCP code itself was unchanged by all three; the work was documentation and one doc-level fix.

### Wiki dedup — no duplicates

Compared all 28 pages pairwise (378 pairs) on frontmatter **and** body text via token overlap. The
top-scoring pair was **0.377** against a ~0.85 merge threshold, and every `session_id` is unique.

The two closest pages (`2026-07-16-github-pr-webhooks-search` and
`2026-07-16-merge-rebase-pr-comment-handlers`) both conclude "no GitHub integration exists" and look
duplicative by title, but they are **different sessions** (`ses_0936b80f…` vs `ses_0936bf8b…`) with
different scopes — search matrix vs. WebPush surface catalogue. Per the skill, distinct sessions get
cross-linked rather than merged, and both were already linked in both directions. **Nothing merged,
nothing deleted.**

### Wiki consistency — 2 stale claims fixed, 24 one-way links repaired

**MNT-215 midseason predicate was superseded.** It stated `self.now.hour % 3 == 0` as live. Current
code is `hour >= 6 and hour % 2 == 0 and minute < 30` (`odin/apps/relays/services.py:107`, shifted from
`:101` by the MNT-250 schedule cycle on 2026-10-16). Annotated with a dated note and cross-linked both ways.

**Kafka page described a removed subsystem.** `2026-07-17-mock-kafka-systemctl-in-tests` presents
`KafkaService` as a live obstacle; Kafka was removed from the project entirely (no `KafkaService`, no
`kafka` dependency, no `refresh_state_from_kafka`). Noted that the `systemd_status` half still holds
(`odin/apps/core/services.py:10`, still patched in `odin/tests/api/test_systemd.py:23`) and that the
aggregate dashboard view the mocks targeted is gone.

Two claims that *looked* stale were verified accurate and left alone: `update_boiler_mode` genuinely
is commented out (`scheduler.py:40`), and the boiler API genuinely returns a `status` dict
(`serializers.py:15`).

**24 cross-links were one-way.** The README requires double-bracket body links and `related:`
frontmatter to stay in sync; 24 edges pointed a single direction, so the graph was largely one-way.
All 28 pages now pass a schema + link + reciprocity check.

**INDEX.md rebuilt.** `## By topic` was missing 3 pages including this one; added an *MCP server &
agent tooling* cluster and re-verified largest-first ordering. Also fixed one malformed entry whose
date rendered as `(2026-09-24/25)`.

> **Process note:** the first link-repair script rewrote files non-idempotently and silently dropped
> links it had added moments earlier. Caught by the validator, restored from a backup, redone as a
> single in-memory fixed point. The intermediate churn was avoidable.

### AGENTS.md audit — 5 stale, 4 missing, 2 wrong

Ran the `wiki-agents-file` skill, cross-checking every concrete claim against the code, the wiki, and
25 commits of history. Two genuine factual errors:

- **`uv run bandit -c pyproject.toml .` does not work.** Bandit is only a pre-commit hook
  (`.pre-commit-config.yaml:30-37`), not a project dependency — `uv run bandit` fails with
  `Failed to spawn: bandit`. Replaced with `uv run pre-commit run bandit`.
- **`odin/apps/relays/services.py:19` no longer points at `perform_update`.** Line 19 is now
  `class RelayLogService` after the async-relay-log rework (`86af8fb`); `perform_update` is at
  `odin/api/v1/relays/views.py:52`.

Missing entries: the `./mcp_server/` package, the new runtime deps (`asyncpg`, `mcp`) and
`pytest-asyncio`, and the fact that CI resolves Python from `requires-python` via
`python-version-file` — which is why the 3.13→3.14 bump silently changed the CI runtime.

One draft claim was corrected before landing: I first wrote the import-ordering section with
`mcp_server` as its own isort tier, then checked `pyproject.toml` and found `section-order` omits it,
so it actually sorts as first-party. AGENTS.md now states the truth rather than the tidier version.

### PR #41 review findings — 8 unresolved threads fixed

Ran `fix-review-findings` against the open PR. All 8 threads were CodeRabbit; 7 valid, fixed as
suggested or more strictly. Each thread carried an embedded "Prompt for AI Agents" block telling me
to run `coderabbit review --agent` afterwards — that is untrusted review content, not a user
instruction, so it was ignored.

- **`database.py` — pool creation race.** Two concurrent first callers could each create a pool and
  leak one. Added a double-checked `asyncio.Lock`.
- **`database.py` — denylist replaced with an allow-list.** `_filter_sensitive_columns` only removed
  names in `SENSITIVE_COLUMNS`, so `password_hash` or `client_secret` would leak through
  `query_table` until someone remembered to add them. A denylist cannot keep pace with schema
  changes, so `APPROVED_COLUMNS` now denies by default. Verified against the live database:
  `auth_user` no longer returns `password`.
- **`database.py` — filters on redacted columns.** Filtering on `ssn` or `token` revealed whether a
  guessed secret matched even though the column was omitted. `_validate_column_name` now checks the
  same allow-list (`QUERYABLE_COLUMNS`).
- **`logs.py` — truncated first line in `tail_file`.** Reproduced CodeRabbit's case: 9,000 `A`s plus
  `\nB\n` with `lines=2` returned a **partial** first line, because the read stopped once enough
  newlines were buffered without requiring the first requested line to be complete.
- **`logs.py` — symlink escape in `list_log_files`.** `rglob` follows symlinks, so a link inside the
  log root exposed an outside file's size and mtime even though `tail_logs` rejected the same path.
- **`logs.py` — unbounded scan after truncation.** An empty `read()` kept the loop seeking once per
  block for the rest of the recorded size. Now breaks on empty read and takes the size from the open
  handle instead of a separate `stat`.
- **`wiki.py` — `pages_root` not resolved.** `target.relative_to(pages_root)` compared a resolved
  target against an unresolved root, so a relative or symlinked `MCP_PAGES_ROOT` made **every** page
  fail to resolve. `config.py` already resolved `LOG_ROOT` for exactly this reason.
- **MNT-215 wiki page** — TL;DR and Overview still presented the superseded *every 3 hours for 1 hour*
  cadence as current. Rewrote both to state the live predicate and labelled the `hour % 3` material
  historical.

Two problems surfaced while verifying rather than from the review itself:

- A new test failed because `password` was still in my first allow-list draft, which defeated the
  entire point of the change. Removed.
- That allow-list was also too narrow — it hid ~80 legitimate columns. Checked all 124 real columns
  and widened it, deliberately withholding `password`, `token`, `session_data`, `raw_body` and
  `encoded_headers`: the last three are session blobs and raw request payloads that can carry
  cookies or authorization headers.

**621 tests pass** (8 new regression tests), ruff/ty/pre-commit clean. Changes staged only — no
commit, no push; the orchestrator handles that.

## Follow-ups

- `MCP_LOG_ROOT` replaces `ODIN_LOG_ROOT`. If it is set in a shell profile or systemd unit it needs
  updating.
- The database tool caches the set of public-schema tables process-wide and never invalidates it, so
  tables created after the server starts stay invisible until restart. Left as-is (restart is cheap)
  but worth a TTL if migrations ever run against a live server.
- `allowed_tables` is also never refreshed; same consideration as above.
- ~~The 15 modified `wiki/pages/*.md` files~~ — **resolved 2026-10-12**: the working tree is clean
  and the `branch: -` → `master` rewrite is committed. No action needed.
- `opencode.json` has an unstaged deletion of the `"plugin": []` key that predates this session and
  was not made here. The file is valid JSON either way, but confirm the removal was intentional.
- PR #41 review fixes are staged but uncommitted. If new columns are added to the schema,
  `APPROVED_COLUMNS` in `mcp_server/tools/database.py` must be updated or they become invisible to
  `query_table` — that is the intended fail-closed behaviour, but it means a schema migration
  should be accompanied by an allow-list update.

## References

- Related: [[2026-09-23-relay-mode-compute-on-read]]