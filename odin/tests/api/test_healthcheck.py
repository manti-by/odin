from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


class TestHealthcheck:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:healthcheck")

    def test_healthcheck(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
