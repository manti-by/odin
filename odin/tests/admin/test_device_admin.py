import pytest

from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.urls import reverse
from rest_framework import status

from odin.apps.core.models import Device
from odin.tests.factories import DeviceFactory, DjangoAdminUserFactory


@pytest.mark.django_db
@pytest.mark.views
class TestDeviceAdmin:
    def setup_method(self):
        self.user = DjangoAdminUserFactory()
        self.device = DeviceFactory()

    def test_device_changelist(self, client):
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Device._meta, "changelist")), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_device_change(self, client):
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Device._meta, "change"), args=[self.device.id]), follow=True)
        assert response.status_code == status.HTTP_200_OK
