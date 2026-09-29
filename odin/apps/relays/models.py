from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.conf import settings
from django.db import models, transaction
from django.db.models import query
from django.utils.translation import gettext_lazy as _

from odin.apps.core.exceptions import RedisReadError
from odin.apps.core.redis_bus import RedisBus


if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from odin.apps.sensors.models import Sensor

logger = logging.getLogger(__name__)


class RelayType(models.TextChoices):
    PUMP = "PUMP", _("Pump")
    SERVO = "SERVO", _("Servo")
    VALVE = "VALVE", _("Valve")


class RelayState(models.TextChoices):
    ON = "ON", _("ON")
    OFF = "OFF", _("OFF")
    UNKNOWN = "UNKNOWN", _("Unknown")

    @classmethod
    def active_choices(cls) -> list:
        return [(cls.ON.value, cls.ON.label), (cls.OFF.value, cls.OFF.label)]


class RelayMode(models.TextChoices):
    UNKNOWN = "UNKNOWN", _("Unknown")
    FALLBACK = "FALLBACK", _("Fallback")
    FORCED = "FORCED", _("Forced")
    IGNORED = "IGNORED", _("Ignored")

    SUMMER = "SUMMER", _("Summer")
    MIDSEASON = "MIDSEASON", _("Midseason")
    BASIC = "BASIC", _("Basic")
    ANTIFREEZE = "ANTIFREEZE", _("Antifreeze")


class RelayStateError(Exception):
    """Raised when relay state cannot be retrieved from Redis."""


class RelayQuerySet(query.QuerySet):
    def active(self) -> query.QuerySet:
        return self.filter(is_active=True)


class RelayManager(models.Manager):
    def get_queryset(self) -> RelayQuerySet:
        return RelayQuerySet(self.model, using=self._db)

    def active(self) -> query.QuerySet:
        return self.get_queryset().active()


class Relay(models.Model):
    relay_id: models.CharField[str] = models.CharField(max_length=32, db_index=True, verbose_name=_("Relay ID"))
    name: models.CharField[str] = models.CharField(max_length=32, verbose_name=_("Name"))
    type: models.CharField[str] = models.CharField(max_length=32, choices=RelayType.choices, verbose_name=_("Type"))
    is_active: models.BooleanField[bool] = models.BooleanField(default=True, verbose_name=_("Is active"))

    state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.choices, null=True, blank=True, max_length=32, verbose_name=_("Relay state")
    )
    mode: models.CharField[RelayMode] | None = models.CharField(
        choices=RelayMode.choices, null=True, blank=True, max_length=32, verbose_name=_("Relay mode")
    )
    force_state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.active_choices(), null=True, blank=True, max_length=32, verbose_name=_("Force relay state")
    )

    related_relay: models.ForeignKey[Relay] | None = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="related_relays",
        verbose_name=_("Related relay"),
    )
    context: models.JSONField[dict] = models.JSONField(default=dict, verbose_name=_("Context"))

    created_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = RelayManager()

    class Meta:
        verbose_name = _("relay")
        verbose_name_plural = _("relays")

    def __str__(self):
        return f"Relay {self.relay_id}"

    @property
    def is_on(self) -> bool:
        return self.state == RelayState.ON

    @property
    def is_pump(self) -> bool:
        return self.type == RelayType.PUMP

    @property
    def sensor(self) -> Sensor | None:
        return self.sensors.order_by("-created_at").first()  # ty: ignore

    @property
    def target_state(self) -> RelayState:
        """Computed target state. Read-only: does not persist or log."""
        return self.get_target_state()[0]

    def get_target_state(self) -> tuple[RelayState, RelayMode]:
        """Compute the target state and mode without persisting them."""
        from odin.apps.relays.services import RelayTargetStateService

        return RelayTargetStateService(self).get_target_state()

    def apply_target_state(self, user: User | None = None, before: dict[str, Any] | None = None) -> RelayState:
        """Compute the target state/mode, persist them, and log the transition.

        This is the explicit write path for the ``target_state`` computation; use it
        instead of the read-only ``target_state`` property when a persisted update
        (and its audit row) is intended. ``before`` can be supplied by callers that
        already hold a snapshot taken earlier in the request.

        Args:
            user: the acting user, or None for system-driven changes.
            before: optional snapshot of the relay taken before the change.

        Returns:
            The persisted target state.
        """
        from odin.apps.relays.services import RelayLogService

        if before is None:
            before = RelayLogService.snapshot(self)
        with transaction.atomic():
            self.state, self.mode = self.get_target_state()
            self.save()
            RelayLogService(self, user=user).log_change(before)
        return self.state

    def refresh_state(self) -> str | None:
        """Refresh relay state from Redis and persist it.

        Fetches the latest state for this relay from Redis, updates the
        model, and saves the change. This is a reconciliation path (admin
        rendering, SPA polling, pub/sub wake-ups) that can observe transient
        states - including ODIN's own control echo before Coruscant confirms
        it - so it deliberately does not append a RelayLog row. Audit rows are
        written at the explicit command boundaries instead (API update, admin
        save via ``apply_target_state``).

        Returns:
            The state value from Redis if available, otherwise None.
        """
        try:
            message = RedisBus.get_relay_latest_message(self.relay_id)
        except RedisReadError:
            logger.error(f"Failed to get state from Redis for relay {self.relay_id}")
            return None

        if message is None:
            logger.error(f"There are no messages for relay {self.relay_id}")
            return None

        if state := message.get("data", {}).get("state"):
            self.state = state
            self.save(update_fields=["state", "updated_at"])
            return state


class RelayLog(models.Model):
    relay: models.ForeignKey[Relay] | None = models.ForeignKey(
        Relay,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="logs",
        verbose_name=_("Relay"),
    )

    old_state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.choices, null=True, blank=True, max_length=32, verbose_name=_("Old state")
    )
    new_state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.choices, null=True, blank=True, max_length=32, verbose_name=_("New state")
    )
    old_mode: models.CharField[RelayMode] | None = models.CharField(
        choices=RelayMode.choices, null=True, blank=True, max_length=32, verbose_name=_("Old mode")
    )
    new_mode: models.CharField[RelayMode] | None = models.CharField(
        choices=RelayMode.choices, null=True, blank=True, max_length=32, verbose_name=_("New mode")
    )
    old_force_state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.active_choices(), null=True, blank=True, max_length=32, verbose_name=_("Old force state")
    )
    new_force_state: models.CharField[RelayState] | None = models.CharField(
        choices=RelayState.active_choices(), null=True, blank=True, max_length=32, verbose_name=_("New force state")
    )
    old_context: models.JSONField[dict] = models.JSONField(default=dict, verbose_name=_("Old context"))
    new_context: models.JSONField[dict] = models.JSONField(default=dict, verbose_name=_("New context"))

    updated_by: models.ForeignKey[settings.AUTH_USER_MODEL] | None = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="relay_logs",
        verbose_name=_("Updated by"),
    )

    updated_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    created_at: models.DateTimeField[datetime] = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))

    objects = models.Manager()

    class Meta:
        verbose_name = _("relay log")
        verbose_name_plural = _("relay logs")
        ordering = ("-created_at",)

    def __str__(self):
        return f"RelayLog {self.relay} @ {self.created_at}"
