---
title: 'MNT-275: Video library backend in odin'
date: '2026-10-31'
type: implementation
status: resolved
session_id: -
services: [video, video-scan, omdb, trailers, nginx, scheduler, api]
branch: opencode/feature/mnt-275-home-cinema-backend
tickets: [MNT-275, MNT-271]
tags: [video, django, api, x-accel-redirect, omdb, yt-dlp, scanner, nginx, feature]
related: [2026-09-23-mnt-218-split-dashboard-api.md, 2026-09-11-ebusd-config-load-boiler-refresh.md]
---

# MNT-275: Video library backend in odin

## TL;DR

The video library backend landed as a new Django app (`odin/apps/video/`) plus a read API
(`odin/api/v1/video/`) inside odin — no FastAPI, no Docker, no new repo. A scheduler-driven
`video_scan` command reconciles the `Video` table with the configured media dirs (incremental by
path + mtime), caches OMDb metadata, and downloads one Russian trailer MP4 per title with yt-dlp.
`stream/` and `trailer/` endpoints answer with `X-Accel-Redirect` so nginx streams the bytes with
native HTTP Range support for Media3 on the Google TV app.

## Overview

The scope absorbed MNT-274 (scanner + OMDb + trailer fetcher). Every piece reuses existing odin
conventions: a TextChoices status enum, `services/` package, `LoggedCommand`, an APScheduler job in
`odin/apps/core/scheduler.py`, DRF `GenericViewSet`/`APIView`, pytest + Factory Boy.

**Files:** `odin/apps/video/{models,admin,apps}.py`, `odin/apps/video/services/`,
`odin/apps/video/management/commands/video_scan.py`, `odin/api/v1/video/`,
`odin/settings/base.py`, `odin/apps/core/scheduler.py`, `configs/nginx.conf`

## Step 1 — The `Video` model

One row per file on the media share, keyed by the unique absolute `path`. The row caches what the
TV app needs (`title`, `year`, `imdb_rating`, `description`, `genres`) plus two independent fetch
state machines (`metadata_status`, `trailer_status` ∈ `PENDING | FETCHED | NOT_FOUND | ERROR`) with
attempt counters. `mtime` is the incremental cache: an unchanged, available row is never rewritten.
Removed files are flagged `is_available=False` instead of deleted, so a returning file keeps its
metadata and a missing mount never wipes the library.

**File:** `odin/apps/video/models.py:40`

## Step 2 — Scanner (`video_scan` + scheduler job)

`scan_library()` walks every `VIDEO_MEDIA_DIRS` root, matches video extensions, skips dot-files, and
parses `Movie Name (Year)` into `(title, year)`. Names without a year keep the whole stem and log a
warning — the scan never drops a file. Each root and each file is isolated: an unreadable dir logs
and is skipped, and rows are only marked missing for roots that were actually readable. The same
command then runs one bounded batch of metadata and trailer work
(`VIDEO_SCAN_BATCH_SIZE`, `--limit`, `--no-metadata`, `--no-trailers`).

**File:** `odin/apps/video/services/scanner.py:82`
**File:** `odin/apps/video/management/commands/video_scan.py:14`

The scheduler job defaults to a 1-minute interval with `max_instances=1`, so a slow trailer download
does not stack ticks.

**File:** `odin/apps/core/scheduler.py:41`

## Step 3 — OMDb metadata

`fetch_metadata()` searches `?t=<title>&y=<year>&type=movie`, then persists title/year/rating/plot/
genres and flips `metadata_status` to `FETCHED`. `Response: False` is final (`NOT_FOUND`); transient
errors stay retryable (`ERROR`) until `VIDEO_FETCH_MAX_ATTEMPTS`. The free tier cap is enforced
through the Django cache with a per-day counter (`VIDEO_OMDB_DAILY_LIMIT`, default 900 < 1,000).
Rows are only ever fetched once — `pending_metadata()` excludes `FETCHED`.

**File:** `odin/apps/video/services/metadata.py:99`

## Step 4 — Russian trailers

