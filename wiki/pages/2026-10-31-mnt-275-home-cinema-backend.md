---
title: 'MNT-275: Home cinema backend in odin'
date: '2026-10-31'
type: implementation
status: resolved
session_id: -
services: [cinema, cinema-scan, omdb, trailers, nginx, scheduler, api]
branch: mnt-275-video-library
tickets: [MNT-275, MNT-271]
tags: [cinema, video, django, api, x-accel-redirect, omdb, yt-dlp, scanner, nginx, feature]
related: [2026-09-23-mnt-218-split-dashboard-api.md, 2026-09-11-ebusd-config-load-boiler-refresh.md]
---

# MNT-275: Home cinema backend in odin

## TL;DR

The Home Cinema backend landed as a new Django app (`odin/apps/cinema/`) plus a read API
(`odin/api/v1/cinema/`) inside odin — no FastAPI, no Docker, no new repo. A scheduler-driven
`cinema_scan` command reconciles the `Video` table with the configured media dirs (incremental by
path + mtime), caches OMDb metadata, and downloads one Russian trailer MP4 per title with yt-dlp.
`stream/` and `trailer/` endpoints answer with `X-Accel-Redirect` so nginx streams the bytes with
native HTTP Range support for Media3 on the Google TV app.

## Overview

The scope absorbed MNT-274 (scanner + OMDb + trailer fetcher). Every piece reuses existing odin
conventions: a TextChoices status enum, `services/` package, `LoggedCommand`, an APScheduler job in
`odin/apps/core/scheduler.py`, DRF `GenericViewSet`/`APIView`, pytest + Factory Boy.

**Files:** `odin/apps/cinema/{models,admin,apps}.py`, `odin/apps/cinema/services/`,
`odin/apps/cinema/management/commands/cinema_scan.py`, `odin/api/v1/cinema/`,
`odin/settings/base.py`, `odin/apps/core/scheduler.py`, `configs/nginx.conf`

## Step 1 — The `Video` model

One row per file on the media share, keyed by the unique absolute `path`. The row caches what the
TV app needs (`title`, `year`, `imdb_rating`, `description`, `genres`) plus two independent fetch
state machines (`metadata_status`, `trailer_status` ∈ `PENDING | FETCHED | NOT_FOUND | ERROR`) with
attempt counters. `mtime` is the incremental cache: an unchanged, available row is never rewritten.
Removed files are flagged `is_available=False` instead of deleted, so a returning file keeps its
metadata and a missing mount never wipes the library.

**File:** `odin/apps/cinema/models.py:40`

## Step 2 — Scanner (`cinema_scan` + scheduler job)

`scan_library()` walks every `CINEMA_MEDIA_DIRS` root, matches video extensions, skips dot-files, and
parses `Movie Name (Year)` into `(title, year)`. Names without a year keep the whole stem and log a
warning — the scan never drops a file. Each root and each file is isolated: an unreadable dir logs
and is skipped, and rows are only marked missing for roots that were actually readable. The same
command then runs one bounded batch of metadata and trailer work
(`CINEMA_SCAN_BATCH_SIZE`, `--limit`, `--no-metadata`, `--no-trailers`).

**File:** `odin/apps/cinema/services/scanner.py:82`
**File:** `odin/apps/cinema/management/commands/cinema_scan.py:14`

The scheduler job defaults to a 1-minute interval with `max_instances=1`, so a slow trailer download
does not stack ticks.

**File:** `odin/apps/core/scheduler.py:41`

## Step 3 — OMDb metadata

`fetch_metadata()` searches `?t=<title>&y=<year>&type=movie`, then persists title/year/rating/plot/
genres and flips `metadata_status` to `FETCHED`. `Response: False` is final (`NOT_FOUND`); transient
errors stay retryable (`ERROR`) until `CINEMA_FETCH_MAX_ATTEMPTS`. The free tier cap is enforced
through the Django cache with a per-day counter (`CINEMA_OMDB_DAILY_LIMIT`, default 900 < 1,000).
Rows are only ever fetched once — `pending_metadata()` excludes `FETCHED`.

