# ODIN server core application

[ODIN](https://github.com/manti-by/odin/) is a Django-based backend application delivering comprehensive RESTful APIs
and management interfaces. It powers data ingestion, processing, and visualization for the
[Coruscant](https://github.com/manti-by/coruscant/) Raspberry Pi-based heating control system, exposes endpoints for
[Centax](https://github.com/manti-by/centax/) satellite sensor telemetry (including real-time IoT data streams),
and features an interactive dashboard with customizable graphs and historical analytics.

[![Python 3.13](https://img.shields.io/badge/python-3.13-green.svg)](https://www.python.org/downloads/release/python-3136/)
[![Code style: ruff](https://img.shields.io/badge/ruff-enabled-informational?logo=ruff)](https://astral.sh/ruff)
[![License](https://img.shields.io/badge/license-BSD-blue.svg)](https://raw.githubusercontent.com/manti-by/pdw/master/LICENSE)

Author: Alexander Chaika <manti.by@gmail.com>

Source link: [https://github.com/manti-by/odin/](https://github.com/manti-by/odin/)

Requirements: Python 3.13, PostgreSQL 18, Redis 7, UV.

Version: v1.6.0


## Quick Start

1. Install [Python 3.13](https://www.python.org/downloads/release/python-3136/),
   [UV tool](https://docs.astral.sh/uv/getting-started/installation/) and
   [Bun](https://bun.sh/) (the version pinned in `frontend/package.json`).

2. Clone sources, switch to working directory and setup environment:

```shell
git clone https://github.com/manti-by/odin.git
cd odin/
uv sync --all-extras
```

3. Install frontend dependencies and build the SPA:

```shell
make frontend-install
make frontend
```

4. Collect static, run migrations and create superuser:

```shell
uv run python manage.py collectstatic --no-input
uv run python manage.py createsuperuser
uv run python manage.py migrate
```

5. Run development server:

```shell
uv run python manage.py runserver
```


## Makefile Commands

| Command       | Description                                |
|---------------|--------------------------------------------|
| `make run`    | Start development server                   |
| `make migrate`| Run database migrations                    |
| `make messages`| Generate translation files (ru)           |
| `make locale` | Compile translation files (ru)             |
| `make static` | Collect static files (depends on `frontend`) |
| `make frontend-install` | Install frontend dependencies (bun) |
| `make frontend` | Install + build the React SPA (bun)     |
| `make frontend-lint` | Lint frontend (Biome)              |
| `make frontend-typecheck` | Type-check frontend (tsc)       |
| `make frontend-check` | Lint + type-check frontend (run by `make check`) |
| `make test`   | Run test suite                             |
| `make check`  | Run frontend checks + pre-commit hooks     |
| `make django-checks` | Run Django checks                  |
| `make pip`    | Install dev dependencies                   |
| `make update` | Update dependencies and pre-commit hooks   |
| `make ci`     | Run pip, checks, and tests                 |
| `make dump`   | Backup database to odin.sql                |
| `make restore`| Restore database from odin.sql             |


## Deployment

```shell
make deploy
```

This will: pull changes, sync dependencies, run migrations, collect static, and restart services.


## Testing

```shell
make test
```


## Code Quality

```shell
make check      # Run all pre-commit hooks
uv run ruff check .       # Lint only
uv run ruff format .      # Format only
uv run bandit -c pyproject.toml .  # Security analysis
```


## Database Operations

```shell
make dump       # Backup database to odin.sql
make restore    # Restore database from odin.sql
```


## Project Structure

```
odin/
├── api/              # REST API endpoints
├── apps/             # Django apps (core, relays, sensors, weather)
├── tests/            # Test suite
├── static/           # Admin assets, favicons, images, fonts (no public CSS/JS)
├── templates/admin/  # Django admin templates only
├── locale/           # Translation files
├── settings/         # Django settings (base, dev, prod, test, sqlite)
├── configs/          # Nginx and other configs
├── frontend/         # React + TypeScript SPA (Vite + Bun + Biome)
├── opencode.json     # Opencode configuration
└── manage.py         # Django management script
```


## Frontend (React SPA)

The dashboard UI is a React + TypeScript SPA under `frontend/`, built with
[Vite](https://vitejs.dev/), bundled by [Bun](https://bun.sh/), and
linted/formatted with [Biome](https://biomejs.dev/). It replaces the previous
Django-rendered dashboard (`index.html`, `chart.html`, `header.html`,
`modal.html`).

- Built artifacts (`frontend/dist/`) are picked up by `collectstatic` and
  served at `/` by Django. `/sw.js` and `/manifest.webmanifest` are served
  by dedicated views (see `odin/apps/core/views.py`).
- The SPA is served same-origin and uses Django session cookies
  (`sessionid`) plus the `csrftoken` cookie for write endpoints.
- See [`frontend/README.md`](frontend/README.md) for component layout,
  API client, PWA configuration, and session/CSRF details.

Quick start:

```shell
cd frontend
bun install
bun run dev      # http://localhost:5173, proxies /api, /admin, /static to Django
bun run build    # type-checks and emits static assets to frontend/dist
```

Or from the project root:

```shell
make frontend-install   # bun install
make frontend           # install + build
make frontend-check     # biome lint + tsc typecheck
```

The Django dev server (`uv run manage.py runserver`) serves the SPA at `/`
once `frontend/dist/` is built; otherwise it returns a 500 with a hint to
run `make frontend`.
