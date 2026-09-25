from django.db import migrations, models


def link_sensors_to_linked_sensors(apps, schema_editor):
    Sensor = apps.get_model("sensors", "Sensor")

    mapping = {}
    for sensor in Sensor.objects.order_by("created_at", "id").iterator():
        mapping[sensor.sensor_id] = sensor.pk

    batch = []
    for sensor in Sensor.objects.exclude(linked_sensor_id_old__isnull=True).exclude(linked_sensor_id_old="").iterator():
        target = mapping.get(sensor.linked_sensor_id_old)
        if sensor.linked_sensor_id != target:
            sensor.linked_sensor_id = target
            batch.append(sensor)
        if len(batch) >= 1000:
            Sensor.objects.bulk_update(batch, ["linked_sensor"])
            batch = []
    if batch:
        Sensor.objects.bulk_update(batch, ["linked_sensor"])


class Migration(migrations.Migration):
    dependencies = [
        ("sensors", "0019_sensor_humidity_sensor_temp"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensor",
            old_name="linked_sensor_id",
            new_name="linked_sensor_id_old",
        ),
        # Drop the legacy column index before adding the FK, which uses the same generated index name.
        migrations.AlterField(
            model_name="sensor",
            name="linked_sensor_id_old",
            field=models.CharField(
                blank=True, db_index=False, max_length=32, null=True, verbose_name="Linked sensor ID (legacy)"
            ),
        ),
        migrations.AddField(
            model_name="sensor",
            name="linked_sensor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="linked_sensors",
                to="sensors.sensor",
                verbose_name="Linked sensor",
            ),
        ),
        migrations.AlterField(
            model_name="sensor",
            name="linked_sensor_id_old",
            field=models.CharField(
                blank=True, db_index=True, max_length=32, null=True, verbose_name="Linked sensor ID (legacy)"
            ),
        ),
        migrations.RunPython(link_sensors_to_linked_sensors, migrations.RunPython.noop),
    ]
