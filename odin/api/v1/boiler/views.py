from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from odin.api.v1.boiler.serializers import BoilerStatusSerializer
from odin.apps.boiler.services import BoilerModeService, BoilerStatusService, get_next_boil_schedule, parse_override


class BoilerStatusView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, *args: list, **kwargs: dict) -> Response:
        service = BoilerStatusService()
        override = service.current_override()
        flow_temp = hwc_temp = None
        if override:
            _, flow_temp, hwc_temp = parse_override(override)

        boil_at, clear_at = get_next_boil_schedule()
        data = {
            "mode": BoilerModeService().get_current_mode(),
            "target_temp": flow_temp,
            "hwc_temp": hwc_temp,
            "override_active": override is not None,
            "override_updated_at": service.override_updated_at(),
            "ebusd_alive": service.is_alive(),
            "next_boil_at": boil_at,
            "next_clear_at": clear_at,
        }
        return Response(BoilerStatusSerializer(data).data)
