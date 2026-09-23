from datetime import timedelta

import pytest

from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from odin.apps.core.models import Log
from odin.tests.factories import LogDataFactory


@pytest.mark.django_db
class TestLogsView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:logs:create")

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


@pytest.mark.django_db
class TestLogErrorsView:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:logs:errors")

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_log_errors__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_log_errors__empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_log_errors__returns_errors_last_day(self):
        Log.objects.create(
            name="test.stderr",
            msg="Test error message",
            filename="test_module.py",
            levelname="ERROR",
            asctime=timezone.now(),
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["msg"] == "Test error message"

    def test_log_errors__excludes_info_and_old_logs(self):
        Log.objects.create(
            name="test.stdout",
            msg="Info message",
            filename="test_module.py",
            levelname="INFO",
            asctime=timezone.now(),
        )
        Log.objects.create(
            name="test.stderr",
            msg="Old error",
            filename="test_module.py",
            levelname="ERROR",
            asctime=timezone.now() - timedelta(hours=48),
        )

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


@pytest.mark.django_db
class TestDeprecatedLogsAlias:
    """The old core/logs/ URL must keep accepting POSTs from external forwarders."""

    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:core:logs")

    def test_deprecated_logs__create(self):
        data = LogDataFactory()
        response = self.client.post(self.url, data=data, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Log.objects.exists()

    @pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
    def test_deprecated_logs__not_allowed_methods(self, method):
        response = getattr(self.client, method)(self.url, format="json")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
