from unittest.mock import patch

import pytest

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSystemdStatusAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:systemd")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_systemd__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_systemd__returns_status(self):
        mocked = {"scheduler.service": {"status": "active"}, "worker.service": {"error": "test error"}}
        with patch("odin.api.v1.core.views.systemd_status", return_value=mocked):
            response = self.client.get(self.url, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["scheduler.service"]["status"] == "active"
        assert response.data["worker.service"]["error"] == "test error"
