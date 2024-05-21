from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from odin.apps.sensors.models import Sensor
from .serializers import SensorSerializer


class SensorsView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self):
        return Sensor.objects.order_by("-created_at")
