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

```
frontend/
├── index.html              # Vite HTML entrypoint
├── src/
│   ├── main.tsx            # app entry + router
│   ├── App.tsx             # root layout
│   ├── components/         # shared UI components
│   │   └── Header.tsx
│   ├── pages/              # route components (lazy-loaded)
│   │   ├── DashboardPage.tsx
│   │   ├── SensorChartPage.tsx
│   │   └── NotFoundPage.tsx
│   ├── lib/
│   │   ├── config.ts       # env-based config (API base URL, admin URL)
│   │   └── api/            # fetch-based API client with CSRF handling
│   │       ├── client.ts
│   │       └── sensors.ts
│   └── styles/
│       └── app.css
├── biome.json
├── tsconfig.json
└── vite.config.ts
```

## Routing

Routes mirror the existing Django pages:

- `/` — dashboard (replaces `index.html`)
- `/sensors/home` — home temperature chart (replaces `sensors_home`)
- `/sensors/boiler` — boiler temperature chart (replaces `sensors_boiler`)
- `*` — 404 placeholder

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