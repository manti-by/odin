from datetime import datetime, timedelta

from django.utils import timezone

from odin.apps.sensors.models import Sensor, SensorLog


def get_temp_sensors_chart_data(start: datetime | None = None, end: datetime | None = None) -> dict:
    now = end or timezone.now()
    start_dt = start or (now - timedelta(hours=48))

    # Get all active DS18B20 sensors
    sensors = Sensor.objects.active().ds18b20().order_by("sensor_id")
    sensor_ids = list(sensors.values_list("sensor_id", flat=True))

    if not sensor_ids:
        return {"timestamps": [], "sensors": []}

    logs = SensorLog.objects.filter(sensor_id__in=sensor_ids, created_at__range=(start_dt, now)).order_by("created_at")

    # Create a mapping of sensor_id to sensor name
    sensor_map = {s.sensor_id: s.name for s in sensors}

    # Group logs by timestamp (rounded to nearest 5 minutes for better visualization)
    timestamp_data = {}

    for log in logs:
        # Use created_at if available, otherwise synced_at
        log_time = log.created_at if log.created_at else log.synced_at

        # Round to nearest 5 minutes
        minutes = log_time.minute
        rounded_minutes = (minutes // 5) * 5
        rounded_time = log_time.replace(minute=rounded_minutes, second=0, microsecond=0)

        timestamp_key = rounded_time.isoformat()

        if timestamp_key not in timestamp_data:
            timestamp_data[timestamp_key] = {}

        # Store the temperature value for this sensor at this timestamp
        # If multiple logs exist for the same rounded timestamp, keep the one with the latest actual time
        if (
            log.sensor_id not in timestamp_data[timestamp_key]
            or log_time > timestamp_data[timestamp_key][log.sensor_id][0]
        ):
            timestamp_data[timestamp_key][log.sensor_id] = (log_time, float(log.temp))

    # Get sorted unique timestamps
    sorted_timestamps = sorted(timestamp_data.keys())

    # Build sensor data arrays
    sensor_data_list = []
    for sensor_id in sensor_ids:
        sensor_name = sensor_map.get(sensor_id, sensor_id)
        data = []

        for timestamp_key in sorted_timestamps:
            # Get temperature value for this sensor at this timestamp, or None if missing
            sensor_entry = timestamp_data[timestamp_key].get(sensor_id)
            temp_value = sensor_entry[1] if sensor_entry else None
            data.append(temp_value)

        sensor_data_list.append({"sensor_id": sensor_id, "name": sensor_name, "data": data})

    return {"timestamps": sorted_timestamps, "sensors": sensor_data_list}
