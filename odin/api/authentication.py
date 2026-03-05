from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from odin.apps.core.models import Auth


class TokenAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            raise AuthenticationFailed("Token not provided")

        parts = auth_header.split()

        if len(parts) != 2 or parts[0] != self.keyword:
            raise AuthenticationFailed("Invalid authorization header")

        token = parts[1]

        auth_instance = Auth.objects.filter(token=token).first()

        if not auth_instance:
            raise AuthenticationFailed("Invalid token")

        return (auth_instance, auth_instance)

    def authenticate_header(self, request):
        return self.keyword
