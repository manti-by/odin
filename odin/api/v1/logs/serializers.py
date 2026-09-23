from rest_framework import serializers


class LogSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    msg = serializers.CharField(max_length=100)
    filename = serializers.CharField(max_length=100)
    levelname = serializers.CharField(max_length=100)
    asctime = serializers.DateTimeField()
    stacktrace = serializers.JSONField(allow_null=True, required=False)
    variables = serializers.JSONField(allow_null=True, required=False)


class ErrorLogSerializer(serializers.Serializer):
    asctime = serializers.DateTimeField()
    msg = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=100)
    levelname = serializers.CharField(max_length=100)
    filename = serializers.CharField(max_length=100)
