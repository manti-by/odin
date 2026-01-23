from collections import defaultdict
from typing import Any

from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from odin.apps.core.kafka import KafkaService

from .models import Relay, RelayType


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    fields = (
        "relay_id",
        "name",
        "type",
        "is_active",
        "sensor",
        "state",
        "force_state",
        "schedule",
        "updated_at",
        "created_at",
    )
    list_display = ("relay_id", "name", "type", "is_active", "state", "updated_at")
    list_filter = ("type",)
    readonly_fields = ("sensor", "state", "schedule", "updated_at", "created_at")

    class Media:
        css = {"all": ("css/admin/schedule.css",)}
        js = ("js/admin/schedule.js",)

    @admin.display(description=_("sensor"))
    def sensor(self, obj: Relay) -> str:
        if not (sensor := obj.sensor):
            return "-"

        url = reverse("admin:sensors_sensor_change", args=[sensor.id])  #
        return format_html('<a href="{}">{}</a>', url, sensor)

    @admin.display(description=_("schedule"))
    def schedule(self, obj: Relay) -> str:
        schedule = obj.context.get("schedule")
        html = render_to_string("admin/schedule.html", {"schedule": schedule, "relay_type": obj.type})
        return format_html(html)

    @admin.display(description=_("state"))
    def state(self, obj: Relay) -> str:
        return obj.state

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

        super().save_model(request, obj, form, change)

        KafkaService.send_relay_update(
            relay_id=obj.relay_id,  # ty: ignore[invalid-argument-type]
            target_state=obj.target_state,
        )
