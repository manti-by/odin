from django.db import models
from django.utils.translation import gettext_lazy as _


class Sensor(models.Model):
    external_id = models.IntegerField(unique=True)
    sensor_id = models.CharField(max_length=32)
    temp = models.DecimalField(max_digits=7, decimal_places=2)
    humidity = models.DecimalField(max_digits=7, decimal_places=2)
    synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id} data for {self.created_at}"

    def serialize(self):
        return {
            "external_id": self.external_id,
            "sensor_id": self.sensor_id,
            "temp": str(self.temp),
            "humidity": str(self.humidity),
            "created_at": str(self.created_at),
        }


class SyncLog(models.Model):
    type = models.CharField(max_length=32, choices=[("IN", _("Incoming")), ("OUT", _("Outgoing"))])
    synced_at = models.DateTimeField(auto_now_add=True)
    synced_count = models.IntegerField()

    class Meta:
        verbose_name = _("sync log")
        verbose_name_plural = _("sync logs")

    def __str__(self):
        return f"Sync log at {self.synced_at}"
