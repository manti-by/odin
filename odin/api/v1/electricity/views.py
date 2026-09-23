from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.electricity.serializers import VoltageSerializer
from odin.apps.electricity.models import VoltageLog


class VoltageCurrentView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        voltage = VoltageLog.objects.first()
        if voltage is None:
            return Response(None)
        return Response(VoltageSerializer(voltage).data)
