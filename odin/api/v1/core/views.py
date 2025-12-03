from django.http import HttpResponse
from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from odin.api.v1.core.serializers import ChartTypeSerializer
from odin.apps.core.utils import create_metric_gauge_chart


class HealthCheckView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        return Response()


class ChartView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        serialiser = ChartTypeSerializer(data=request.query_params)
        serialiser.is_valid(raise_exception=True)

        contents = create_metric_gauge_chart(**serialiser.validated_data)
        return HttpResponse(contents, content_type="image/svg+xml")
