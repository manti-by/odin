from django.contrib import admin

from .models import RawSensor, Sensor


@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ("sensor_id", "temp", "humidity", "updated_at", "created_at")
    search_fields = ("sensor_id",)
    list_filter = ("sensor_id", "updated_at")


@admin.register(RawSensor)
class RawSensorAdmin(admin.ModelAdmin):
    list_display = ("address", "temp", "created_at")
    search_fields = ("address",)
    list_filter = ("address", "created_at")
