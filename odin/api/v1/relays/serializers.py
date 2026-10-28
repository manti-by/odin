from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from odin.api.utils.serializers import BaseSerializer
from odin.apps.relays.models import Relay, RelayType
from odin.apps.relays.services import MAX_SCHEDULE_PERIODS, TIME_ERROR, TIME_PATTERN, validate_schedule_periods


class RelaySerializer(BaseSerializer):
    relay_id = serializers.CharField()
    name = serializers.CharField()
    type = serializers.CharField()
    state = serializers.CharField()
    context = serializers.JSONField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance: Relay) -> dict:
        data = super().to_representation(instance)
        state, mode = instance.get_target_state()
        data["mode"] = str(mode)
        data["target_state"] = str(state)
        return data


class RelayPeriodSerializer(BaseSerializer):
    start_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    end_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    target_temp = serializers.FloatField(required=False, allow_null=True)
    target_state = serializers.ChoiceField(choices=("ON", "OFF"), required=False, allow_null=True)


def _validate_schedule_periods(periods: list[dict]) -> list[dict]:
    try:
        return validate_schedule_periods(periods)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages[0]) from exc


class RelayScheduleSerializer(BaseSerializer):
    periods = serializers.ListField(child=RelayPeriodSerializer(), max_length=MAX_SCHEDULE_PERIODS, required=False)

    def validate_periods(self, periods: list[dict]) -> list[dict]:
        return _validate_schedule_periods(periods)


class RelayOverridePeriodSerializer(BaseSerializer):
    start_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    end_time = serializers.RegexField(TIME_PATTERN, error_messages={"invalid": TIME_ERROR})
    target_state = serializers.ChoiceField(choices=("ON", "OFF"))


class RelayOverrideScheduleSerializer(BaseSerializer):
    periods = serializers.ListField(
        child=RelayOverridePeriodSerializer(), max_length=MAX_SCHEDULE_PERIODS, required=False
    )

    def validate_periods(self, periods: list[dict]) -> list[dict]:
        return _validate_schedule_periods(periods)


class RelayUpdateContextSerializer(BaseSerializer):
    schedule = RelayScheduleSerializer(required=False)
    override_schedule = RelayOverrideScheduleSerializer(required=False)


class RelayUpdateSerializer(BaseSerializer):
    context = RelayUpdateContextSerializer(required=False)
    force_state = serializers.ChoiceField(choices=("ON", "OFF"), required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        context = attrs.get("context", {})
        if (schedule := context.get("schedule")) is not None and (relay := self.instance):
            periods = schedule.get("periods") or []
            if relay.type == RelayType.VALVE and periods:
                raise serializers.ValidationError({"context": "Schedule is not supported for VALVE relays"})
            for period in periods:
                if relay.type == RelayType.SERVO and period.get("target_temp") is None:
                    raise serializers.ValidationError({"context": "SERVO schedule periods require target_temp"})
                if relay.type == RelayType.PUMP and period.get("target_state") is None:
                    raise serializers.ValidationError({"context": "PUMP schedule periods require target_state"})

        if (override := context.get("override_schedule")) is not None:
            for period in override.get("periods") or []:
                if period.get("target_state") is None:
                    raise serializers.ValidationError({"context": "Override schedule periods require target_state"})
        return attrs

    @property
    def data(self) -> dict:
        """Ad-hoc solution to prevent response rendering errors."""
        return self.validated_data
