---
title: Sensor Model QuerySet and Manager Investigation
date: 2026-07-16
type: investigation
status: reference
session_id: ses_0962f4978ffe74aY6KpTYHBzEk
services: [sensors]
branch: -
tickets: []
tags: [models, queryset, manager]
related: []
---

# Sensor Model QuerySet and Manager Investigation

## TL;DR

Investigated `Sensor` model, `SensorQuerySet`, and `SensorManager` in `odin/apps/sensors/models.py`. Found four QuerySet filter methods (`active`, `visible`, `ds18b20`, `esp8266`), a custom `SensorManager` proxying `active()` and `visible()` at the manager level, and a `SensorLogManager` with a `current()` method for latest-log-per-sensor queries.

---

## SensorType

**File:** `odin/apps/sensors/models.py:20-22`

```python
class SensorType(models.TextChoices):
    DS18B20 = "DS18B20", "DS18B20"
    ESP8266 = "ESP8266", "ESP8266"
```

## SensorQuerySet

**File:** `odin/apps/sensors/models.py:25-36`

```python
class SensorQuerySet(query.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def visible(self):
        return self.filter(is_visible=True)

    def ds18b20(self):
        return self.filter(type=SensorType.DS18B20)

    def esp8266(self):
        return self.filter(type=SensorType.ESP8266)
```

## SensorManager

**File:** `odin/apps/sensors/models.py:39-47`

```python
class SensorManager(models.Manager):
    def get_queryset(self):
        return SensorQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def visible(self):
        return self.get_queryset().visible()
```

`active()` and `visible()` are callable directly on the manager; `ds18b20()` and `esp8266()` require chaining through `Sensor.objects.all().ds18b20()`.

## Sensor Model

**File:** `odin/apps/sensors/models.py:50`

Fields: `sensor_id` (db_index), `linked_sensor_id`, `relay_id`, `name`, `type` (DS18B20/ESP8266 via `SensorType`), `is_active`, `is_visible`, `order`, `context` (JSONField), `temp_offset`, `humidity_offset`, `created_at`, `updated_at`. Manager: `objects = SensorManager()`. Properties: `latest_log`, `is_alive`, `linked_sensor`, `relay`, `temp`, `target_temp`, `temp_hysteresis`, `humidity`.

## SensorLogManager

**File:** `odin/apps/sensors/models.py:139-147`

Custom manager on `SensorLog` with a `current()` method returning the latest log per active sensor via a subquery.

---

## Follow-ups

- None

## References

- **File:** `odin/apps/sensors/models.py`
