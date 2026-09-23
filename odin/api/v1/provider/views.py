from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.provider.serializers import TrafficSerializer
from odin.apps.provider.models import Traffic


class TrafficCurrentView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        traffic = Traffic.objects.first()
        if traffic is None:
            return Response(None)
        return Response(TrafficSerializer(traffic).data)
