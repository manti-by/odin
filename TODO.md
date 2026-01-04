# TODO - Security and Bug Fixes

This document outlines prioritized security and bug fixes for the Odin project.

## Critical Priority (Fix Immediately)

### 1. Add Authentication to All API Endpoints

**Status:** Pending  
**Severity:** Critical

**Description:** All API endpoints currently use `AllowAny` permission, allowing unrestricted access to sensor data reading, creation, and relay control.

**Affected Files:**
- `odin/api/v1/sensors/views.py:19` (SensorsView)
- `odin/api/v1/sensors/views.py:27` (SensorsUpdateView)
- `odin/api/v1/sensors/views.py:39` (SensorsLogView)
- `odin/api/v1/sensors/views.py:49` (DS18B20DataView)
- `odin/api/v1/relays/views.py:11` (RelayView)
- `odin/api/v1/relays/views.py:19` (RelayUpdateView)
- `odin/api/v1/core/views.py` (LogsView, ChartView)

**Solution:**
```python
from rest_framework.permissions import IsAuthenticated

class SensorsView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    # ...
```

**Alternative for IoT devices:**
- IP whitelist filtering
- Token-based authentication in request headers
- Mutual TLS authentication

---

### 2. Add Rate Limiting to API Endpoints

**Status:** Pending  
**Severity:** Critical

**Description:** No rate limiting is configured for API endpoints that accept data from external sources. The `SensorsLogView` accepts POST requests from sensors without any rate limiting.

**Affected Files:**
- `odin/settings/base.py`
- `odin/api/v1/sensors/views.py`

**Solution:**

1. Add `django-ratelimit` to installed apps:
```python
# settings/base.py
INSTALLED_APPS = [
    ...
    'ratelimit',
]
```

2. Add rate limit decorator to views:
```python
from django_ratelimit.decorators import ratelimit

class SensorsLogView(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = SensorLogSerializer
    
    @ratelimit(key='ip', rate='100/h', block=True)
    def perform_create(self, serializer):
        ...
```

---

## High Priority (Fix Within 1 Week)

### 3. Move DEBUG=False to Production Settings

**Status:** Pending  
**Severity:** High

**Description:** `DEBUG=True` is set in base settings. This should only be enabled in development environments.

**Affected File:** `odin/settings/base.py:26`

**Solution:**

1. Remove `DEBUG = True` from `base.py`
2. Ensure `DEBUG = True` is only in `dev.py`
3. Generate a cryptographically secure secret key:

```python
# settings/prod.py
import secrets

SECRET_KEY = secrets.token_urlsafe(64)
# Or use environment variable
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
```

---

### 4. Fix IDOR Vulnerability in Update Endpoints

**Status:** Pending  
**Severity:** High

**Description:** The `SensorsUpdateView` and `RelayUpdateView` use URL parameters to identify resources without verifying user authorization or resource ownership.

**Affected Files:**
- `odin/api/v1/sensors/views.py:26-36`
- `odin/api/v1/relays/views.py:18-28`

**Solution:**

```python
class SensorsUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Sensor.objects.all()
    lookup_field = "sensor_id"
    lookup_url_kwarg = "sensor_id"

    def perform_update(self, serializer):
        # Add object-level permission check
        if self.request.user != serializer.instance.owner:
            raise PermissionDenied()
        serializer.instance.context.update(**serializer.validated_data["context"])
        serializer.instance.save(update_fields=["context"])
```

---

### 5. Add Field Whitelisting to Context Updates

**Status:** Pending  
**Severity:** High

**Description:** The context dictionary is merged directly without sanitization, potentially allowing injection of unexpected fields.

**Affected Files:**
- `odin/api/v1/sensors/views.py:35`
- `odin/api/v1/relays/views.py:27`

**Solution:**

