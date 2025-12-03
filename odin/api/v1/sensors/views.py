from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import AllowAny

from odin.api.v1.sensors.serializers import SensorSerializer
from odin.apps.sensors.models import Sensor, SensorQuerySet


class SensorsView(CreateAPIView, ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self) -> SensorQuerySet:
        return Sensor.objects.current()

    def perform_create(self, serializer: SensorSerializer):
        Sensor.objects.create(**serializer.validated_data)