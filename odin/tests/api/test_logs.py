import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.core.models import Log
from odin.tests.factories import LogDataFactory


@pytest.mark.django_db
class TestLogsView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:logs")

    @pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
    def test_sensors__not_allowed_methods(self, method):
        test_client_callable = getattr(self.client, method)
        response = test_client_callable(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_logs__create(self):
        data = LogDataFactory()
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Log.objects.exists()
