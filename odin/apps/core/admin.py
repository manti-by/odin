from django.contrib import admin

from .models import Device, Log


def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    app_list = app_dict.values()
    return app_list


admin.AdminSite.get_app_list = get_app_list  # type: ignore[invalid-assignment]


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "browser", "is_active", "is_admin", "created_at", "updated_at")
    list_filter = ("browser", "is_active", "created_at")
    search_fields = ("subscription",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("levelname", "filename", "name", "msg", "asctime")
    search_fields = ("msg",)
    list_filter = ("levelname", "filename", "asctime")