```python
def perform_update(self, serializer):
    allowed_fields = {"target_temp", "state", "min_temp", "max_temp"}  # Define allowed fields
    context = {k: v for k, v in serializer.validated_data["context"].items() 
               if k in allowed_fields}
    serializer.instance.context.update(**context)
    serializer.instance.save(update_fields=["context"])
```

---

### 6. Add Input Validation Bounds to Chart Serializer

**Status:** Pending  
**Severity:** High

**Description:** The `ChartTypeSerializer` accepts decimal values without range validation.

**Affected File:** `odin/api/v1/core/serializers.py:20-26`

**Solution:**

```python
class ChartTypeSerializer(serializers.Serializer):
    value = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        max_value=1000,  # Add reasonable upper bound
        min_value=-100,  # Add reasonable lower bound
        allow_null=False,
    )
    metric = serializers.ChoiceField(choices=MetricChoices.choices)
```

---

## Medium Priority (Fix Within 2 Weeks)

### 7. Add Database Index to SensorLog.sensor_id

**Status:** Pending  
**Severity:** Medium

**Description:** `SensorLog.sensor_id` is frequently queried but lacks a database index.

**Affected File:** `odin/apps/sensors/models.py:77`

**Solution:**

```python
class SensorLog(models.Model):
    sensor_id = models.CharField(max_length=32, db_index=True)
```

**Note:** This requires a new migration.

---

### 8. Configure Secure Cookie Settings

**Status:** Pending  
**Severity:** Medium

**Description:** Default session cookie settings are used without explicit security configuration.

**Affected File:** `odin/settings/prod.py`

**Solution:**

```python
# Production settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
```

---

### 9. Add Security Headers Middleware

**Status:** Pending  
**Severity:** Medium

**Description:** Missing middleware for security headers (CSP, X-Content-Type-Options, Referrer-Policy).

**Affected File:** `odin/settings/base.py` (MIDDLEWARE)

**Solution:**

```python
MIDDLEWARE = [
    ...
    'csp.middleware.CSPMiddleware',
    'django.middleware.security.SecurityMiddleware',
    ...
]

# Add to settings
CSP_DEFAULT_SRC = ["'self'"]
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CONTENT_TYPE_NOSNIFF = True
```

---

### 10. Enable CSRF Protection for State-Changing Operations

**Status:** Pending  
**Severity:** Medium

**Description:** API endpoints with `AllowAny` permission may be vulnerable to CSRF attacks if cookies are used for session management.

**Affected Files:**
- `odin/api/v1/sensors/views.py`
- `odin/api/v1/relays/views.py`

**Solution:**

```python
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SensorsUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    # Note: For token-based authentication, CSRF is typically not needed
    # This is only necessary if using session-based authentication
    ...
```

---

## Low Priority (Fix Within 1 Month)

### 11. Remove Hardcoded IP from Production ALLOWED_HOSTS

**Status:** Pending  
**Severity:** Low

**Description:** Private IP address `192.168.1.100` is hardcoded in production settings.

**Affected File:** `odin/settings/prod.py:5`

**Solution:**

```python
ALLOWED_HOSTS = ["odin.manti.by"]
```

---

### 12. Fix N+1 Query in Index View

**Status:** Pending  
**Severity:** Low

**Description:** The index view may cause N+1 query issues when loading sensor data.

**Affected File:** `odin/apps/core/views.py:14-20`

**Solution:**

```python
def index_view(request: HttpRequest) -> HttpResponse:
    weather = Weather.objects.current()
    sensors = Sensor.objects.active().prefetch_related('latest_log')
    context = {
        "time": timezone.localtime(timezone.now()).strftime("%d %b %Y %H:%M"),
        "weather": weather,
        "sensors": sensors,
    }
    return render(request, "index.html", context=context)
```

---

### 13. Create Log Directory Dynamically

**Status:** Pending  
**Severity:** Low

**Description:** Log path is hardcoded and may fail if directory doesn't exist.

**Affected File:** `odin/settings/base.py:201-204`

