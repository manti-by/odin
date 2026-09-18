from rest_framework import serializers

from odin.apps.boiler.services import BoilerMode


class BoilerStatusSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=BoilerMode.choices, allow_null=True)
    target_temp = serializers.IntegerField(allow_null=True)
    hwc_temp = serializers.IntegerField(allow_null=True)
    override_active = serializers.BooleanField()
    override_updated_at = serializers.DateTimeField(allow_null=True)
    ebusd_alive = serializers.BooleanField()
    next_boil_at = serializers.DateTimeField()
    next_clear_at = serializers.DateTimeField()
