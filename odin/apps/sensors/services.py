from collections import defaultdict
from datetime import datetime, timedelta

from django.db.models import QuerySet
from django.utils import timezone

from odin.apps.sensors.models import SensorLog


def round_to_5_minutes(dt: datetime) -> datetime:
    minutes = dt.minute
    rounded_minutes = (minutes // 5) * 5
    return dt.replace(minute=rounded_minutes, second=0, microsecond=0)


def parse_timestamp_data(sensors: QuerySet, sensor_logs: QuerySet) -> dict[str, dict]:
    timestamp_data = defaultdict(dict)
    sensor_offset_map = {s.sensor_id: s.temp_offset for s in sensors}

    for sensor_log in sensor_logs:
        log_time = sensor_log.created_at if sensor_log.created_at else sensor_log.synced_at
        rounded_minutes = (log_time.minute // 5) * 5
        timestamp_key = log_time.replace(minute=rounded_minutes, second=0, microsecond=0).isoformat()

        if (
            sensor_log.sensor_id not in timestamp_data[timestamp_key]
            or log_time > timestamp_data[timestamp_key][sensor_log.sensor_id][0]
        ):
            temp_offset = sensor_offset_map.get(sensor_log.sensor_id, 0)
            timestamp_data[timestamp_key][sensor_log.sensor_id] = (log_time, float(sensor_log.temp + temp_offset))

    return timestamp_data


def get_chart_data(sensors: QuerySet, start: datetime | None = None, end: datetime | None = None) -> dict:
    end_dt = end or timezone.now()
    start_dt = start or (end_dt - timedelta(hours=48))

    sensor_ids = sensors.order_by("sensor_id").values_list("sensor_id", flat=True)
    if not sensor_ids:
        return {"timestamps": [], "sensors": []}

    sensor_logs = SensorLog.objects.filter(
        sensor_id__in=sensor_ids,
        created_at__range=(start_dt, end_dt),
    ).order_by("created_at")

    timestamp_data = parse_timestamp_data(sensors=sensors, sensor_logs=sensor_logs)
    sorted_timestamps = sorted(timestamp_data.keys())

    sensor_data_list = []
    sensor_map = {s.sensor_id: s.name for s in sensors}
    for sensor_id in sensor_ids:
        sensor_name = sensor_map.get(sensor_id, sensor_id)

        data = []
        for timestamp_key in sorted_timestamps:
            sensor_entry = timestamp_data[timestamp_key].get(sensor_id)
            temp_value = sensor_entry[1] if sensor_entry else None
            data.append(temp_value)

        sensor_data_list.append({"sensor_id": sensor_id, "name": sensor_name, "data": data})

    return {"timestamps": sorted_timestamps, "sensors": sensor_data_list}