**Solution:**

```python
import os

LOG_DIR = os.getenv("LOG_DIR", "/var/log/odin")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'handlers': {
        'file': {
            'filename': f"{LOG_DIR}/django.log",
            ...
        }
    }
}
```

---

### 14. Validate Music Path Against Symlink Attacks

**Status:** Pending  
**Severity:** Low

**Description:** If `MUSIC_PATH` is manipulated, could scan unintended directories.

**Affected File:** `odin/apps/music/management/commands/scan_music.py:22-24`

**Solution:**

```python
from pathlib import Path

def get_file_list() -> Iterable:
    music_path = Path(settings.MUSIC_PATH).resolve()
    
    # Validate path is within expected directory
    base_path = Path("/var/lib/odin/music").resolve()
    if not str(music_path).startswith(str(base_path)):
        raise ValueError(f"MUSIC_PATH outside allowed directory: {settings.MUSIC_PATH}")
    
    if not music_path.exists() or not music_path.is_dir():
        raise ValueError(f"Invalid MUSIC_PATH: {settings.MUSIC_PATH}")
    
    for ext in (f"**/*.{ext}" for ext in ("flac", "mp3", "wav")):
        yield from glob.glob(str(music_path / f"**/*.{ext}"), recursive=True)
```

---

### 15. Optimize Weather.current() Query

**Status:** Pending  
**Severity:** Low

**Description:** `WeatherManager.current()` makes two queries when one would suffice.

**Affected File:** `odin/apps/weather/models.py:18-23`

**Solution:**

```python
def current(self) -> Weather:
    start_range = timezone.now().replace(minute=0, second=0)
    end_date = start_range + timedelta(minutes=60)
    queryset = self.get_queryset().filter(
        period__range=(start_range, end_date)
    ).order_by("-period")
    # Use first() instead of exists() + last()
    return queryset.first() or self.get_queryset().last()
```

---

## Code Quality Improvements

### 16. Fix Factory Boy Type Errors

**Status:** Pending  
**Severity:** Low

**Description:** Type checker reports errors in `odin/tests/factories.py` related to Factory Boy imports.

**Solution:** Update imports to use correct paths:
```python
from factory import Faker, LazyAttribute, Sequence, SubFactory, post_generation
from factory.django import DjangoModelFactory
from factory.base import Meta
```

---

## Ongoing Maintenance

### 17. Regular Dependency Updates

**Status:** Ongoing

**Description:** Keep packages updated to avoid known vulnerabilities.

**Commands:**
```bash
uv sync --upgrade           # Update all dependencies
uv run pre-commit autoupdate  # Update pre-commit hooks
```

**Schedule:** Monthly

---

### 18. Security Audit

**Status:** Ongoing

**Description:** Run security analysis tools regularly.

**Commands:**
```bash
uv run bandit -c pyproject.toml .  # Security analysis
uv run ruff check .                # Linting
uv run pytest --cov=odin odin/     # Test coverage
```

**Schedule:** Before each release

---

## Progress Tracking

| Task | Priority | Status | Assigned To | Due Date | Notes |
|------|----------|--------|-------------|----------|-------|
| Add Authentication | Critical | Pending | | | |
| Add Rate Limiting | Critical | Pending | | | |
| Fix DEBUG Mode | High | Pending | | | |
| Fix IDOR | High | Pending | | | |
| Field Whitelisting | High | Pending | | | |
| Input Validation | High | Pending | | | |
| DB Index | Medium | Pending | | | |
| Cookie Settings | Medium | Pending | | | |
| Security Headers | Medium | Pending | | | |
| Weather Query | Low | Pending | | | |

---

## References

- Django Security Documentation: https://docs.djangoproject.com/en/stable/topics/security/
- DRF Authentication: https://www.django-rest-framework.org/api-guide/authentication/
- django-ratelimit: https://django-ratelimit.readthedocs.io/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
