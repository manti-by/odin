from __future__ import annotations

import json
import logging
import threading
from enum import Enum
from typing import Any

import redis
from redis.exceptions import RedisError

from django.conf import settings

from odin.apps.core.exceptions import RedisReadError


logger = logging.getLogger(__name__)


class PartitionKey(Enum):
    SENSORS = "sensors"
    RELAYS = "relays"


class MessageType(Enum):
    RELAY_STATE_UPDATE = "RELAY_STATE_UPDATE"
    SENSOR_DATA_UPDATE = "SENSOR_DATA_UPDATE"


class RedisBus:
    _client: redis.Redis | None = None
    _lock = threading.Lock()

    @classmethod
    def get_redis(cls) -> redis.Redis:
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cls._client = redis.Redis.from_url(settings.REDIS_URL)
        return cls._client

    @classmethod
    def publish_message(cls, channel: str, payload: dict[str, Any]) -> bool:
        try:
            client = cls.get_redis()
        except (RedisError, ValueError) as e:
            logger.error(f"Redis error: {e}")
            return False

        try:
            data = json.dumps(payload).encode("utf-8")
            count = client.publish(channel, data)

            logger.info(f"Published message to channel {channel} (subscribers: {count})")
            return True

        except RedisError as e:
            logger.error(f"Redis error: {e}")
        except (TypeError, ValueError) as e:
            logger.error(f"Payload serialization error: {e}")

        return False

    @classmethod
    def publish_relay_control(cls, relay_id: str, target_state: str) -> bool:
        message = {"relay_id": relay_id, "target_state": target_state}
        return cls.publish_message(settings.REDIS_RELAYS_CHANNEL, payload=message)

    @classmethod
    def get_relay_state(cls, relay_id: str) -> dict[str, Any] | None:
        key = f"{settings.REDIS_RELAY_STATE_KEY_PREFIX}{relay_id}"
        try:
            raw = cls.get_redis().get(key)
        except (RedisError, ValueError) as e:
            raise RedisReadError from e

        if raw is None:
            return None

        try:
            state = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise RedisReadError from e

        if not isinstance(state, dict):
            raise RedisReadError

        return state
