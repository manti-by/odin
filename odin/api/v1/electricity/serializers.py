from rest_framework import serializers


class VoltageSerializer(serializers.Serializer):
    voltage = serializers.DecimalField(max_digits=7, decimal_places=2)
    created_at = serializers.DateTimeField()
