# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ODIN is a Django-based backend application that provides RESTful APIs and management interfaces for IoT systems. It serves as the core backend for:
- Coruscant: Raspberry Pi-based heating control system
- Centax: Satellite sensor telemetry with real-time IoT data streams
- Interactive dashboards with customizable graphs and historical analytics

## Development Setup

The project uses **UV** as the package manager (not pip or poetry). Environment setup:

```bash
uv sync --all-extras          # Install all dependencies
uv sync --all-extras --dev    # Install with dev dependencies
```

## Common Commands

### Development Server
```bash
make run                      # Start development server
uv run python manage.py runserver
```

### Database Operations
```bash
make migrate                  # Run migrations
make migrations              # Create migrations
uv run python manage.py makemigrations
make dump                    # Backup database to odin.sql
make restore                 # Restore database from odin.sql
```

### Testing
```bash
make test                    # Run tests (excludes view tests, uses test settings)
make full-test              # Run all tests including views with --create-db
uv run pytest -m "not views" --disable-warnings --ds=odin.settings.test odin/
```

### Code Quality
```bash
make check                   # Run all pre-commit hooks (ruff, bandit, etc.)
make django-checks          # Run Django system checks
uv run ruff check .         # Lint only
uv run ruff format .        # Format only
```

### Static Files & Internationalization
```bash
make static                  # Collect static files
make messages               # Generate translation files (ru)
make locale                 # Compile translation files (ru)
```

### Dependencies & Updates
```bash
make update                 # Update dependencies and pre-commit hooks
uv run uv-bump             # Update dependency versions
```

## Project Architecture

### Django Apps Structure
- **core**: Base models (Device, Browser choices), management commands
- **sensors**: IoT sensor data handling
- **relays**: Hardware relay control
- **currency**: Exchange rate tracking and trends
- **electricity**: Electricity consumption monitoring
- **music**: Music-related functionality
- **weather**: Weather data services
- **provider**: Provider-related services

### API Structure
- **odin.api.v1**: RESTful API endpoints using Django REST Framework
  - `/api/v1/core/`: Core API endpoints
  - `/api/v1/relays/`: Relay control APIs
  - `/api/v1/sensors/`: Sensor data APIs

### Settings Configuration
The project uses environment-specific settings:
- **base.py**: Common settings
- **dev.py**: Development settings (default for manage.py)
- **prod.py**: Production settings
- **test.py**: Test-specific settings
- **sqlite.py**: SQLite-specific settings

Default settings module: `odin.settings.dev`

### Testing Framework
- Uses **pytest** with pytest-django
- Factory Boy for test data generation
- Tests organized by type: `odin/tests/models/`, `odin/tests/services/`, `odin/tests/views/`
- View tests marked with pytest markers and can be excluded
- Test settings: `odin.settings.test`

### Code Quality Tools
- **Ruff**: Linting and formatting (line length: 120, Python 3.13+)
- **Bandit**: Security analysis
- **pre-commit**: Automated code quality checks
- **ty**: Type checking
- Specific exclusions for settings and test directories

### Key Dependencies
- Django 5.2.7 with DRF 3.16.1
- PostgreSQL (psycopg2-binary) + Redis for production
- Django-RQ for background tasks
- Django-APScheduler for scheduled tasks
- Kafka integration for IoT data streams
- Web push notifications support

### Development Patterns
- Environment variables for configuration (SECRET_KEY, database settings)
- Custom model managers with QuerySets for active records filtering
- RESTful API design following Django REST Framework patterns
- Internationalization support (Russian translations)
- Background task processing with RQ
- IoT data ingestion and real-time processing capabilities