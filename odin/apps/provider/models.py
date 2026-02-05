from __future__ import annotations

from django.db import models
from django.db.models import query
from django.utils.translation import gettext_lazy as _


class TrafficQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)


class TrafficManager(models.Manager):
    def get_queryset(self) -> TrafficQuerySet:
        return TrafficQuerySet(self.model, using=self._db)


class Traffic(models.Model):
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Value"))
    unit = models.CharField(max_length=16, verbose_name=_("Unit"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"), db_index=True)

    objects = TrafficManager()

    class Meta:
        verbose_name = _("traffic")
        verbose_name_plural = _("traffic")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.value} {self.unit} at {self.created_at}"
