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

    def test_logs__create_with_stacktrace_and_variables(self):
        data = LogDataFactory(
            stacktrace={"type": "ValueError", "message": "test error", "line": 42},
            variables={"user_id": 123, "action": "login"},
        )
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        log = Log.objects.first()
        assert log.stacktrace == {"type": "ValueError", "message": "test error", "line": 42}
        assert log.variables == {"user_id": 123, "action": "login"}

    def test_logs__create_without_stacktrace_and_variables(self):
        data = LogDataFactory(stacktrace=None, variables=None)
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        log = Log.objects.first()
        assert log.stacktrace is None
        assert log.variables is None
