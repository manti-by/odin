# AGENTS.md

## Project Overview

Odin is a Django-based IoT dashboard for sensor management, weather monitoring, and home automation.
It uses Django 6 with Django REST Framework, PostgreSQL, Redis, and modern Python tooling.

## Project Structure

- All REST API related code placed in `./odin/api/`
- Django apps with models, admin classes, migrations and management commands in `./odin/apps/`
- eBus boiler control in `./odin/apps/boiler/` — `BoilerStatusService` (+ `BoilerModeService` /
  `BoilerModeController` decision logic) in the `services/` package (`ebusd.py`, `status.py`,
  `mode.py`, `controller.py`, `schedule.py`), `boiler_set` / `boiler_status` management commands,
  and a read API in `./odin/api/v1/boiler/` (`GET /api/v1/boiler/status/`); talks to the local
  `ebusd` daemon
- Tests in `./odin/tests/`
- Standalone MCP server in `./mcp_server/` — stdio server exposing read tools over the database,
  source docstrings, the wiki and the log directory. Project-specific values (roots, server name,
  Django settings module) live in `mcp_server/config.py`; the rest of the package is
  project-agnostic. Its tests are in `./mcp_server/tests/`
- React + TypeScript SPA (Vite + Bun + Biome) in `./frontend/` — dashboard UI, built to `frontend/dist/`
- Public-facing Django templates/static JS/CSS are no longer rendered (orphans still on disk
  under `./odin/templates/` and `./odin/static/{css,js}/`, slated for deletion); only the Django
  admin assets under `./odin/templates/admin/`, `./odin/static/css/admin/`, and
  `./odin/static/js/admin/` are live
- Shared static assets (favicons, images, fonts) live in `./odin/static/`
- Nginx configuration in `./configs/`

## Git Workflow

This project adheres strictly to the Git Flow branching model. AI agents must follow these guidelines:

### Main Branch:

- The `master` branch always contains production-ready, stable code.
- Never commit directly to `master`.
- Do not use `git push --force` on the `master` branch.
- Do not merge branches into `master` without explicit approval.

### Feature Branches:

