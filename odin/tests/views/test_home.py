from django.urls import reverse
from django.test import Client
from rest_framework import status


class TestHome:
    def setup_method(self):
        self.client = Client()
        self.url = reverse("index")

    def test_index(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
