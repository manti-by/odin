from datetime import timedelta

from django.conf import settings
from django.db.models import query
from django.utils import timezone
from rest_framework import mixins
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from odin.api.authentication import TokenAuthentication
from odin.api.v1.sensors.serializers import (
    ChartOptionsQueryParamsSerializer,
    ChartQueryParamsSerializer,
    DashboardSensorsSerializer,
    SensorLogSerializer,
    SensorSerializer,
    SensorUpdateSerializer,
)
from odin.apps.sensors.models import Sensor, SensorLog, SensorType
from odin.apps.sensors.services import get_chart_data


class SensorsView(mixins.ListModelMixin, GenericViewSet):
    permission_classes = (AllowAny,)
    serializer_class = SensorSerializer

    def get_queryset(self) -> query.QuerySet:
        return Sensor.objects.active()


class SensorsUpdateView(mixins.UpdateModelMixin, GenericViewSet):
    authentication_classes = (SessionAuthentication, TokenAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "sensors_update"
    serializer_class = SensorUpdateSerializer
    queryset = Sensor.objects.all()

    lookup_field = "sensor_id"
    lookup_url_kwarg = "sensor_id"

    def perform_update(self, serializer: SensorUpdateSerializer) -> None:
        serializer.instance.context.update(  # ty: ignore
            **serializer.validated_data["context"]
        )
        serializer.instance.save(update_fields=["context"])  # ty: ignore


class SensorsLogView(mixins.CreateModelMixin, mixins.ListModelMixin, GenericViewSet):
    # TODO: Temporary disable until satellites updated
    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = SensorLogSerializer

    def get_queryset(self) -> query.QuerySet:
        return SensorLog.objects.current().select_related("sensor")

    def perform_create(self, serializer: SensorLogSerializer) -> SensorLog:
        return serializer.save()


class SensorDataView(APIView):
    permission_classes = (AllowAny,)
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


class DashboardSensorsView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    sensor_type: SensorType

    def get(self, request: Request) -> Response:
        sensors = (
            Sensor.objects.active().visible().filter(type=self.sensor_type).select_related("relay").order_by("order")
        )
        for sensor in sensors:
            if sensor.relay:
                sensor.relay.refresh_state()

        data = {"is_alive": all(sensor.is_alive for sensor in sensors), "sensors": sensors}
        return Response(DashboardSensorsSerializer(data).data)


class ESP8266DashboardView(DashboardSensorsView):
    sensor_type = SensorType.ESP8266


class DS18B20DashboardView(DashboardSensorsView):
    sensor_type = SensorType.DS18B20


class ChartOptionsView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        serializer = ChartOptionsQueryParamsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        sensor_type = serializer.validated_data["type"]
        options = settings.CHART_OPTIONS.get(sensor_type, settings.CHART_OPTIONS["DS18B20"])

        return Response(options)
