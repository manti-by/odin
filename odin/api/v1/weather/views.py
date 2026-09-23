from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.weather.serializers import WeatherSerializer
from odin.apps.weather.models import Weather


class WeatherCurrentView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        weather = Weather.objects.current()
        if weather is None:
            return Response(None)
        return Response(WeatherSerializer(weather).data)
