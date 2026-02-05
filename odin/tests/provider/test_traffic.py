import pytest
from decimal import Decimal

from django.urls import reverse

from odin.apps.provider.models import Traffic


@pytest.mark.django_db
class TestTrafficModel:
    def test_traffic_creation(self):
        traffic = Traffic.objects.create(value=Decimal("10.50"), unit="GB")
        assert traffic.id is not None
        assert traffic.value == Decimal("10.50")
        assert traffic.unit == "GB"
        assert traffic.created_at is not None

    def test_traffic_str(self):
        traffic = Traffic.objects.create(value=Decimal("5.25"), unit="MB")
        assert str(traffic) == "5.25 MB"


@pytest.mark.django_db
class TestTrafficContext:
    def setup_method(self):
        self.client = getattr(self, "client", None) or self.client
        if not hasattr(self, "client"):
            from rest_framework.test import APIClient

            self.client = APIClient()

    def test_traffic_in_index_context(self):
        Traffic.objects.create(value=Decimal("15.00"), unit="GB")
        response = self.client.get(reverse("index"))
        assert response.status_code == 200
        assert "traffic" in response.context
        assert response.context["traffic"] is not None
        assert response.context["traffic"].value == Decimal("15.00")
        assert response.context["traffic"].unit == "GB"
