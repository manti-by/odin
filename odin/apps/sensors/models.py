from django.db import models
from django.utils.translation import gettext_lazy as _


class Sensor(models.Model):
    external_id = models.IntegerField(unique=True)
    sensor_id = models.CharField(max_length=32)
    temp = models.DecimalField(max_digits=7, decimal_places=2)
    humidity = models.DecimalField(max_digits=7, decimal_places=2)
    created_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = _("sensor")
        verbose_name_plural = _("sensors")

    def __str__(self):
        return f"Sensor {self.sensor_id} data for {self.created_at}"