**File:** `odin/apps/cinema/services/metadata.py:99`

## Step 4 — Russian trailers

`download_trailer()` builds `<title> <year> трейлер`, runs yt-dlp with
`best[ext=mp4]/best` into a scratch dir next to the target, and moves the file into
`CINEMA_TRAILERS_DIR` only after a clean exit — a killed download never leaves a half-written MP4.
An existing non-empty file is reused instead of re-downloading. Optional `YOUTUBE_PROXY` is passed
as `--proxy`. A missing yt-dlp binary logs an error and does not burn an attempt.

**File:** `odin/apps/cinema/services/trailers.py:96`

## Step 5 — Read API and nginx streaming

`GET /api/v1/cinema/videos/` (paginated, available only) and `GET /api/v1/cinema/videos/<id>/`
return the metadata; `.../stream/` and `.../trailer/` return a `200` whose `X-Accel-Redirect`
points at an internal nginx location. Django checks the row and the file, then hands off.

**File:** `odin/api/v1/cinema/views.py:31`
**File:** `odin/apps/cinema/services/streaming.py:41`

Two internal nginx locations were added to both the HTTP and HTTPS server blocks:

```nginx
location /cinema-media/ {
    internal;
    alias /;
}

location /cinema-trailers/ {
    internal;
    alias /;
}
```

Both locations map the internal URI 1:1 onto the absolute path Django puts in `X-Accel-Redirect`,
so any `CINEMA_MEDIA_DIRS` / `CINEMA_TRAILERS_DIR` deployment path works without its own location
block and the nginx config never repeats the settings. Django re-checks that the resolved video
path stays under `CINEMA_MEDIA_DIRS` and the trailer under `CINEMA_TRAILERS_DIR`, so a symlink
swapped into the share cannot expose a file outside the library. nginx serves both with Range
support, which is what Media3 needs to seek on the TV.

## Configuration

- `CINEMA_MEDIA_DIRS` — comma-separated absolute media roots on the odin host.
- `CINEMA_TRAILERS_DIR` — writable trailer dir (default `MEDIA_ROOT/cinema/trailers`).
- `OMDB_API_KEY`, `OMDB_API_URL`, `OMDB_TIMEOUT`, `CINEMA_OMDB_DAILY_LIMIT`.
- `YOUTUBE_PROXY`, `CINEMA_YTDLP_BIN`, `CINEMA_TRAILER_TIMEOUT`, `CINEMA_TRAILER_MAX_FILESIZE`.
- `CINEMA_SCAN_INTERVAL`, `CINEMA_SCAN_BATCH_SIZE`, `CINEMA_FETCH_MAX_ATTEMPTS`.

## Test Results

`622 passed` (`uv run pytest ... odin/` on PostgreSQL), `make django-checks` clean (no pending
migrations for `cinema`), `uv run ty check` clean, pre-commit hooks pass (bandit needs the same
`# nosec` annotations as the existing subprocess call sites).

New tests: `odin/tests/api/test_cinema.py`, `odin/tests/services/test_cinema_{scanner,metadata,trailers}.py`,
`odin/tests/commands/test_cinema_scan.py`, plus `VideoFactory`.

## Follow-ups

- No frontend tile for cinema yet; the Google TV app (MNT-273) is the only consumer.
- `X-Accel-Redirect` only works behind nginx; `runserver` returns an empty 200 locally.
- Trailer language is a query heuristic (`трейлер`) and only MP4 results are accepted; a Russian
  audio track is not verified.
- An empty media root is treated as an unmounted share: missing-file reconciliation is skipped, so
  a library whose last file was deleted keeps its rows until a file reappears.

## References

- External: https://linear.app/mnt/issue/MNT-275/home-cinema-server-backend-in-odin-django-app-api-scanner
- Related: [[2026-09-23-mnt-218-split-dashboard-api]]
- Related: [[2026-09-11-ebusd-config-load-boiler-refresh]]
