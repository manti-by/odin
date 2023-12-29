from django.test.client import Client

import pytest


@pytest.fixture
def client():
    client = Client(HTTP_HOST="odin.local")
    return client
