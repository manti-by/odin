# Generated by Django 5.2.2 on 2025-06-09 17:54

from django.db import migrations, models

from odin.apps.weather.models import WeatherProvider


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Weather",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField()),
                ("provider", models.CharField(choices=WeatherProvider.choices, default=WeatherProvider.POGODA_BY)),
                ("data", models.JSONField(default=dict)),
                ("period", models.DateTimeField(db_index=True)),
                ("synced_at", models.DateTimeField(auto_now=True, db_index=True)),
            ],
            options={
                "verbose_name": "weather",
                "verbose_name_plural": "weather",
            },
        ),
    ]
