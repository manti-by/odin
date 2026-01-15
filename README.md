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

1. Install [Python 3.13](https://www.python.org/downloads/release/python-3120/) and
   [UV tool](https://docs.astral.sh/uv/getting-started/installation/)

2. Clone sources, switch to working directory and setup environment:

```shell
git clone https://github.com/manti-by/odin.git
cd odin/
uv sync --all-extras
```

3. Collect static, run migrations and create superuser:

```shell
uv run python manage.py collectstatic --no-input
uv run python manage.py createsuperuser
uv run python manage.py migrate
```

4. Run development server:

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
| `make static` | Collect static files                       |
| `make test`   | Run test suite                             |
| `make check`  | Run pre-commit hooks                       |
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
├── static/           # Static files (CSS, JS, images)
├── templates/        # Django templates
├── locale/           # Translation files
├── settings/         # Django settings (base, dev, prod, test, sqlite)
├── configs/          # Nginx and other configs
├── opencode.json     # Opencode configuration
└── manage.py         # Django management script
```
