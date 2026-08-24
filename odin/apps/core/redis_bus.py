from __future__ import annotations

import json
import logging
import threading
from enum import Enum
from typing import Any, cast

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
    """Shared Redis client and helpers for publishing and reading bus messages.

    Provides lazy singleton Redis client creation and convenience methods
    for publishing messages to streams and reading relay state. Publish
    methods return False on Redis or serialization failures instead of
    raising, while read methods raise RedisReadError on failures.
    """

    _client: redis.Redis | None = None
    _lock = threading.Lock()

    @classmethod
    def get_redis(cls) -> redis.Redis:
        """Return the shared Redis client, creating it lazily.

        Uses bounded socket timeouts from settings to avoid blocking
        workers indefinitely when Redis is unavailable.

        Returns:
            redis.Redis: The shared Redis client instance.
        """
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cls._client = redis.Redis.from_url(
                        settings.REDIS_URL,
                        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    )
        return cls._client

    @classmethod
    def publish_message(cls, stream: str, payload: dict[str, Any]) -> bool:
        """Publish a JSON payload to a Redis stream.

        Args:
            stream: Name of the Redis stream to publish to.
            payload: JSON-serializable dictionary to publish.

        Returns:
            True if the message was published, False if Redis or
            serialization failed.
        """
        try:
            client = cls.get_redis()
        except (RedisError, ValueError) as e:
            logger.error(f"Redis error: {e}")
            return False

        try:
            data = json.dumps(payload).encode("utf-8")
            message_id = client.xadd(stream, {"data": data}, maxlen=10000, approximate=True)

            logger.info(f"Published message {message_id} to stream {stream}")
            return True

        except RedisError as e:
            logger.error(f"Redis error: {e}")
        except (TypeError, ValueError) as e:
            logger.error(f"Payload serialization error: {e}")

        return False

    @classmethod
    def publish_relay_control(cls, relay_id: str, target_state: str) -> bool:
        """Publish a relay control command to the relays stream.

        Args:
            relay_id: Identifier of the relay to control.
            target_state: Desired relay state value.

        Returns:
            True if the control message was published, False otherwise.
        """
        message = {"relay_id": relay_id, "target_state": target_state}
        return cls.publish_message(settings.REDIS_RELAYS_CHANNEL, payload=message)

    @classmethod
    def get_relay_state(cls, relay_id: str) -> dict[str, Any] | None:
        """Fetch and decode relay state from Redis.

        Args:
            relay_id: Identifier of the relay whose state is requested.

        Returns:
            Decoded state dictionary if present, None if no state is stored.

        Raises:
            RedisReadError: If Redis is unavailable, the payload is not
                valid JSON, or the decoded value is not a dictionary.
        """
        key = f"{settings.REDIS_RELAY_STATE_KEY_PREFIX}{relay_id}"
        try:
            raw = cast(bytes | None, cls.get_redis().get(key))
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
