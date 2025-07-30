from django.db import models
from django.utils.translation import gettext_lazy as _


class Sensor(models.Model):
    sensor_id = models.CharField(max_length=32)
    temp = models.DecimalField(max_digits=7, decimal_places=2)
    humidity = models.DecimalField(max_digits=7, decimal_places=2, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id} data for {self.created_at}"

    def serialize(self):
        return {
            "sensor_id": self.sensor_id,
            "temp": str(self.temp),
            "humidity": str(self.humidity),
            "created_at": str(self.created_at),
        }


class RawSensor(models.Model):
    address = models.CharField(max_length=32)
    temp = models.DecimalField(max_digits=7, decimal_places=2)
    is_synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("raw sensor")
        verbose_name_plural = _("raw sensors")

        managed = False
        db_table = "sensors_raw_data"

    def __str__(self):
        return f"Raw Sensor {self.address} data for {self.created_at}"


class SyncLog(models.Model):
    type = models.CharField(max_length=32, choices=[("IN", _("Incoming")), ("OUT", _("Outgoing"))])
    synced_at = models.DateTimeField(auto_now_add=True)
    synced_count = models.IntegerField()

    class Meta:
        verbose_name = _("sync log")
        verbose_name_plural = _("sync logs")

    def __str__(self):
        return f"Sync log at {self.synced_at}"
