# AGENTS.md

This file contains guidelines and commands for agentic coding agents working in the Odin repository.

## Project Overview

Odin is a Django-based IoT dashboard for sensor management, weather monitoring, and home automation. It uses Django 5.2.7 with Django REST Framework, PostgreSQL, Redis, and modern Python tooling.

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

### Testing
```bash
# Run all tests
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/

# Run single test file
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/tests/api/test_sensors.py

# Run single test method
uv run pytest --create-db --disable-warnings --ds=odin.settings.test odin/tests/api/test_sensors.py::TestSensorsAPI::test_sensors__list

# Run with coverage (if available)
uv run pytest --cov=odin --cov-report=term-missing odin/
```

### Code Quality
```bash
# Run all pre-commit hooks
uv run pre-commit run

# Individual tools
uv run ruff check .                 # Lint
uv run ruff format .                # Format
uv run black .                      # Alternative formatter
uv run bandit -c pyproject.toml .   # Security analysis
```

### Database Operations
```bash
# Development
make dump     # Backup database to odin.sql
make restore  # Restore database from odin.sql

# Django checks
uv run manage.py makemigrations --dry-run --check --verbosity=3 --settings=odin.settings.sqlite
uv run manage.py check --fail-level WARNING --settings=odin.settings.sqlite
```

## Code Style Guidelines

### Python Standards
- **Python Version**: 3.13+ with type hints encouraged
- **Line Length**: 120 characters
- **Indentation**: 4 spaces
- **Encoding**: UTF-8

### Import Organization
Use Ruff isort with this order:
1. `__future__` imports
2. Standard library imports
3. Third-party imports
4. First-party imports
5. Django imports
6. Odin imports
7. Local folder imports

```python
from __future__ import annotations

import os
from decimal import Decimal

from django.db import models
from rest_framework import serializers

from odin.apps.core.models import SomeModel
from .utils import helper_function
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
    return None

temp: Decimal | None = sensor.temp
```

### Django Patterns

#### Models
- Use `__future__ import annotations` for forward references
- Include `created_at` and `updated_at` timestamp fields
- Use `verbose_name` with translation support
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
- Use GenericViewSet with mixins for REST APIs
- Include proper type hints for Request/Response
- Use `lookup_field` for custom URL parameters
- Implement `perform_create`/`perform_update` for custom logic

```python
class SensorsView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer
    
    def get_queryset(self) -> query.QuerySet:
        return Sensor.objects.active()
```

#### Serializers
- Use explicit field definitions for clarity
- Include validation constraints
- Use `ChoiceField` for enum fields

```python
class SensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ["sensor_id", "name", "type", "context", "created_at"]
```

### Testing Patterns

#### Test Structure
- Use pytest with pytest-django
- Create descriptive test method names with double underscores
- Use Factory Boy for test data
- Test both success and error cases
- Use parametrized tests for similar scenarios

```python
@pytest.mark.django_db
class TestSensorsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:sensors:list")

    def test_sensors__list_returns_active_only(self):
        active_sensor = SensorFactory(is_active=True)
        SensorFactory(is_active=False)
        
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
```

#### Test Data
- Use Factory Boy for creating test instances
- Use meaningful default values in factories
- Test with different data variations

### Error Handling
- Use specific exception types
- Include meaningful error messages
- Log errors appropriately
- Handle edge cases gracefully

### Documentation
- Use docstrings for complex functions
- Include type hints in docstrings
- Use inline comments for business logic
- Translate user-facing strings

## Environment Configuration

### Settings Files
- `base.py`: Common settings
- `dev.py`: Development (DEBUG=True, ALLOWED_HOSTS="*")
- `test.py`: Testing (DEBUG=False, minimal logging)
- `prod.py`: Production settings
- `sqlite.py`: SQLite settings for Django checks

### Database
- **Development/Production**: PostgreSQL
- **Testing**: SQLite (configured in test settings)
- Use environment variables for sensitive configuration

## Security Guidelines
- Never commit secrets or API keys
- Use environment variables for configuration
- Run `bandit` security analysis before commits
- Validate all user inputs
- Use Django's built-in security features

## Pre-commit Hooks
The project uses pre-commit hooks for code quality:
- Ruff (linting and formatting)
- Black (code formatting)
- Bandit (security analysis)
- pyupgrade (Python 3.13+ syntax)
- curlylint (HTML linting)

## Deployment
- Use the `make deploy` command for production deployment
- Services: gunicorn, worker, scheduler, nginx
- Use systemd for service management
- Configure proper logging and monitoring

## Common Issues and Solutions

### Testing
- Always use `@pytest.mark.django_db` for database tests
- Use `--create-db` flag for fresh test database
- Test with both SQLite and PostgreSQL when possible

### Migrations
- Check for pending migrations: `make django-checks`
- Create migrations after model changes
- Test migrations in development before production

### Performance
- Use `select_related` and `prefetch_related` for query optimization
- Implement proper database indexing
- Cache frequently accessed data with Redis

## File Structure Guidelines
- Keep models in `models.py`
- Keep views in `views.py`
- Keep serializers in `serializers.py`
- Create `services.py` for business logic
- Create `utils.py` for helper functions
- Use `management/commands/` for custom Django commands