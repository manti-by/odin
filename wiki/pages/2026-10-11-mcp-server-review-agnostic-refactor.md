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
related: []
---

# MCP server review and project-agnostic refactor

## TL;DR

Reviewed an MCP server copied from another project, found **two silent data-corruption bugs** that
returned confidently wrong answers rather than errors, fixed them, then made the server project
agnostic. The worst bug: the wiki tools were reading a *different repository's* wiki because
`Path(__file__).resolve().parents[3]` was off by one after the package moved — every wiki query
answered from the umbrella repo's 2 pages instead of odin's 27, with no error. Added 208 tests and
replaced 10 loose module-global cache variables with one frozen `Corpus` snapshot. 603 tests pass.

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

## Follow-ups

- `MCP_LOG_ROOT` replaces `ODIN_LOG_ROOT`. If it is set in a shell profile or systemd unit it needs
  updating.
- The database tool caches the set of public-schema tables process-wide and never invalidates it, so
  tables created after the server starts stay invisible until restart. Left as-is (restart is cheap)
  but worth a TTL if migrations ever run against a live server.
- `allowed_tables` is also never refreshed; same consideration as above.
- The 15 modified `wiki/pages/*.md` files in the working tree look like output of the wiki-sync
  skill (frontmatter quote normalization, `branch: -` → `master`), unrelated to this work. The
  `branch: -` → `master` rewrite is a semantic change worth a look.

## References

- Related: [[2026-09-23-relay-mode-compute-on-read]]