from django.conf import settings

from odin.apps.sensors.models import Sensor
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from .serializers import SensorSerializer


class SensorsView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self):
        return Sensor.objects.order_by("-created_at")

    def filter_queryset(self, queryset):
        items = (queryset.filter(sensor_id=item).last() for item in settings.SATELLITES)
        return list(filter(lambda x: x, items))
