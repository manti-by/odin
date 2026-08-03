# Odin Frontend

React + TypeScript SPA that replaces the Django-rendered dashboard
(`index.html`, `chart.html`, `header.html`, `modal.html`). Django admin is
unaffected. Built with [Vite](https://vitejs.dev/), bundled by
[Bun](https://bun.sh/), and linted/formatted with [Biome](https://biomejs.dev/).

## Requirements

- [Bun](https://bun.sh/) >= 1.3

## Getting started

```bash
cd frontend
cp .env.example .env     # optional: override VITE_API_BASE_URL
bun install
bun run dev              # dev server on http://localhost:5173
```

The dev server proxies `/api`, `/admin`, and `/static` to the Django dev
server at `http://127.0.0.1:8000`, so start Django in another terminal:

```bash
uv run manage.py runserver
```

## Environment

| Variable              | Default     | Description                                         |
| --------------------- | ----------- | --------------------------------------------------- |
| `VITE_API_BASE_URL`   | `/api/v1/`  | Base URL for the OdIN REST API used by the client.  |

These variables are read by Vite at build time and exposed to the client via
`import.meta.env`. Never put secrets in `.env` files — they are bundled into the
client.

## Scripts

```bash
bun run dev         # start the Vite dev server
bun run build       # type-check and build production assets to dist/
bun run preview     # preview the production build locally
bun run typecheck   # type-check only (no emit)
bun run lint        # run Biome check
bun run format      # format the codebase with Biome
```

## Project layout

```text
frontend/
├── index.html              # Vite HTML entrypoint
├── src/
│   ├── main.tsx            # app entry + router
│   ├── App.tsx             # root layout (uses Layout component)
│   ├── components/
│   │   ├── Header.tsx      # site header with nav
│   │   ├── icons/
│   │   │   └── Icon.tsx    # icon component (graph, settings, cooling, heating)
│   │   ├── layout/
│   │   │   ├── Container.tsx  # wrapper with .container class, fluid/breakpoint support
│   │   │   └── Layout.tsx     # header + main container layout
│   │   ├── tile/
│   │   │   ├── AliveIndicator.tsx  # colored status dot (alive/dead/heating/cooling)
│   │   │   └── Tile.tsx            # dashboard card shell (title, status, icon link, body)
│   │   ├── grid/
│   │   │   └── ResponsiveGrid.tsx  # responsive column grid
│   │   ├── modal/
│   │   │   └── Modal.tsx           # modal overlay with Escape/backdrop close
│   │   └── form/
│   │       ├── Form.tsx             # form wrapper
│   │       ├── TextField.tsx        # text/number input with label
│   │       ├── SubmitButton.tsx     # submit button (primary/secondary/outline)
│   │       └── FieldStatus.tsx      # inline validation message (error/info/success)
│   ├── pages/              # route components (lazy-loaded)
│   │   ├── DashboardPage.tsx
│   │   ├── SensorChartPage.tsx
│   │   ├── StyleguidePage.tsx  # component styleguide
│   │   └── NotFoundPage.tsx
│   ├── lib/
│   │   ├── config.ts       # env-based config (API base URL, admin URL)
│   │   └── api/            # fetch-based API client with CSRF handling
│   │       ├── client.ts
│   │       └── sensors.ts
│   └── styles/
│       ├── app.css         # global resets / base theme
│       ├── components.css  # tile, modal, alive-indicator, form primitives
│       └── responsive.css  # mobile/tablet/large-tablet breakpoints
├── biome.json
├── tsconfig.json
└── vite.config.ts
```

## Routing

Routes mirror the existing Django pages:

- `/` — dashboard (replaces `index.html`)
- `/sensors/home` — home temperature chart (replaces `sensors_home`)
- `/sensors/boiler` — boiler temperature chart (replaces `sensors_boiler`)
- `/styleguide` — component styleguide with every state visible
- `*` — 404 placeholder

## Shared components

All presentational, no dashboard-specific business logic. Parameterized via props.

| Component | File | Description |
|-----------|------|-------------|
| `Container` | `src/components/layout/Container.tsx` | Wraps children in `.container` class; accepts `as` (element type) and `fluid` (no max-width). |
| `Layout` | `src/components/layout/Layout.tsx` | Composes `<Header />` + `<main className="container">`. Used by `App.tsx`. |
| `ResponsiveGrid` | `src/components/grid/ResponsiveGrid.tsx` | CSS grid container; 3 columns (>1400px) → 2 columns (769-1400px) → 1 column (≤768px). |
| `Tile` | `src/components/tile/Tile.tsx` | Dashboard card shell — `title`, optional `status` (AliveState), optional `iconLink` (ReactNode), and `children` body slot. |
| `AliveIndicator` | `src/components/tile/AliveIndicator.tsx` | 8px colored dot; states: `alive` (#4caf50), `dead` (#f44336), `heating` (#f44336), `cooling` (#007190). |
| `Modal` | `src/components/modal/Modal.tsx` | Fixed overlay with `open`/`onClose` control; Escape key and backdrop-click dismiss; `title`, `children` (body slot), optional `message`. |
| `Icon` | `src/components/icons/Icon.tsx` | Renders `<img>` referencing `/static/img/{name}.svg` via the Vite proxy. Names: `graph`, `settings`, `cooling`, `heating`. |
| `Form` | `src/components/form/Form.tsx` | `<form>` wrapper with `onSubmit`. |
| `TextField` | `src/components/form/TextField.tsx` | Text/number input with `<label>`. Props: `id`, `label`, `value`, `onChange`, `type`, `name`, `step`, `required`, `autoComplete`. |
| `SubmitButton` | `src/components/form/SubmitButton.tsx` | Styled button; `label`, `variant` (primary/secondary/outline), `disabled`, plus any `<button>` attributes. |
| `FieldStatus` | `src/components/form/FieldStatus.tsx` | Inline validation message; `tone` (error/info/success), `children`. |

### CSS

- `src/styles/components.css` — tile, grid, modal, alive-indicator, form styles (ported from `odin/static/css/index/base.css`, `index/sensors.css`, `modal.css`, and `base.css`).
- `src/styles/responsive.css` — breakpoint overrides matching the four existing breakpoints (≤480, 481-768, 769-1024, 1025-1400).

Icons are served by Django's static file server via the Vite dev proxy (`/static/img/*`), consistent with `Header.tsx`'s logo reference.

## API client

`src/lib/api/client.ts` wraps `fetch` and:

- Prepends `config.apiBaseUrl` (`/api/v1/` by default).
- Reads the `csrftoken` cookie and sends it as `X-CSRFToken` for unsafe
  requests (mirrors `odin/static/js/index.js`).
- Sends `credentials: "same-origin"` so session auth works.
- JSON-encodes request bodies and decodes JSON responses.
- Throws `ApiError` (with `status` + `body`) on non-2xx responses.

### Smoke test

`DashboardPage` calls `GET /api/v1/sensors/` via `sensorsApi.list()` on mount
and renders the count, verifying the API client end-to-end against the running
Django backend.

## PWA (Progressive Web App)

The frontend is a PWA: installable via `Add to Home Screen` and capable of
offline SPA shell loading once the service worker has been installed by a prior
visit.

- **Manifest**: generated by `vite-plugin-pwa` from the configuration in
  `vite.config.ts` and served by Django at `/manifest.webmanifest`.
- **Service worker** (`src/sw.ts`): built with Workbox via `vite-plugin-pwa`'s
  `injectManifest` strategy. It precaches all hashed bundle assets + the HTML
  shell (automatically injected via `self.__WB_MANIFEST`). The existing push
  notification handlers (`push`, `notificationclick`, `notificationclose`) from
  the Django-era `sw.js` are ported directly.
- **Registration** (`src/pwa.ts`): run from `src/main.tsx`. Fetches the FCM
  application server key from `/api/v1/core/app-server-key/`, registers the SW
  at `/sw.js` with `{scope: "/"}`, then subscribes for push notifications and
  POSTs the subscription to `/api/v1/core/devices/`.
- **Django routes**: `/sw.js` is served by a dedicated view with
  `Service-Worker-Allowed: /` so the SW can control the entire site.
  `/manifest.webmanifest` is served as `application/manifest+json`.
- **Icons**: favicon PNGs live in `frontend/public/favicon/` and are copied
  verbatim by Vite to `dist/favicon/`, then served at `/static/favicon/*`.
  The maskable `favicon/180.png` is used as the Apple touch icon.

## Authentication & CSRF

### Session-based authentication

The SPA is served same-origin and relies on Django's session cookies
(`sessionid`). No auth tokens are stored in the client. Sessions are
established via the Django admin login (`/admin/`).

- All API requests are sent with `credentials: "same-origin"` (set in
  `client.ts`), which ensures the session cookie is included.
- Read endpoints (`/sensors/`, `/dashboard/`, `/relays/`, `/ds18b20/`,
  `/esp8266/`, `/chart-options/`, `/weather-chart/`, `/healthcheck/`) are
  public (`AllowAny`).
- Write endpoints (`PATCH /sensors/<id>/`, `PATCH /relays/<id>/`) require
  `IsAuthenticated`. The SPA user must have an active Django session.

### CSRF protection

The Django `CsrfViewMiddleware` sets the `csrftoken` cookie on every response
that uses `get_token`. The SPA's API client reads this cookie and sends its
value as the `X-CSRFToken` header on all unsafe (POST/PUT/PATCH/DELETE)
requests.

- `csrf` cookie name: `csrftoken` (Django default), HTTPOnly `false` (so
  `document.cookie` is readable by the client).
- SameSite policy: `Lax` (safe for same-origin navigation and subresource
  requests).
- **Cookie bootstrap**: On app boot the client should `GET /api/v1/core/csrf/`
  to ensure the `csrftoken` cookie is present. This endpoint calls
  `django.middleware.csrf.get_token()` which triggers the middleware to set the
  cookie in the response. The existing `client.ts` reads the cookie from
  `document.cookie`, so no explicit client change is needed — just make sure
  the boot sequence includes a call to this endpoint before the first unsafe
  request.
- Token-authenticated requests (used by satellite devices, not the SPA) are
  CSRF-exempt by DRF design — they bypass the cookie check entirely.

### Rate limiting (throttling)

Write endpoints have DRF `ScopedRateThrottle` rates configured in
`odin/settings/base.py`:

| Scope             | Rate   | Endpoint(s)                        |
|-------------------|--------|-------------------------------------|
| `sensors_update`  | 30/min | `PATCH /api/v1/sensors/<id>/`      |
| `relays_update`   | 30/min | `PATCH /api/v1/relays/<id>/`       |

Exceeding the rate returns `429 Too Many Requests`.