- Create feature branches using the naming convention `<agent-name>/feature/<issue-id>-<descriptive-name>`, where `<agent-name>` can be `opencode`, `cursor`, `copilot`, etc.
- Use the [Conventional Commits](https://www.conventionalcommits.org) specification for commit messages (e.g., `feat:`, `fix:`, `docs:`).
- Ensure all local tests pass before committing.
- Use `git push --force-with-lease` if needed on your feature branch, but never on `master`.

### Pull Requests (PRs):

- Open a Pull Request for every completed feature branch.
- PRs must be reviewed and pass all CI checks before merging.
- The PR title should follow the Conventional Commits specification.

## Linear Workflow

- When starting implementation of any issue from `TODO`, move it to `In Progress` column.
- When feature is completed and PR is created, move it to `In Review` column.
- After approval, merge the feature branch into `master` and move the issue to `Done` column.
- If the feature branch is not merged into `master`, move it back to `In Progress` column.
- If the feature branch is closed without merging, move it to `Closed` column.

## Development Commands

### Package Management

```bash
uv sync                    # Install dependencies
uv sync --upgrade          # Upgrade dependencies
```

### Django Management

```bash
uv run manage.py runserver                  # Start development server
uv run manage.py migrate                    # Run database migrations
uv run manage.py makemigrations             # Create new migrations
uv run manage.py collectstatic --no-input   # Collect static files
uv run manage.py makemessages -l ru         # Create translation files
uv run manage.py compilemessages -l ru      # Compile translation files
```

### Frontend (React SPA)

The dashboard SPA lives in `./frontend/`. Run `make frontend` (or `make
frontend-install && make frontend`) before the first `collectstatic` /
`runserver` so the build output exists; otherwise the index view returns a
500 with a hint to build.

```bash
cd frontend
bun install                  # Install JS dependencies
bun run dev                  # Vite dev server on http://localhost:5173
                             # (proxies /api, /admin, /static to Django)
bun run build                # Type-check + production build to frontend/dist
bun run typecheck            # tsc --noEmit only
bun run lint                 # Biome check
bun run format               # Biome format --write
```

Makefile shortcuts (run from the project root):

```bash
make frontend-install        # bun install --cwd frontend
make frontend                # install + build (run by `make deploy`)
make frontend-lint           # biome check
make frontend-typecheck      # tsc -b --noEmit
make frontend-check          # lint + typecheck (run by `make check` / `make ci`)
```

`make static` depends on `make frontend`, so `collectstatic` always sees the
latest build. See [`frontend/README.md`](frontend/README.md) for the
component layout, API client, PWA configuration, and session/CSRF details.

Dev-only gotchas: Silk profiler is wired only under `DEBUG` (`odin/urls.py:40-45`), and the SPA
catch-all explicitly excludes `silk` (`odin/urls.py:34`) — keep any new non-SPA route out of that
lookahead or it will serve `index.html`.

### Database Operations

```bash
# Development
make dump     # Backup database to odin.sql
make restore  # Restore database from odin.sql
make migrate  # Run database migrations
make migrations  # Create new migrations
make locale   # Compile translation files

# Django checks
uv run manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
uv run manage.py check --fail-level WARNING --settings=odin.settings.sqlite
```

### Testing

```bash
# Run all tests
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/

# Run single test file
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/tests/api/test_sensors.py

# Run single test method
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/tests/api/test_sensors.py::TestSensorsAPI::test_sensors__list

# MCP server tests (no database required)
uv run pytest mcp_server/tests/

# Everything
uv run pytest mcp_server/tests/ odin/

# Run with coverage (if available)
uv run pytest --cov=odin --cov-report=term-missing odin/
```

Makefile targets (what CI actually runs — `make ci` = `install check django-checks test test-mcp`,
`Makefile:80`):

```bash
make test        # pytest over odin/ only
make test-mcp    # pytest over mcp_server/
make ci          # the full CI pipeline, in order
```

PostgreSQL must be running for `make test` — `test.py` inherits the Postgres config from `base.py`
and every DB-backed test errors with `OperationalError` otherwise. `make django-checks` uses the
in-memory SQLite settings and needs no server; `mcp_server/tests/` needs no database at all.

### Code Quality

```bash
# Run all pre-commit hooks
uv run pre-commit run

# Note: `make check` also runs `git add .` before `ty check` + pre-commit (Makefile:63-66)

# Individual tools
uv run ruff check .                 # Backend lint
uv run ruff format .                # Backend format
uv run ty check                     # Backend type checking (also runs via `make check`)
uv run pre-commit run bandit        # Backend security analysis (bandit is a pre-commit hook,
                                     #   not a project dependency — `uv run bandit` does not resolve)
make frontend-check                 # Frontend lint (Biome) + typecheck (tsc)
```

## Language & Environment

- Follow PEP 8 style guidelines, use Ruff for formatting (120 char line length)
- Use type hints for all function parameters and return values
- Prefer f-strings for string formatting over .format() or %
- Use list/dict/set comprehensions over map/filter when readable
- Prefer Pathlib over os.path for file operations
- Follow PEP 257 for docstrings (simple summary line plus detailed explanation)
- Use structural pattern matching (match/case) for complex conditionals
- Prefer EAFP (try/except) over LBYL (if checks) for Python idioms
- Prefer round brackets instead of square brackets where it possible (tuples instead of lists)

## Django Framework

- Follow Django best practices and the MVT pattern
- Use Django ORM effectively, avoid raw SQL
- Use select_related and prefetch_related to avoid N+1 queries
- Never modify migrations after deployment
- Class-based views for API, function-based views for Django apps views
- Put business logic to services, prefer functions, models and views should be short and clean

### Background Tasks

- RQ (`django-rq`) is wired in but idle: the admin UI is mounted at `admin/rq/`
  (`odin/urls.py:29`) and `odin/apps/core/scheduler.py:12` holds a `default` queue handle, yet nothing
  in the tree calls `enqueue` and there are no `queue_*` jobs. When adding one:
- Define jobs as additional functions with prefix `queue_`
- Configure queue names for different priority levels

```python
import django_rq


def sync_sensor_data(sensor_id: str):
    # Long-running sync operation
    return sensor_id


def queue_sync_sensor_data(sensor_id: str):
    queue = django_rq.get_queue("default")
    queue.enqueue(sync_sensor_data, sensor_id=sensor_id)
```

### Periodic Jobs

- Use APScheduler (via `django-apscheduler`) for scheduled tasks
- Define jobs in `odin/apps/core/scheduler.py` within the app
- Use `scheduler.scheduled_job` for scheduling
- Live jobs: `update_weather` (30 min), `update_voltage` (5 min), `update_exchange_rates` (4 h),
  `fetch_traffic` (15 min). `update_boiler_mode` is commented out (disabled 2026-09-22, MNT-216
  pending) — the boiler controller does not run periodically.

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from django.conf import settings
from django.core.management import call_command

scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)


