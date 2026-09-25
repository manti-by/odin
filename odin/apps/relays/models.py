from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import query
from django.utils.translation import gettext_lazy as _

from odin.apps.core.exceptions import RedisReadError
from odin.apps.core.redis_bus import RedisBus


if TYPE_CHECKING:
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
        self.state, self.mode = self.get_target_state()
        self.save()
        return self.state

    def get_target_state(self) -> tuple[RelayState, RelayMode]:
        """Compute the target state and mode without persisting them."""
        from odin.apps.relays.services import RelayTargetStateService

        return RelayTargetStateService(self).get_target_state()

    def refresh_state(self) -> str | None:
        """Refresh relay state from Redis and persist it.

        Fetches the latest state for this relay from Redis, updates the
        model context, and saves the change. Returns None when Redis is
        unavailable or no state is stored for the relay.

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
