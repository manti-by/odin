from rest_framework import serializers

from odin.apps.cinema.models import FetchStatus


class VideoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    filename = serializers.CharField()
    year = serializers.IntegerField(allow_null=True)
    imdb_rating = serializers.DecimalField(max_digits=3, decimal_places=1, allow_null=True)
    description = serializers.CharField()
    genres = serializers.ListField(child=serializers.CharField())
    trailer_available = serializers.BooleanField(source="has_trailer")
    metadata_status = serializers.ChoiceField(choices=FetchStatus.choices)
    trailer_status = serializers.ChoiceField(choices=FetchStatus.choices)
    is_available = serializers.BooleanField()
    created_at = serializers.DateTimeField()