`download_trailer()` builds `<title> <year> трейлер`, runs yt-dlp with
`best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]` (plus `--ignore-config` and
`--merge-output-format mp4`) into a scratch dir next to the target, and moves the single `.mp4`
result into `VIDEO_TRAILERS_DIR` only after a clean exit — a killed download never leaves a
half-written MP4, and a non-MP4 or sidecar-only result fails the attempt. An existing non-empty file
is reused instead of re-downloading. Optional `YOUTUBE_PROXY` is passed as `--proxy`. A missing
yt-dlp binary logs an error and does not burn an attempt.

**File:** `odin/apps/video/services/trailers.py:96`

## Step 5 — Read API and nginx streaming

`GET /api/v1/video/videos/` (paginated, available only) and `GET /api/v1/video/videos/<id>/`
return the metadata; `.../stream/` and `.../trailer/` return a `200` whose `X-Accel-Redirect`
points at an internal nginx location. Django checks the row and the file, then hands off.

**File:** `odin/api/v1/video/views.py:31`
**File:** `odin/apps/video/services/streaming.py:41`

Two internal nginx locations were added to both the HTTP and HTTPS server blocks:

```nginx
location /video-media/ {
    internal;
    alias /;
}

location /video-trailers/ {
    internal;
    alias /var/lib/odin/trailers/;
}
```

`/video-media/` maps the internal URI 1:1 onto the absolute path Django puts in `X-Accel-Redirect`,
so any `VIDEO_MEDIA_DIRS` entry works without its own location block. `/video-trailers/` aliases the
single known trailer directory (`VIDEO_TRAILERS_DIR`, default `/var/lib/odin/trailers`), so the URI
carries only the file name. Django re-checks that the resolved video path stays under
`VIDEO_MEDIA_DIRS` and the trailer under `VIDEO_TRAILERS_DIR`, so a symlink swapped into the share
cannot expose a file outside the library. nginx serves both with Range support, which is what Media3
needs to seek on the TV.

## Configuration

- `VIDEO_MEDIA_DIRS` — comma-separated absolute media roots on the odin host.
- `VIDEO_TRAILERS_DIR` — writable trailer dir, default `/var/lib/odin/trailers` (must match the
  nginx alias).
- `OMDB_API_KEY`, `OMDB_API_URL`, `OMDB_TIMEOUT`, `VIDEO_OMDB_DAILY_LIMIT`.
- `YOUTUBE_PROXY`, `VIDEO_YTDLP_BIN`, `VIDEO_TRAILER_TIMEOUT`, `VIDEO_TRAILER_MAX_FILESIZE`.
- `VIDEO_SCAN_INTERVAL`, `VIDEO_SCAN_BATCH_SIZE`, `VIDEO_FETCH_MAX_ATTEMPTS`.

## Test Results

`636 passed` (`uv run pytest ... odin/` on PostgreSQL), `make django-checks` clean (no pending
migrations for `video`), `uv run ty check` clean, pre-commit hooks pass (bandit needs the same
`# nosec` annotations as the existing subprocess call sites).

New tests: `odin/tests/api/test_video.py`, `odin/tests/services/test_video_{scanner,metadata,trailers}.py`,
`odin/tests/commands/test_video_scan.py`, plus `VideoFactory`.

## Follow-ups

- No frontend tile for video yet; the Google TV app (MNT-273) is the only consumer.
- `X-Accel-Redirect` only works behind nginx; `runserver` returns an empty 200 locally.
- Trailer language is a query heuristic (`трейлер`) and only MP4 results are accepted; a Russian
  audio track is not verified.
- An empty media root is treated as an unmounted share: missing-file reconciliation is skipped, so
  a library whose last file was deleted keeps its rows until a file reappears.

## References

- External: https://linear.app/mnt/issue/MNT-275/home-cinema-server-backend-in-odin-django-app-api-scanner
- Related: [[2026-09-23-mnt-218-split-dashboard-api]]
- Related: [[2026-09-11-ebusd-config-load-boiler-refresh]]
