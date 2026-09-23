from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.logs.serializers import ErrorLogSerializer, LogSerializer
from odin.apps.core.models import Log


class LogsView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LogSerializer

    def perform_create(self, serializer: LogSerializer):
        Log.objects.create(**serializer.validated_data)


class LogErrorsView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        logs = Log.objects.errors_last_day()
        return Response(ErrorLogSerializer(logs, many=True).data)
