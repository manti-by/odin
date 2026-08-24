---
title: "Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug"
date: 2026-08-24
type: debug
status: resolved
session_id: ses_opencode_2026-08-24-react-spa-dev
services: [frontend, core]
branch: -
tickets: []
tags: [react, vite, strictmode, dev-server, dashboard, typescript]
related:
  - 2026-07-21-react-frontend-pr-review-fixes.md
---

# Fix React SPA dev-mode issues: docs, proxy, base path, StrictMode Loading bug

## TL;DR

Synced `AGENTS.md` and `README.md` with the React SPA migration. While running the
Vite dev server locally, fixed two distinct dev-only bugs: (1) `base: "/static/"`
redirected `/` → `/static/` → 404, so `base` is now scoped to production only;
(2) all five dashboard tiles were stuck on "Loading…" because
`useDashboardData` used the `isMountedRef` pattern, which React 18 `<StrictMode>`
breaks in dev by leaving the ref at `false` after the simulated unmount — the
`fetchIdRef` staleness check alone is enough. Prod was never affected because
the bug only fires under StrictMode's double-invocation, which is dev-only.

---

## Symptom

After the React SPA migration, with `bun run dev` against a local Django:

- http://localhost:5173/ rendered the SPA shell but every dashboard tile stayed
  on `Loading…`. The API call returned 200 with a valid JSON payload from both
  Django's logs and a manual `fetch()` in the browser console.
- Earlier in the session: visiting `/` 302'd to `/static/` which returned 404.

The bug was **only local**: the production dashboard at `https://odin.manti.by`
rendered data correctly.

## Step 1 — Verify the request reaches Django

- `curl http://127.0.0.1:8000/api/v1/core/dashboard/` returned 200 with ~4.4 KB
  of JSON. Django's runserver log confirmed `GET /api/v1/core/dashboard/ HTTP/1.1 200 4457`.
- `curl http://localhost:5173/api/v1/core/dashboard/` (through the Vite proxy)
  also returned 200 with the same payload.
- Browser-side `fetch('/api/v1/core/dashboard/')` from the dev page returned 200
  with `application/json`. A manual `JSON.parse` succeeded; `Object.keys()`
  listed all 10 expected top-level fields.
- Ruled out: proxy config (the `changeOrigin` rewrite was fine), CSRF (read
  endpoints are `AllowAny`), and JSON parsing.
- **Conclusion:** the data was reaching the browser; the React state just
  wasn't updating.

## Step 2 — Locate the "Loading…" guard

- All five tiles render `<p className="tile__loading">Loading...</p>` while
  `loading === true` — confirmed in
  `frontend/src/components/tile/WeatherTile.tsx:21` and
  `frontend/src/components/tile/Esp8266SensorsTile.tsx:40` (and the three
  other tiles).
- `loading` lives in `frontend/src/hooks/useDashboardData.ts:8`. The hook
  sets it to `false` in `fetchData`'s `finally`, **guarded by**
  `id === fetchIdRef.current && isMountedRef.current` (line 28).

## Step 3 — Reproduce the StrictMode double-effect locally

