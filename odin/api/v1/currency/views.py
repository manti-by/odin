from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.currency.serializers import ExchangeRatesSerializer
from odin.apps.currency.models import ExchangeRate
from odin.apps.currency.services import get_exchange_rate_trends


class ExchangeRateCurrentView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        data = {
            "rates": ExchangeRate.objects.current(),
            "trends": get_exchange_rate_trends(),
        }
        return Response(ExchangeRatesSerializer(data).data)
