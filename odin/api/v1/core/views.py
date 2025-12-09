from django.http import HttpResponse
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from odin.api.v1.core.serializers import ChartTypeSerializer, LogSerializer
from odin.apps.core.models import Log
from odin.apps.core.utils import create_metric_gauge_chart


class LogsView(CreateAPIView):
    serializer_class = LogSerializer

    def perform_create(self, serializer: LogSerializer):
        Log.objects.create(**serializer.validated_data)


class HealthCheckView(RetrieveAPIView):
    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        return Response()


class ChartView(RetrieveAPIView):
    serializer_class = ChartTypeSerializer

    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        contents = create_metric_gauge_chart(**serializer.validated_data)
        return HttpResponse(contents, content_type="image/svg+xml")
