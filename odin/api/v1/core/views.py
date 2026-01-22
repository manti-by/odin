from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.core.serializers import ChartTypeSerializer, DeviceSubscriptionSerializer, LogSerializer
from odin.apps.core.models import Device, Log
from odin.apps.core.utils import create_metric_gauge_chart


class ApplicationServerKeyView(APIView):
    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        return Response(
            {"application_server_key": settings.FIREBASE_CLOUD_MESSAGING_PUBLIC_KEY},
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )


@method_decorator(csrf_exempt, name="dispatch")
class DeviceView(CreateAPIView, ListAPIView):
    serializer_class = DeviceSubscriptionSerializer
    queryset = Device.objects.active()

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        return Response({"count": self.get_queryset().count()})

    def perform_create(self, serializer: DeviceSubscriptionSerializer):
        subscription = serializer.validated_data["subscription"]
        browser = serializer.validated_data.get("browser", "other")
        endpoint = subscription.get("endpoint") if isinstance(subscription, dict) else None

        if endpoint:
            existing = Device.objects.filter(subscription__endpoint=endpoint).first()
            if existing:
                existing.subscription = subscription
                existing.browser = browser
                existing.is_active = True
                existing.save(update_fields=["subscription", "browser", "is_active"])
                return

        Device.objects.create(subscription=subscription, browser=browser, is_active=True)


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
