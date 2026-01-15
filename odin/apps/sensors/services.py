from datetime import datetime, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from odin.apps.sensors.models import SensorLog


def _round_to_5_minutes(dt: datetime) -> datetime:
    minutes = dt.minute
    rounded_minutes = (minutes // 5) * 5
    return dt.replace(minute=rounded_minutes, second=0, microsecond=0)


def _parse_timestamp_data(logs: QuerySet, timestamp_data: dict[str, dict[str, tuple[datetime, float]]]) -> None:
    for log in logs:
        log_time = log.created_at if log.created_at else log.synced_at
        rounded_time = _round_to_5_minutes(log_time)
        timestamp_key = rounded_time.isoformat()

        if timestamp_key not in timestamp_data:
            timestamp_data[timestamp_key] = {}

        if (
            log.sensor_id not in timestamp_data[timestamp_key]
            or log_time > timestamp_data[timestamp_key][log.sensor_id][0]
        ):
            timestamp_data[timestamp_key][log.sensor_id] = (log_time, float(log.temp))


def get_chart_data(
    sensors: QuerySet,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict:
    now = end or timezone.now()
    start_dt = start or (now - timedelta(hours=48))

    sensors = sensors.order_by("sensor_id")
    sensor_ids = list(sensors.values_list("sensor_id", flat=True))

    if not sensor_ids:
        return {"timestamps": [], "sensors": []}

    logs = SensorLog.objects.filter(sensor_id__in=sensor_ids, created_at__range=(start_dt, now)).order_by("created_at")

    sensor_map = {s.sensor_id: s.name for s in sensors}

    timestamp_data: dict[str, dict[str, tuple[datetime, float]]] = {}

    _parse_timestamp_data(logs, timestamp_data)

    sorted_timestamps = sorted(timestamp_data.keys())

    sensor_data_list = []
    for sensor_id in sensor_ids:
        sensor_name = sensor_map.get(sensor_id, sensor_id)
        data = []

        for timestamp_key in sorted_timestamps:
            sensor_entry = timestamp_data[timestamp_key].get(sensor_id)
            temp_value = sensor_entry[1] if sensor_entry else None
            data.append(temp_value)

        sensor_data_list.append({"sensor_id": sensor_id, "name": sensor_name, "data": data})

    return {"timestamps": sorted_timestamps, "sensors": sensor_data_list}
