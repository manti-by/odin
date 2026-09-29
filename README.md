# ODIN server core application

[ODIN](https://github.com/manti-by/odin/) is a Django-based application delivering IoT dashboard and management interfaces. It powers data ingestion, processing, and visualization for the
[Coruscant](https://github.com/manti-by/coruscant/) Raspberry Pi-based heating control system, exposes API for
[Centax](https://github.com/manti-by/centax/) wireless sensors,
and features an interactive dashboard with customizable graphs and historical analytics.

[![Python 3.13](https://img.shields.io/badge/python-3.13-green.svg)](https://www.python.org/downloads/release/python-3136/)
[![Code style: ruff](https://img.shields.io/badge/ruff-enabled-informational?logo=ruff)](https://astral.sh/ruff)
[![License](https://img.shields.io/badge/license-BSD-blue.svg)](https://raw.githubusercontent.com/manti-by/pdw/master/LICENSE)

Author: Alexander Chaika <manti.by@gmail.com>

Source link: [https://github.com/manti-by/odin/](https://github.com/manti-by/odin/)

Requirements: Python 3.13, PostgreSQL 18, Redis 7, UV.

Current version: [v1.24.3 Bright Bluejay](https://github.com/manti-by/odin/releases/tag/v1.24.3)

Related Coruscant version: [v4.10.1 Blind Badger](https://github.com/manti-by/coruscant/releases/tag/v4.10.1)

## Quick Start (Django app)

1. Install [Python 3.13](https://www.python.org/downloads/release/python-3136/) and
   [UV tool](https://docs.astral.sh/uv/getting-started/installation/).

2. Clone sources, switch to working directory and setup environment:

```shell
git clone https://github.com/manti-by/odin.git
cd odin/
uv sync --all-extras --dev
```

3. Collect static, run migrations and create superuser:

```shell
uv run python manage.py collectstatic --no-input
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

4. Run development server:

```shell
uv run python manage.py runserver
```

## Frontend (React SPA)

The dashboard UI is a React + TypeScript SPA under `frontend/`, built with [Vite](https://vitejs.dev/) and run via
[Bun](https://bun.sh/), and linted/formatted with [Biome](https://biomejs.dev/). It replaces the previous
Django-rendered dashboard.

### Quick start:

Install [Bun](https://bun.sh/) (the version pinned in `frontend/package.json`) and setup the app.

```shell
cd frontend
bun install
bun run dev      # http://localhost:5173, proxies /api, /admin, /static to Django
bun run build    # type-checks and emits static assets to frontend/dist
```

## NOTES

The Django dev server (`uv run manage.py runserver`) serves the SPA at `/` once `frontend/dist/` is built;
otherwise it returns a 500 with a hint to run `make frontend`.

Check Makefile for more usefull command.
