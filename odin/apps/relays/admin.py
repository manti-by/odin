import logging
import re
from collections import defaultdict
from collections.abc import Mapping
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

from .models import Relay, RelayLog, RelayState, RelayType


logger = logging.getLogger(__name__)

SCHEDULE_PERIOD_PREFIX = "schedule-periods-"
OVERRIDE_SCHEDULE_PERIOD_PREFIX = "override_schedule-periods-"

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _collect_periods(form_data: Mapping[str, Any], prefix: str) -> dict[int, dict[str, Any]]:
    """Group the `<prefix><index>-<field>` inputs of a schedule component by period index.

    The schedule components are rendered as plain inputs outside the model form, so their values
    never reach the form and have to be read back from the raw POST data.
    """
    periods: dict[int, dict[str, Any]] = defaultdict(dict)
    for field_name, value in form_data.items():
        if not field_name.startswith(prefix):
            continue

        index, _, field_type = field_name[len(prefix) :].partition("-")
        if not index.isdigit() or not field_type:
            continue

        periods[int(index)][field_type] = value

    return periods


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    fields = (
        "relay_id",
        "name",
        "type",
        "sensor",
        "related_relay",
        "is_active",
        "state",
        "mode",
        "force_state",
        "schedule",
        "override_schedule",
        "updated_at",
        "created_at",
    )
    list_display = (
        "relay_id",
        "name",
        "type",
        "is_active",
        "state",
        "mode",
        "forced_state",
        "updated_at",
    )
    list_filter = ("type",)
    readonly_fields = ("sensor", "schedule", "override_schedule", "updated_at", "created_at")

    class Media:
        css = {"all": ("css/admin/schedule.css",)}
        js = ("js/admin/schedule.js",)

    @admin.display(description=_("sensor"))
    def sensor(self, obj: Relay | None) -> str:
        if obj is None or obj.pk is None:
            return "-"
        if not (sensor := obj.sensor):
            return "-"

        url = reverse("admin:sensors_sensor_change", args=[sensor.pk])
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

    @admin.display(description=_("override schedule"))
    def override_schedule(self, obj: Relay | None) -> str:
        if obj is None:
            override_schedule_data = None
        else:
            override_schedule_data = obj.context.get("override_schedule") if isinstance(obj.context, dict) else None
        html = render_to_string("admin/override_schedule.html", {"override_schedule": override_schedule_data})
        return mark_safe(html)  # noqa: S308

    @admin.display(description=_("forced"))
    def forced_state(self, obj: Relay | None) -> RelayState | None:
        if obj is None:
            return RelayState.UNKNOWN
        return obj.force_state

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
        period_data = _collect_periods(form.data, SCHEDULE_PERIOD_PREFIX)
        override_period_data = _collect_periods(form.data, OVERRIDE_SCHEDULE_PERIOD_PREFIX)

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

        override_periods = []
        for period_index in sorted(override_period_data.keys()):
            period = override_period_data[period_index]
            if not all(key in period for key in ("start_time", "end_time", "target_state")):
                continue

            if not (TIME_PATTERN.match(period["start_time"]) and TIME_PATTERN.match(period["end_time"])):
                logger.warning(f"Relay {obj.relay_id} override period {period_index} has an invalid time")
                continue

            if period["target_state"] not in RelayState.active_values():
                logger.warning(f"Relay {obj.relay_id} override period {period_index} has an invalid target state")
                continue

            override_periods.append(
                {
                    "start_time": period["start_time"],
                    "end_time": period["end_time"],
                    "target_state": period["target_state"],
                }
            )

        if isinstance(obj.context, dict):
            if periods:
                obj.context["schedule"] = {"periods": periods}

            if override_periods:
                obj.context["override_schedule"] = {"periods": override_periods}
            elif "override_schedule" in obj.context:
                # Every override period was removed in the admin
                obj.context["override_schedule"] = {"periods": []}
        else:
            logger.warning(f"Relay {obj.relay_id} has a non-dict context, schedule fields were skipped")

        with transaction.atomic():
            super().save_model(request, obj, form, change)

            state, mode = obj.get_target_state()
            published = RedisBus.publish_relay_control(
                relay_id=obj.relay_id, state=state, mode=mode, user=getattr(request, "user", None)
            )
            if not published:
                logger.error(f"Failed to publish relay control message to Redis for relay {obj.relay_id}")


@admin.register(RelayLog)
class RelayLogAdmin(admin.ModelAdmin):
    fieldsets = [
        ("", {"fields": ("relay",)}),
        ("State", {"fields": ("old_state", "new_state")}),
        ("Mode", {"fields": ("old_mode", "new_mode")}),
        ("Force state", {"fields": ("old_force_state", "new_force_state")}),
        ("Context", {"fields": ("old_context", "new_context")}),
        ("Changed", {"fields": ("updated_by", "updated_at", "created_at")}),
    ]
    list_display = (
        "relay",
        "old_state",
        "new_state",
        "updated_by",
        "updated_at",
        "created_at",
    )
    list_filter = ("relay",)
    readonly_fields = ("updated_by", "updated_at", "created_at")
