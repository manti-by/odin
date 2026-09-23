from rest_framework import serializers


class ExchangeRateSerializer(serializers.Serializer):
    currency = serializers.CharField(max_length=3)
    rate = serializers.DecimalField(max_digits=10, decimal_places=4)
    rate_per_unit = serializers.DecimalField(max_digits=10, decimal_places=4)
    scale = serializers.IntegerField()
    date = serializers.DateField()


class ExchangeRatesSerializer(serializers.Serializer):
    rates = ExchangeRateSerializer(many=True)
    trends = serializers.JSONField()
