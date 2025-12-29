from django.db.models import query
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.sensors.serializers import (
    SensorLogSerializer,
    SensorSerializer,
    SensorUpdateSerializer,
)
from odin.apps.sensors.models import Sensor, SensorLog
from odin.apps.sensors.services import get_temp_sensors_chart_data


class SensorsView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self) -> query.QuerySet:
        return Sensor.objects.active()


class SensorsUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = SensorUpdateSerializer
    queryset = Sensor.objects.all()

    lookup_field = "sensor_id"
    lookup_url_kwarg = "sensor_id"

    def perform_update(self, serializer: SensorUpdateSerializer) -> None:
        serializer.instance.context.update(**serializer.validated_data["context"])
        serializer.instance.save(update_fields=["context"])


class SensorsLogView(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = SensorLogSerializer

    def get_queryset(self) -> query.QuerySet:
        return SensorLog.objects.current()

    def perform_create(self, serializer: SensorLogSerializer) -> SensorLog:
        return SensorLog.objects.create(**serializer.validated_data)


class DS18B20DataView(APIView):
    def get(self, request: Request) -> Response:
        data = get_temp_sensors_chart_data()
        return Response(data)
