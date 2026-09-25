from django.db import migrations, models


def link_sensors_to_relays(apps, schema_editor):
    Relay = apps.get_model("relays", "Relay")
    Sensor = apps.get_model("sensors", "Sensor")

    mapping = {}
    for relay in Relay.objects.order_by("created_at", "id").iterator():
        mapping[relay.relay_id] = relay.pk

    batch = []
    for sensor in Sensor.objects.exclude(relay_id_old__isnull=True).exclude(relay_id_old="").iterator():
        target = mapping.get(sensor.relay_id_old)
        if sensor.relay_id != target:
            sensor.relay_id = target
            batch.append(sensor)
        if len(batch) >= 1000:
            Sensor.objects.bulk_update(batch, ["relay"])
            batch = []
    if batch:
        Sensor.objects.bulk_update(batch, ["relay"])


class Migration(migrations.Migration):
    dependencies = [
        ("sensors", "0016_sensorlog_sensor_fk"),
        ("relays", "0009_alter_relay_state"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sensor",
            old_name="relay_id",
            new_name="relay_id_old",
        ),
        # Drop the legacy column index before adding the FK, which uses the same generated index name.
        migrations.AlterField(
            model_name="sensor",
            name="relay_id_old",
            field=models.CharField(
                blank=True, db_index=False, max_length=32, null=True, verbose_name="Relay ID (legacy)"
            ),
        ),
        migrations.AddField(
            model_name="sensor",
            name="relay",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="sensors",
                to="relays.relay",
                verbose_name="Relay",
            ),
        ),
        migrations.AlterField(
            model_name="sensor",
            name="relay_id_old",
            field=models.CharField(
                blank=True, db_index=True, max_length=32, null=True, verbose_name="Relay ID (legacy)"
            ),
        ),
        migrations.RunPython(link_sensors_to_relays, migrations.RunPython.noop),
    ]