@scheduler.scheduled_job("interval", minutes=30, id="update_weather")
def schedule_update_weather():
    call_command("update_weather")
```

### Relay control

- `Relay.state`/`Relay.mode` are persisted columns, but the API computes `mode`/`target_state` on
  read via `Relay.get_target_state()` — never trust the stored `mode` in responses
  (`odin/api/v1/relays/serializers.py:42`).
- `RelayState` is `ON`/`OFF`/`UNKNOWN` only (`IGNORED` was removed); `RelayMode.IGNORED` still
  exists (servo whose related pump is off).
- `perform_update` recomputes and persists `state`+`mode`, publishes via `RedisBus`, and records a
  `RelayLog` row via `RelayLogService.log_change()` (`odin/api/v1/relays/views.py:52`,
  `odin/apps/relays/services.py:49`); servos link to their pump via the nullable
  `related_relay` self-FK.
- Antifreeze fail-safe: `RelayTargetStateService.get_target_state()` answers `ANTIFREEZE` **first**,
  but only for missing/unusable weather or `outside_temp < -8` — pump `(ON, ANTIFREEZE)`, servo
  `(OFF, ANTIFREEZE)`. It outranks `force_state` and the override schedule, so a pump cannot be
  stopped during a freeze or a weather outage. The `-8 … 10 °C` default band is _not_ part of the
  fail-safe: it follows the cycle, schedule and sensor rules below.
- Override schedule: `context["override_schedule"]` mirrors `context["schedule"]` but its periods are
  state-only — `start_time`/`end_time`/`target_state` (`ON`/`OFF`, required), no `target_temp`. A
  matching period is applied immediately after `force_state`, before the weather and schedule rules,
  for every relay type including `VALVE`; the reported mode is `RelayMode.OVERRIDE`. `target_state`
  is logical (`ON` = heat/run) and is inverted for `SERVO`, whose `ON` closes the circuit. `end_time`
  is exclusive and overnight spans are supported. Periods with a missing or unknown `target_state`
  are dropped before the active period is selected, so a later overlapping valid period still
  applies (and only when none matches do the regular rules apply), while a period missing a time is
  rejected by the serializers. Hand-edited context data (a context that is not an object, non-dict
  period entries, non-string or non-list values) is skipped by `RelayTargetStateService` instead of
  raising. `RelayMode.OVERRIDE` needs migration
  `0012_alter_relay_mode_alter_relaylog_new_mode_and_more` (MNT-255, MNT-259).
- Force and override share one helper, `RelayTargetStateService.get_manual_target_state()`
  (`odin/apps/relays/services.py:183`), which returns `(state, mode)` or `None` and applies the servo
  inversion. Every type calls it in the same position, so an unsupported force/override never
  silently disappears from the API. The heat direction (pump `ON`, servo open) is also the fail-safe
  answer; the stop direction only lands when the fail-safe did not fire and, for a servo, the linked
  pump is on — `IGNORED` beats a forced or overridden close.
- Weather bands come from `RelayTargetStateService.get_weather_mode()`
  (`odin/apps/relays/services.py:149`), which returns the private `WeatherMode` enum
  (`NONE`/`ANTIFREEZE`/`DEFAULT`/`MIDSEASON`/`SUMMER`) rather than a `RelayMode`: "no usable weather"
  and the `-8 … 10 °C` default band must stay distinguishable, and only the reported mode is mapped
  back to `RelayMode`. `ANTIFREEZE` (`outside_temp < -8`) and the midseason edges stay on the
  **raw** temperature, so the fail-safe heat answer never depends on fetched humidity/wind.
- A weather row counts only through `get_latest_weather()` (`odin/apps/weather/services.py:17`):
  it needs a temperature, a `period` within two hours of now in either direction, and a `synced_at`
  within the last two hours (`WEATHER_MAX_AGE`). `Weather.objects.current()` is ageless and, having
  no ordering, falls back to the highest pk — which can be a _future_ forecast slot — so relay and
  boiler logic must not call it directly; the dashboard tile still does. `BoilerModeService.get_target_mode()`
  shares the helper, so the boiler and the relays agree on what "no weather" means.
- Midseason (`10 <= outside_temp < 17`): pump runs only in the active daytime window (`hour >= 6 and
hour % 2 == 0 and minute < 30`); servos stay open (`OFF, MIDSEASON`) for the whole band. Above
  17 °C the band extends to `outside_temp < 20` while the Steadman apparent temperature
  (`odin/apps/weather/services.py:apparent_temp`, `AT = Ta + 0.33e − 0.70ws − 4.00`) is `< 17` —
  a windy warm day keeps cycling the pump, a calm one stays `SUMMER`. Any missing `humidity`/
  `wind_speed` degrades to the raw-temp band (MNT-253). The lower edge became inclusive on
  2026-10-26, so `10.0 °C` is midseason, not the default band.
- Schedule cycle: when none of the higher-priority rules applies (`FORCED`, `OVERRIDE`, servo `UNKNOWN`,
  servo `IGNORED`, `SUMMER`, `ANTIFREEZE`, `MIDSEASON`), the relay is forced open for 30 minutes
  every 2 hours — `hour % 2 == 0 and minute < 30`, **no night guard**, so 00:00–00:30 runs too
  (`odin/apps/relays/services.py:87`). Pump `(ON, CYCLE)`, servo `(OFF, CYCLE)`. Outside the
  window the schedule applies as usual (`BASIC`, or `FALLBACK` with no matching period). Midseason
  keeps its own, _different_ night guard — do not merge the two rules.
- `RedisBus.publish_relay_control(relay_id, state, mode, user)` requires `mode` and puts it in the
  envelope. Both call sites publish the **freshly computed** pair, not the stored column: the API
  view recomputes it in `perform_update` and passes the acting user
  (`odin/api/v1/relays/views.py:78`); `RelayAdmin.save_model` publishes
  `obj.get_target_state()` (`odin/apps/relays/admin.py:127`). Passing `obj.mode` there would send a
  stale mode next to a fresh state.
- The `consumer` command applies both `state` and `mode` from a `RELAY_STATE_UPDATE` envelope
  (`odin/apps/core/management/commands/consumer.py:140-145`); coruscant echoes the mode it read from
  `GET /api/v1/relays/<relay_id>/`. A missing, `null` or unknown mode leaves the stored column
  untouched, so valve updates from an older coruscant never clobber it. `Relay.refresh_state()`
  applies `mode` from `relays:state:<relay_id>` on the same terms.

### Sensor data

- Ingest contract: `POST /api/v1/sensors/logs/` takes a string `sensor_id` (unknown IDs stored
  with `sensor=None`); producers omit fields they cannot provide.
- `Sensor.temp`/`humidity` are denormalized calibrated caches; `is_alive` derives from
  `updated_at` (10 min threshold, `odin/apps/sensors/models.py:111`). `SensorLogManager.current()`
  uses Postgres `DISTINCT ON (sensor)` (`odin/apps/sensors/models.py:129`).

## Code Style Guidelines

### Python Standards

- Python 3.14.x (`requires-python = ">=3.14,<3.15.0"`) with type hints encouraged
- Ensure code style consistency using Ruff
- Line length 120 characters
- Indentation 4 spaces

### Import Organization

Use Ruff isort with this order:

1. Standard library imports
2. Third-party imports
3. First-party imports
4. Django imports (also `rest_framework`, `django_rq`, `django_apscheduler`, `apscheduler`)
5. Odin imports (`odin`) — configured in `[tool.ruff.lint.isort.sections]`
6. Local folder imports

`mcp_server` is not its own section; its imports sort as first-party (tier 3).

Do **not** add `from __future__ import annotations` — it was removed project-wide in MNT-243
(`0b181fb`) now that Python 3.14 supports the annotations natively. Use PEP 585/604 syntax
directly (`models.ForeignKey[Sensor] | None`, `list[str]`, `Self`).

```python
import os
from decimal import Decimal