- `frontend/src/main.tsx:36` wraps the tree in `<StrictMode>`. In React 18 dev
  StrictMode runs every effect as `setup → cleanup → setup` **on the same ref
  instance** — refs are preserved across the simulated unmount/remount (the
  React team has confirmed this in [facebook/react#26315](https://github.com/facebook/react/issues/26315)).
- Traced the exact sequence for `useDashboardData`:
  1. Effect #1 runs: `fetchIdRef.current = 1`, fetch starts (`await dashboardApi.get()`).
  2. Cleanup runs: `isMountedRef.current = false` (line 45).
  3. Effect #2 runs: `fetchIdRef.current = 2`, second fetch starts.
  4. Fetch #1 resolves: `id=1` vs `current=2` → stale, skipped.
  5. Fetch #2 resolves: `id=2` vs `current=2` → match, **but
     `isMountedRef.current` is still `false`** — the cleanup ran on the same
     ref and was never reset, so the `&&` short-circuits and `setData` plus
     `setLoading(false)` are silently skipped.
- Net: tiles stay on "Loading…" forever. Prod never reproduces this because
  the `setup → cleanup → setup` cycle is dev-only and the production bundle
  isn't served via Vite.

## Step 4 — Separate the `base: "/static/"` redirect

While debugging the Loading… issue, an earlier symptom also surfaced: opening
`http://localhost:5173/` 302'd to `http://localhost:5173/static/` which then
404'd. Vite's own startup log made the cause explicit:

```text
➜  Local:   http://localhost:5173/static/
```

The `base: "/static/"` setting (intended for production, where the SPA is
served under `/static/` after `collectstatic`) makes Vite treat `/static/` as
the app's root in dev too, redirecting the bare origin to that sub-path.

## Root cause

Two independent dev-only bugs:

- **Loading… forever:** the `isMountedRef = useRef(true)` + `cleanup → false`
  pattern is broken under React 18 `<StrictMode>` because the simulated
  unmount/remount preserves refs. React 18 already no-ops `setState` on
  unmounted components, so the extra guard is redundant and actively harmful.
  The `fetchIdRef` staleness check alone is sufficient.

- **`/` → `/static/` redirect:** `base: "/static/"` is a production concern;
  the dev server should serve the SPA from `/`. The same config can't serve
  both roles.

## Resolution / Fix

**File:** `frontend/src/hooks/useDashboardData.ts`

- Removed `isMountedRef` and its `current = false` in the cleanup. Kept only
  `fetchIdRef` for staleness — all three `if (id === fetchIdRef.current)`
  guards now drive `setData`, `setError`, and `setLoading(false)`.

```ts
// before
if (id === fetchIdRef.current && isMountedRef.current) {
  setData(result);
}
// ...
return () => {
  isMountedRef.current = false;
  if (intervalRef.current !== null) {
    clearInterval(intervalRef.current);
  }
};

// after
if (id === fetchIdRef.current) {
  setData(result);
}
// ...
return () => {
  if (intervalRef.current !== null) {
    clearInterval(intervalRef.current);
  }
};
```

**File:** `frontend/vite.config.ts`

- Scoped `base` to production only:

```ts
// before
export default defineConfig({
  base: "/static/",
  // ...

// after
export default defineConfig(({ mode }) => ({
  base: mode === "production" ? "/static/" : "/",
  // ...
}));
```

- Also reverted the brief experiment that pointed the dev proxy at
  `https://odin.manti.by` for `/api`, `/admin`, `/static`. The proxy now
  points at `http://127.0.0.1:8000` again, which is the supported flow.

**Files:** `AGENTS.md`, `README.md`

- `AGENTS.md`: added the `### Frontend (React SPA)` section with the `bun`
  scripts and Makefile shortcuts (`frontend-install`, `frontend`,
  `frontend-lint`, `frontend-typecheck`, `frontend-check`); updated
  `Project Structure` to call out that public templates/static JS/CSS were
  retired (admin assets only remain); expanded `Dependency Management` with
  Bun; clarified `Pre-commit Hooks` is Python-only and frontend checks run via
  `make frontend-check`; noted `make deploy` builds the SPA before
  `collectstatic`.
- `README.md`: Quick Start now lists Bun as a prerequisite and adds a
  `make frontend-install && make frontend` step before `collectstatic`; the
  Makefile table gained the five frontend targets; the
  `## Frontend (React SPA)` section now documents the prod-built artifact
  flow, session/CSRF cookie model, and the root-level Makefile shortcuts.

## Verification

- After HMR reload, the dev page renders real data:
  - Sensors tile shows the six ESP8266 sensors with temperatures and humidity.
  - Boiler Room tile shows the three DS18B20 sensors.
  - Weather tile shows `+13.4°C`, max/min, humidity, pressure, wind.
  - Currency tile shows USD/EUR/RUB rates with trends.
  - Other tile shows voltage (`223 V`), systemd status, and the empty error
    log.
- `make frontend-typecheck` surfaced one pre-existing TS6133 in
  `frontend/src/components/tile/SystemErrorsTile.tsx:32` (`formatTrafficValue`
  declared but never read) — unrelated to this change, flagged as a follow-up.

## Known follow-up (not fixed this session)

- `frontend/src/components/tile/SystemErrorsTile.tsx:32` — `formatTrafficValue`
  declared but never read (TS6133).
- Orphan assets from the retired Django-rendered dashboard still live in the
  repo and are unreferenced by any Python view:
  `odin/static/js/{index,chart,pwa,sw}.js`,
  `odin/static/css/{base,chart,header,index,modal,responsive}/`,
  `odin/static/manifest.json`, and
  `odin/templates/{base,chart,header,modal,chart.svg}`. Safe to delete.
- The dev proxy still assumes Django is running on `127.0.0.1:8000`. If a
  contributor forgets to start it, every `/api/*` request silently fails —
  consider adding a startup banner check or a Makefile target that starts
  both processes together.

---

## Follow-ups

- Remove the orphan Django-era assets listed above in a dedicated cleanup PR.
- Fix the `formatTrafficValue` TS6133 (either use it or drop it).
- Replace the 5-minute `setInterval` polling in `useDashboardData` with SSE /
  Django Channels once data volume justifies the change.

## References

- Related: [[2026-07-21-react-frontend-pr-review-fixes]]
- External: [facebook/react#26315 — `useRef` cleanup in StrictMode refers to second ref twice](https://github.com/facebook/react/issues/26315)
- External: [React docs — `<StrictMode>` / Fixing bugs found by re-running Effects in development](https://react.dev/reference/react/StrictMode)