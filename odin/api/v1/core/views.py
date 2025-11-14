from decimal import Decimal

from django.http import HttpResponse
from django.urls.exceptions import Http404

from odin.apps.core.utils import create_gauge_chart
from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


class HealthCheckView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        return Response()


class ChartView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> HttpResponse:
        try:
            value = Decimal(request.query_params.get("value", 75))
            min_value = Decimal(request.query_params.get("min_value", 0))
            max_value = Decimal(request.query_params.get("max_value", 100))
            threshold = Decimal(request.query_params.get("threshold", 10))
        except TypeError as e:
            raise Http404 from e

        contents = create_gauge_chart(value=value, min_value=min_value, max_value=max_value, threshold=threshold)
        return HttpResponse(contents, content_type="image/svg+xml")