from django.db import models
from rest_framework import serializers

from odin.apps.sensors.models import Sensor
```

### Naming Conventions

- **Models**: `PascalCase` (e.g., `SensorLog`)
- **Functions/Variables**: `snake_case` (e.g., `get_sensor_data`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)
- **File Names**: `snake_case.py` (e.g., `sensor_utils.py`)
- **Classes**: `PascalCase` (e.g., `SensorService`)

### Type Hints

Use type hints for function signatures and complex variables:

```python
from decimal import Decimal


def get_sensor_data(sensor_id: str) -> dict[str, Decimal] | None:
    # Implementation here
    return None
```

### Django Patterns

#### Models

- Use PEP 585/604 annotation syntax natively (`X | None`, `list[str]`); no `__future__` import
- Include `created_at` and `updated_at` timestamp fields
- Use `verbose_name` and `verbose_name_plural` with translation support
- Implement custom QuerySets and Managers for complex queries
- Use `TextChoices` for enum fields

```python
from django.db import models
from django.utils.translation import gettext_lazy as _


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32, verbose_name=_("Sensor ID"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")
```

#### Views and ViewSets

- Use GenericViewSet with mixins for REST APIs if data retrieved directly from a database, e.g. `SensorsView`
- Use APIView with mixins for REST APIs if data generated, e.g. `DS18B20DataView`
- Include proper type hints for Request/Response
- Use `lookup_field` for custom URL parameters
- Implement `perform_create`/`perform_update` for custom logic

#### Serializers

- Use explicit field definitions for clarity
- Include validation constraints
- Use `ChoiceField` for enum fields
- Do not use a ModelSerializer, just a bare Serializer

#### API Versioning

- URL-based versioning: `/api/v1/...`
- Include version in DRF router namespace: `api:v1:sensors:list`
- Increment version for breaking changes only
- The aggregate `core/dashboard/` endpoint was removed (MNT-218); per-model packages live directly
  under `odin/api/v1/` (`core`, `currency`, `electricity`, `logs`, `provider`, `sensors`, `relays`,
  `boiler`, `weather`)

## Dependency Management

- Manage Python dependencies via **[uv](https://github.com/astral-sh/uv)** and **virtual environments**.
- Manage frontend (JS/TS) dependencies via **[Bun](https://bun.sh/)** — `bun install` in `./frontend/`.
- The pinned Bun version lives in `frontend/package.json` (`packageManager`); CI uses the same version.
- `asyncpg` (MCP database tools) and `mcp` are runtime deps; `pytest-asyncio` is a dev dep enabling
  `asyncio_mode = "auto"`. `bandit` is not a project dep — it runs through pre-commit only.
- CI resolves the Python version from `requires-python` via `python-version-file: "pyproject.toml"`,
  so bumping that field changes the CI runtime.

## Testing

- Focus testing on APIs and critical code paths
- Write integration tests for API endpoints and external integrations
- Use mocks for external services and slow dependencies
- Test error handling and validation logic
- Use meaningful test names that describe the scenario
- Test settings (`odin/settings/test.py:12`) use an MD5 password hasher for speed

### Testing Patterns

#### Test Structure

- Use pytest with pytest-django
- Create descriptive test method names with double underscores
- Use Factory Boy (via `pytest-factoryboy`) for test data
- Test both success and error cases
- Use parametrized tests for similar scenarios

```python
import pytest

from odin.tests.factories import SensorFactory
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSensorsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:list")

    def test_sensors__list_returns_active_only(self):
        SensorFactory(is_active=True)
        SensorFactory(is_active=False)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
```

#### Test Data

- Use Factory Boy (via `pytest-factoryboy`) for creating test instances
- Use meaningful default values in factories
- Test with different data variations

## Logging and Error Handling

### Logging

- Use Python's `logging` module, not print statements
- Create logger at module level: `logger = logging.getLogger(__name__)`
- Use appropriate log levels:
  - `DEBUG`: Detailed debug information
  - `INFO`: Confirmation of expected behavior
  - `WARNING`: Unexpected but handled issues
  - `ERROR`: Failures that need attention

```python
import logging

from tinytag import ParseError

from odin.apps.music.services import update_or_create_music

logger = logging.getLogger(__name__)


def process_file(file: str):
    logger.info(f"Processing file {file}")
    try:
        music, _ = update_or_create_music(file=file)
        logger.info(f"{file}: [{music.album}] {music.artist} - {music.title} - {music.year}")
    except ParseError as e:
        logger.error(f"{file}: {e}")
```

### Error Handling

- Use custom exception classes for domain-specific errors
- Log exceptions with context before re-raising

```python
class SensorError(Exception):
    """Base exception for sensor-related errors."""


class SensorNotFoundError(SensorError):
    """Raised when a sensor cannot be found."""


class SensorConnectionError(SensorError):
    """Raised when connection to a sensor fails."""
```

## Environment Configuration

### Settings Files (`odin/settings/`)

- `base.py`: Common settings
- `dev.py`: Development (DEBUG=True, ALLOWED_HOSTS="*")
- `test.py`: Testing (DEBUG=True, ERROR-level logging, MD5 password hasher for speed)
- `prod.py`: Production settings
- `sqlite.py`: In-memory SQLite settings for Django checks only

### Database

- **Development/Production/Testing**: PostgreSQL (`odin/settings/base.py:98`, inherited by `test.py`)
- **SQLite** only in `odin/settings/sqlite.py` (`:memory:`) for `make django-checks`, never pytest

## Security Guidelines

- Never commit secrets or API keys
- Use environment variables for sensitive configuration
- Run `bandit` security analysis before commits
- Validate all user inputs

## Pre-commit Hooks

`.pre-commit-config.yaml` combines generic file hygiene hooks with the Python toolchain:

- Generic (`pre-commit-hooks`): fix-byte-order-marker, check-merge-conflict, debug-statements,
  detect-private-key, requirements-txt-fixer
- Python: pyupgrade (Python 3.14+ syntax), ruff (linting), ruff-format, validate-pyproject,
  bandit (security analysis)

Frontend checks are not part of pre-commit; they run via `make frontend-check`
(`biome check` + `tsc -b --noEmit`) and the `frontend-checks` job in CI.

## Deployment

- Services: gunicorn, worker, scheduler, consumer (`manage.py consumer`, Redis pub/sub for
  sensor + relay updates), nginx
- Redis contract (`odin/apps/core/redis_bus.py`): control channel `relays:control`
  (`REDIS_RELAYS_CHANNEL`), telemetry channel `sensors:telemetry` (`REDIS_SENSORS_CHANNEL`), last
  known state under `relays:state:<relay_id>`; envelope
  `{type: RELAY_STATE_UPDATE | SENSOR_DATA_UPDATE, data, timestamp}`. Kafka was removed entirely —
  do not add Kafka code back.
- Boiler/eBUS services: `ebusd` (must run with `--enabledefine --scanconfig=08`) and
  `boiler-refresh.timer` (must be **enabled**; re-sends the last boiler override every 60 s)
- Use systemd for service management
- `make deploy` builds the SPA (`make frontend`) before `collectstatic` and
  reloads nginx, so the React build artifacts are always served fresh
- The MCP server is launched by the agent client, not by systemd: `uv run python -m mcp_server.main`
  (registered in `opencode.json`). It reads only, so it needs no separate service unit

## Common Issues

### Testing

- Always use `@pytest.mark.django_db` for database tests
- Use `--create-db` flag for a fresh test database

### Migrations

- Check for pending migrations: `make django-checks`
- Create migrations after model changes

### Boiler (eBUS)

- `boiler_status`/`boiler_set` failing with `ERR: element not found` for every field = the ebusd
  daemon lost its device config (drops from ~230 to ~12-13 loaded messages — see `ebusctl info`).
  Fix: `sudo systemctl restart ebusd`.
- `boiler-refresh.timer` must be enabled, otherwise the boiler reverts to its panel settings a few
  minutes after the last SetMode write.
- ebusd options live in `/etc/default/ebusd`; the boiler address (08) is pinned via
  `--scanconfig=08`, and `--enabledefine` is required for `boiler_set`'s `write -def`.

## Performance Optimization

- Use `select_related` and `prefetch_related` for query optimization
- Implement proper database indexing
- Cache frequently accessed data with Redis

## AI Behavior

Response style - Concise and minimal:

- Provide minimal, working code without unnecessary explanation
- Omit comments unless absolutely essential for understanding
- Skip boilerplate and obvious patterns unless requested
- Use type inference and shorthand syntax where possible
- Focus on the core solution, skip tangential suggestions
- Assume familiarity with language idioms and framework patterns
- Let code speak for itself through clear naming and structure
- Avoid over-explaining standard patterns and conventions
- Provide just enough context to understand the solution
- Trust the developer to handle obvious cases independently
