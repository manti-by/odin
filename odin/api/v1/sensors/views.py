from datetime import timedelta

from django.conf import settings
from django.db.models import query
from django.utils import timezone
from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.sensors.serializers import (
    ChartOptionsQueryParamsSerializer,
    ChartQueryParamsSerializer,
    SensorLogSerializer,
    SensorSerializer,
    SensorUpdateSerializer,
)
from odin.apps.sensors.models import Sensor, SensorLog
from odin.apps.sensors.services import get_chart_data


class SensorsView(mixins.ListModelMixin, GenericViewSet):
    serializer_class = SensorSerializer

    def get_queryset(self) -> query.QuerySet:
        return Sensor.objects.active()


class SensorsUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    serializer_class = SensorUpdateSerializer
    queryset = Sensor.objects.all()

    lookup_field = "sensor_id"
    lookup_url_kwarg = "sensor_id"

    def perform_update(self, serializer: SensorUpdateSerializer) -> None:
        serializer.instance.context.update(  # ty: ignore[possibly-missing-attribute]
            **serializer.validated_data["context"]
        )
        serializer.instance.save(update_fields=["context"])  # ty: ignore[possibly-missing-attribute]


class SensorsLogView(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    serializer_class = SensorLogSerializer

    def get_queryset(self) -> query.QuerySet:
        return SensorLog.objects.current()

    def perform_create(self, serializer: SensorLogSerializer) -> SensorLog:
        return SensorLog.objects.create(**serializer.validated_data)


class SensorDataView(APIView):
    queryset: query.QuerySet
    serializer_class = ChartQueryParamsSerializer

    def get(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        end = serializer.validated_data.get("end") or timezone.now()
        start = serializer.validated_data.get("start") or (end - timedelta(hours=48))

        data = get_chart_data(self.queryset.all(), start=start, end=end)
        return Response(data)


class DS18B20DataView(SensorDataView):
    queryset = Sensor.objects.active().ds18b20()


class ESP8266DataView(SensorDataView):
    queryset = Sensor.objects.active().esp8266()


class ChartOptionsView(APIView):
    def get(self, request: Request) -> Response:
        serializer = ChartOptionsQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        sensor_type = serializer.validated_data["type"]
        options = settings.CHART_OPTIONS.get(sensor_type, settings.CHART_OPTIONS["DS18B20"])

        return Response(options)
