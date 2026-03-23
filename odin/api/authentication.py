from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from odin.apps.core.models import Auth


class TokenAuthentication(BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request: Request) -> tuple[User, Auth]:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            raise AuthenticationFailed("Token not provided")

        try:
            keyword, token = auth_header.split()
        except ValueError as e:
            raise AuthenticationFailed("Invalid authorization header") from e

        if keyword.lower() != self.keyword.lower():
            raise AuthenticationFailed("Invalid authorization header")

        if not (auth := Auth.objects.filter(token=token).select_related("user").first()):
            raise AuthenticationFailed("Invalid token")

        return (auth.user, auth)

    def authenticate_header(self, request: Request) -> str:
        return self.keyword
