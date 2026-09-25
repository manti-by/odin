from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("sensors", "0020_sensor_linked_sensor_fk"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sensor",
            name="linked_sensor_id_old",
        ),
    ]
