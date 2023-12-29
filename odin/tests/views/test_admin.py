import pytest
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.urls import reverse
from rest_framework import status

from odin.apps.sensors.models import Sensor
from odin.tests.factories import DjangoAdminUserFactory, SensorFactory


@pytest.mark.django_db
class TestSensorAdmin:
    def setup_method(self):
        self.user = DjangoAdminUserFactory()
        self.sensor = SensorFactory()

    def test_sensor_changelist(self, client):
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Sensor._meta, "changelist")), follow=True)
        assert response.status_code == status.HTTP_200_OK

    def test_sensor_change(self, client):
        client.force_login(self.user)
        response = client.get(reverse(admin_urlname(Sensor._meta, "change"), args=[self.sensor.id]), follow=True)
        assert response.status_code == status.HTTP_200_OK
