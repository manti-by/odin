import logging
from collections import defaultdict
from typing import Any

from django.contrib import admin
from django.db import transaction
from django.forms import ModelForm
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from odin.apps.core.redis_bus import RedisBus

from .models import Relay, RelayState, RelayType


logger = logging.getLogger(__name__)


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    fields = (
        "relay_id",
        "name",
        "type",
        "sensor",
        "related_relay",
        "is_active",
        "force_state",
        "target_state",
        "state",
        "schedule",
        "updated_at",
        "created_at",
    )
    list_display = ("relay_id", "name", "type", "is_active", "forced_state", "target_state", "state", "updated_at")
    list_filter = ("type",)
    readonly_fields = ("sensor", "target_state", "state", "schedule", "updated_at", "created_at")

    class Media:
        css = {"all": ("css/admin/schedule.css",)}
        js = ("js/admin/schedule.js",)

    @admin.display(description=_("sensor"))
    def sensor(self, obj: Relay | None) -> str:
        if obj is None or obj.pk is None:
            return "-"
        if not (sensor := obj.sensor):
            return "-"

        url = reverse("admin:sensors_sensor_change", args=[sensor.id])  #
        return format_html('<a href="{}">{}</a>', url, sensor)

    @admin.display(description=_("schedule"))
    def schedule(self, obj: Relay | None) -> str:
        if obj is None:
            schedule = None
            relay_type = ""
        else:
            schedule = obj.context.get("schedule") if isinstance(obj.context, dict) else None
            relay_type = obj.type
        html = render_to_string("admin/schedule.html", {"schedule": schedule, "relay_type": relay_type})
        return mark_safe(html)  # noqa: S308

    @admin.display(description=_("forced"))
    def forced_state(self, obj: Relay | None) -> RelayState | None:
        if obj is None:
            return RelayState.UNKNOWN
        return obj.force_state

    @admin.display(description=_("target"))
    def target_state(self, obj: Relay | None) -> RelayState | None:
        if obj is None:
            return RelayState.UNKNOWN
        return obj.target_state

    @admin.display(description=_("current"))
    def state(self, obj: Relay | None) -> RelayState | None:
        if obj is None:
            return RelayState.UNKNOWN
        return obj.state

    def changelist_view(self, request: HttpRequest, extra_context: dict | None = None) -> TemplateResponse:
        for relay in self.get_queryset(request):
            relay.refresh_state()
        return super().changelist_view(request, extra_context)

    def change_view(
        self, request: HttpRequest, object_id: int, form_url: str = "", extra_context: dict | None = None
    ) -> TemplateResponse:
        if relay := self.get_object(request, object_id):
            relay.refresh_state()
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request: HttpRequest, obj: Relay, form: ModelForm, change: bool):
        period_data: dict[int, dict[str, Any]] = defaultdict(dict)
        for field_name, value in form.data.items():
            if field_name.startswith("schedule-periods-") and len(parts := field_name.split("-")) >= 4:
                period_index, field_type = int(parts[2]), parts[3]
                period_data[period_index][field_type] = value

        periods = []
        for period_index in sorted(period_data.keys()):
            period = period_data[period_index]
            if all(key in period for key in ("start_time", "end_time")):
                period_dict = {
                    "start_time": period["start_time"],
                    "end_time": period["end_time"],
                }

                if obj.type == RelayType.SERVO and period.get("target_temp"):
                    period_dict["target_temp"] = float(period["target_temp"])

                if obj.type == RelayType.PUMP and period.get("target_state"):
                    period_dict["target_state"] = period["target_state"]

                periods.append(period_dict)

        if periods:
            obj.context.update({"schedule": {"periods": periods}})

        with transaction.atomic():
            super().save_model(request, obj, form, change)

            published = RedisBus.publish_relay_control(
                relay_id=obj.relay_id,
                state=obj.target_state,
            )
            if not published:
                logger.error(f"Failed to publish relay control message to Redis for relay {obj.relay_id}")
