from django.db import migrations, models


def link_sensor_logs(apps, schema_editor):
    Sensor = apps.get_model("sensors", "Sensor")
    SensorLog = apps.get_model("sensors", "SensorLog")

    mapping = {}
    for sensor in Sensor.objects.order_by("created_at", "id").iterator():
        mapping[sensor.sensor_id] = sensor.pk

    batch = []
    for log in SensorLog.objects.exclude(sensor_id_old__isnull=True).exclude(sensor_id_old="").iterator():
        target = mapping.get(log.sensor_id_old)
        if log.sensor_id != target:
            log.sensor_id = target
            batch.append(log)
        if len(batch) >= 1000:
            SensorLog.objects.bulk_update(batch, ["sensor"])
            batch = []
    if batch:
        SensorLog.objects.bulk_update(batch, ["sensor"])


class Migration(migrations.Migration):
    dependencies = [
        ("sensors", "0015_sensor_order"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensorlog",
            old_name="sensor_id",
            new_name="sensor_id_old",
        ),
        migrations.AlterField(
            model_name="sensorlog",
            name="sensor_id_old",
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name="Sensor ID (legacy)"),
        ),
        migrations.AddField(
            model_name="sensorlog",
            name="sensor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="logs",
                to="sensors.sensor",
                verbose_name="Sensor",
            ),
        ),
        migrations.RunPython(link_sensor_logs, migrations.RunPython.noop),
    ]
