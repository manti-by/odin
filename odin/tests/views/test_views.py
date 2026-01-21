import pytest

from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.views
class TestViews:
    def test_index(self, client):
        response = client.get(reverse("index"), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_home_chart(self, client):
        response = client.get(reverse("sensors_home"), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_boiler_chart(self, client):
        response = client.get(reverse("sensors_boiler"), follow=True)
        assert response.status_code == status.HTTP_200_OK
