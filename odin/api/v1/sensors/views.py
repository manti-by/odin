from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny

from odin.api.v1.sensors.serializers import SensorLogSerializer, SensorSerializer
from odin.apps.sensors.models import Sensor, SensorLog, SensorLogQuerySet


class SensorsView(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self) -> SensorLogQuerySet:
        return Sensor.objects.active()


class SensorsLogView(CreateAPIView, ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SensorLogSerializer

    def get_queryset(self) -> SensorLogQuerySet:
        return SensorLog.objects.current()

    def perform_create(self, serializer: SensorLogSerializer):
        SensorLog.objects.create(**serializer.validated_data)
