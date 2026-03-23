import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from odin.tests.factories import AuthFactory


@pytest.mark.django_db
class TestTokenAuthentication:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:healthcheck")

    def test_no_token_returns_401(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid_token")
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_token_returns_200(self):
        auth = AuthFactory()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {auth.token}")
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
