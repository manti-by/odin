from django.contrib import admin
from django.forms import ModelForm
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Relay


@admin.register(Relay)
class RelayAdmin(admin.ModelAdmin):
    fields = ("relay_id", "name", "type", "is_active", "state", "force_state", "schedule", "updated_at", "created_at")
    list_display = ("relay_id", "name", "type", "is_active", "state", "updated_at", "created_at")
    list_filter = ("type",)
    readonly_fields = ("state", "schedule", "updated_at", "created_at")

    def schedule(self, obj: Relay) -> str:
        if not (schedule := obj.context.get("schedule")):
            return "-"

        html = render_to_string("admin/schedule.html", {"schedule": schedule})
        return format_html(html)

    schedule.short_description = _("schedule")

    def state(self, obj: Relay) -> str:
        return obj.state

    state.short_description = _("state")

    def save_model(self, request: HttpRequest, obj: Relay, form: ModelForm, change: bool):
        schedule = {str(d): {str(h).zfill(2): False for h in range(24)} for d in range(7)}
        for field in form.data:
            if field.startswith("schedule"):
                _, day, hour = field.split("-")
                schedule[day][hour] = True
        obj.context.update({"schedule": schedule})
        super().save_model(request, obj, form, change)
