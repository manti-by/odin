from rest_framework import serializers


class TrafficSerializer(serializers.Serializer):
    value = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField(max_length=16)
    created_at = serializers.DateTimeField()
