from django.contrib import admin

from .models import Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("sensor_id", "temp", "humidity", "synced_at", "created_at")
    search_fields = ("sensor_id",)
    list_filter = ("sensor_id", "synced_at")
