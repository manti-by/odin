import pytest

from odin.apps.core.models import Device
from odin.tests.factories import DeviceFactory


@pytest.mark.django_db
class TestDeviceModel:
    def setup_method(self):
        self.device = DeviceFactory()

    def test_device_is_admin_default_false(self):
        device = DeviceFactory(is_admin=False)
        assert device.is_admin is False

    def test_device_is_admin_can_be_set_true(self):
        device = DeviceFactory(is_admin=True)
        assert device.is_admin is True

    def test_device_str_representation(self):
        assert str(self.device) == f"Device ({self.device.browser})"

    def test_device_default_is_active_true(self):
        device = DeviceFactory()
        assert device.is_active is True

    def test_device_manager_active_returns_only_active(self):
        Device.objects.all().delete()
        DeviceFactory(is_active=True)
        DeviceFactory(is_active=True)
        DeviceFactory(is_active=False)

        active_devices = Device.objects.active()
        assert active_devices.count() == 2

    def test_device_filter_by_is_admin(self):
        DeviceFactory(is_admin=True)
        DeviceFactory(is_admin=True)
        DeviceFactory(is_admin=False)

        admin_devices = Device.objects.filter(is_admin=True)
        assert admin_devices.count() == 2
