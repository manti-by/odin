from datetime import UTC, datetime

import pytest

from django.test.client import Client
from rest_framework.test import APIClient

from odin.tests.factories import AuthFactory


# Odd hour, minute 30: a time that never falls inside the 30-minute relay schedule cycle window
OUTSIDE_CYCLE_WINDOW = datetime(2025, 1, 6, 10, 30, 0, tzinfo=UTC)


@pytest.fixture
def pin_clock_outside_cycle_window(monkeypatch):
    """Keep the relay schedule branch out of the cycle window unless a test says otherwise.

    The relay cycle fires on every even hour for its first 30 minutes, so any test that reaches
    the schedule branch without pinning the clock would otherwise depend on when the suite runs.
    Tests that assert the cycle itself patch `timezone.localtime` themselves.
    """
    monkeypatch.setattr("odin.apps.relays.services.timezone.localtime", lambda *args, **kwargs: OUTSIDE_CYCLE_WINDOW)


@pytest.fixture
def client():
    return Client(HTTP_HOST="odin.local")
    return AuthFactory().token


@pytest.fixture
def api_client(db):
    client = APIClient()
    token = AuthFactory().token
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


@pytest.fixture(autouse=True)
def setup_api_client(db, request):
    """Auto-authenticates all API tests with a valid token.

    Skips test_auth.py since it specifically tests authentication failures.
    Use the api_client fixture directly if you need an authenticated client
    without this auto-injection.
    """
    if "test_auth.py" in str(request.fspath):
        yield
        return
    if hasattr(request.cls, "setup_method"):
        original_setup = request.cls.setup_method

        def new_setup(self, *args, **kwargs):
            original_setup(self, *args, **kwargs)
            if hasattr(self, "client") and isinstance(self.client, APIClient):
                token = AuthFactory().token
                self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        request.cls.setup_method = new_setup
        yield
        request.cls.setup_method = original_setup
    else:
        yield
