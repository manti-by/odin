from django.shortcuts import render

from odin.apps.sensors.models import Sensor


def index(request):
    sensors = {
        s.sensor_id: s.serialize()
        for s in Sensor.objects.all().order_by("-created_at", "sensor_id").distinct("created_at", "sensor_id")[:5]
    }
    return render(request, "index.html", {"sensors": sensors})
