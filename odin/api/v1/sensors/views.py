from datetime import datetime, timedelta

from django.db.models import query
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        def _parse_dt(value: str | None) -> datetime | None:
            if not value:
                return None
            dt = parse_datetime(value)
            if dt is None:
                return None
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        end = _parse_dt(end_param)
        if end is None:
            end = timezone.now()

        start = _parse_dt(start_param) or (end - timedelta(hours=48))

        data = get_temp_sensors_chart_data(start=start, end=end)
        return Response(data)
