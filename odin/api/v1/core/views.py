from rest_framework import views

from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HealthCheckView(views.APIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        return Response()
