from __future__ import annotations

from datetime import timedelta

from django.db import models
from django.db.models import query
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Browser(models.TextChoices):
    CHROME = "chrome", _("Chrome")
    FIREFOX = "firefox", _("Firefox")
    SAFARI = "safari", _("Safari")
    EDGE = "edge", _("Edge")
    OTHER = "other", _("Other")


class DeviceQuerySet(models.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)


class DeviceManager(models.Manager):
    def get_queryset(self) -> DeviceQuerySet:
        return DeviceQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()


class Device(models.Model):
    subscription: models.JSONField[dict] = models.JSONField(verbose_name=_("Push subscription data"))
    browser = models.CharField(
        max_length=20,
        choices=Browser.choices,
        default=Browser.OTHER,
        verbose_name=_("Browser"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    is_admin = models.BooleanField(default=False, verbose_name=_("Is admin"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = DeviceManager()

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")

    def __str__(self):
        return f"Device ({self.browser})"


class LogQuerySet(models.QuerySet):
    def errors_last_day(self) -> query.QuerySet:
        cutoff = timezone.now() - timedelta(hours=24)
        return self.exclude(levelname__in=("DEBUG", "INFO")).filter(asctime__gte=cutoff).order_by("-asctime")[:10]


class LogManager(models.Manager):
    def get_queryset(self) -> LogQuerySet:
        return LogQuerySet(self.model, using=self._db)

    def errors_last_day(self) -> query.QuerySet:
        return self.get_queryset().errors_last_day()


class Log(models.Model):
    name = models.CharField(max_length=100)
    msg = models.CharField(max_length=100)
    filename = models.CharField(max_length=100)
    levelname = models.CharField(max_length=100)
    asctime = models.DateTimeField()
    stacktrace = models.JSONField(null=True, blank=True)
    variables = models.JSONField(null=True, blank=True)

    objects = LogManager()

    class Meta:
        verbose_name = _("log")
        verbose_name_plural = _("logs")

    def __str__(self):
        return f"Log at {self.asctime}"
