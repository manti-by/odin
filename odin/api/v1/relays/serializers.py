import re

from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.relays.models import Relay, RelayType
from odin.apps.relays.services import RelayTargetStateService


MAX_SCHEDULE_PERIODS = 5

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
TIME_ERROR = "Time must be in HH:MM format"


def _time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _time_ranges(start: str, end: str) -> list[tuple[int, int]]:
    """Split a period into one or two half-open minute ranges, handling overnight spans."""
    start_minutes = _time_to_minutes(start)
    end_minutes = _time_to_minutes(end)

    if start_minutes < end_minutes:
        return [(start_minutes, end_minutes)]
    if start_minutes > end_minutes:
        return [(start_minutes, 24 * 60), (0, end_minutes)]
    return []


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField()
    mode = serializers.CharField()
    context = serializers.JSONField()
    target_state = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_target_state(self, obj: Relay) -> str:
        state, _ = RelayTargetStateService(obj).get_target_state()
        return str(state)


class RelayPeriodSerializer(BaseSerializer):
    start_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    end_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    target_temp = serializers.FloatField(required=False, allow_null=True)
    target_state = serializers.ChoiceField(choices=("ON", "OFF"), required=False, allow_null=True)


class RelayScheduleSerializer(BaseSerializer):
    periods = serializers.ListField(child=RelayPeriodSerializer(), max_length=MAX_SCHEDULE_PERIODS, required=False)

    def validate_periods(self, periods: list[dict]) -> list[dict]:
        for period in periods:
            if period["start_time"] == period["end_time"]:
                raise serializers.ValidationError("Schedule period start and end times must differ")

        ranges = [range_ for period in periods for range_ in _time_ranges(period["start_time"], period["end_time"])]
        for index, (start_a, end_a) in enumerate(ranges):
            for start_b, end_b in ranges[index + 1 :]:
                if start_a < end_b and start_b < end_a:
                    raise serializers.ValidationError("Schedule periods must not overlap")
        return periods


class RelayUpdateContextSerializer(BaseSerializer):
    schedule = RelayScheduleSerializer(required=False)


class RelayUpdateSerializer(BaseSerializer):
    context = RelayUpdateContextSerializer(required=False)
    force_state = serializers.ChoiceField(choices=("ON", "OFF"), required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        schedule = attrs.get("context", {}).get("schedule")
        if schedule is not None and (relay := self.instance):
            periods = schedule.get("periods") or []
            if relay.type == RelayType.VALVE and periods:
                raise serializers.ValidationError({"context": "Schedule is not supported for VALVE relays"})
            for period in periods:
                if relay.type == RelayType.SERVO and period.get("target_temp") is None:
                    raise serializers.ValidationError({"context": "SERVO schedule periods require target_temp"})
                if relay.type == RelayType.PUMP and period.get("target_state") is None:
                    raise serializers.ValidationError({"context": "PUMP schedule periods require target_state"})
        return attrs

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data
