---
title: Silk profiler unreachable — SPA catch-all shadows /silk/
date: 2026-09-24
type: debug
status: resolved
session_id: ses_f2aeab5d8ffehDscB5kjUAABCV
services: [main]
branch: master
tickets: []
tags: [django, silk, urls, debug, admin, spa]
related: [2026-08-24-react-spa-dev-mode-debug.md]
---

# Silk profiler unreachable — SPA catch-all shadows /silk/

## TL;DR

The local Django dev server on port 8000 was not running at all, so both `/admin/` and `/silk/`
returned connection-refused. After starting it, `/admin/` worked but `/silk/` still served the React
SPA `index.html` (1829 bytes) instead of the profiler: the SPA catch-all `re_path` in `odin/urls.py`
was registered before the silk include and its negative lookahead did not exclude `silk`. Adding
`silk(?:$|/)` to the lookahead fixed it; `/silk/` now renders `Silky - Summary` (20682 bytes).

---

## Symptom

Reported as "can't open admin page and silk" on a locally run Django backend on port 8000.

```
$ lsof -nP -iTCP:8000 -sTCP:LISTEN
(nothing)
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/admin/
000
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/silk/
000
```

`000` means the connection itself failed — no listener on the port, independent of any routing.

## Step 1 — Server was not running (explains admin)

Nothing was listening on 8000. The `silk` wiring already existed in the working tree (uncommitted):

**File:** `odin/settings/dev.py`

```
INSTALLED_APPS.insert(0, "silk")
MIDDLEWARE.insert(0, "silk.middleware.SilkyMiddleware")
```

**File:** `odin/urls.py` (before fix) — inside `if settings.DEBUG:`

```
urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
```

`silk` was installed (`import silk` OK), `manage.py check` reported no issues, and all nine silk
migrations were applied. So the only reason both pages were unreachable was that `runserver` was not
up. Starting it brought `/admin/` back:

```
$ DJANGO_SETTINGS_MODULE=odin.settings.dev uv run manage.py runserver 8000
/admin/         302   (-> /admin/login/ 200)
/admin/login/   200
```

The `302` is normal: an unauthenticated `/admin/` redirects to the login form.

## Step 2 — SPA catch-all shadowed /silk/ (the real routing bug)

With the server up, `/silk/` returned `200` but with the wrong body. It was byte-identical to any
unmatched SPA path:

```
$ curl -s -o /dev/null -w "silk:   %{size_download}\n" http://127.0.0.1:8000/silk/
silk:   1829
$ curl -s -o /dev/null -w "health: %{size_download}\n" http://127.0.0.1:8000/health
health: 1829
```

Both 1829 bytes = `frontend/dist/index.html`. **File:** `odin/apps/core/views.py:23`

```
def index_view(request: HttpRequest) -> HttpResponse:
    return _read_dist_file("index.html", "text/html")
```

`odin/urls.py` registers the SPA catch-all `re_path` **before** the silk include, and the pattern's
negative lookahead omitted `silk`:

```
re_path(
    r"^(?!api(?:$|/)|admin(?:$|/)|static(?:$|/)|media(?:$|/)|sw\.js$|manifest\.webmanifest$).*$",
    index_view,
    name="index",
),
```

Django matches in order, so `/silk/`, `/silk/requests/`, etc. hit the catch-all and never reached
`include("silk.urls")`. `/admin/` was unaffected because `admin(?:$|/)` **was** in the lookahead and
the admin pattern sits above the catch-all.

## Root cause

The SPA fallback route greedily captures every path that is not explicitly excluded. `silk` was
added as a new app but its prefix was never added to the catch-all's exclusion list, so the
profiler's URLs were swallowed by `index_view`.

## Resolution / Fix

Added `silk(?:$|/)` to the negative lookahead in the catch-all pattern.

**File:** `odin/urls.py` (one line)

```
r"^(?!api(?:$|/)|admin(?:$|/)|silk(?:$|/)|static(?:$|/)|media(?:$|/)|sw\.js$|manifest\.webmanifest$).*$",
```

Verified after restarting `runserver`:

```
/admin/          302
/admin/login/    200
/silk/           200   size=20682   <title>Silky - Summary</title>
/silk/requests/  200   size=37689
```

## Known follow-up (not fixed this session)

- `silk` is registered only under `if settings.DEBUG:`, so `/silk/` 404s with prod/test settings — expected.
- `runserver` binds `127.0.0.1` only. `http://localhost:8000` works, but `http://[::1]:8000` and
  `http://<hostname>:8000` are refused. Use `runserver 0.0.0.0:8000` for LAN/hostname access.
- The `silk` app/middleware/url wiring is uncommitted working-tree change; commit alongside the fix.

---

## Follow-ups

- Commit the `odin/urls.py` exclusion fix together with the `dev.py` silk wiring.

## References

- Related: [[2026-08-24-react-spa-dev-mode-debug]]
- Files: `odin/urls.py`, `odin/settings/dev.py`, `odin/apps/core/views.py`
