import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from django.conf import settings

from odin.apps.core.exceptions import RedisReadError
from odin.apps.core.redis_bus import RedisBus


class TestRedisBus:
    def setup_method(self) -> None:
        RedisBus._client = None

    @patch("odin.apps.core.redis_bus.redis.Redis")
    def test_get_redis_singleton(self, mock_redis_class: MagicMock) -> None:
        """Test that get_redis returns the same instance."""
        client1 = RedisBus.get_redis()
        client2 = RedisBus.get_redis()

        assert client1 is client2
        assert mock_redis_class.from_url.call_count == 1

    @patch("odin.apps.core.redis_bus.redis.Redis")
    def test_get_redis_initializes_from_url(self, mock_redis_class: MagicMock) -> None:
        """Test that redis client is initialized from REDIS_URL."""
        RedisBus.get_redis()

        mock_redis_class.from_url.assert_called_once()
        call_args = mock_redis_class.from_url.call_args
        assert call_args.args[0] == settings.REDIS_URL

    def test_get_redis_is_thread_safe(self):
        """Test that concurrent get_redis calls create a single client."""
        created = []
        entered = threading.Event()
        release = threading.Event()
        barrier = threading.Barrier(2)

        def from_url(*args, **kwargs):
            created.append(object())
            entered.set()
            release.wait(5)
            return object()

        def call_get_redis():
            barrier.wait(5)
            return RedisBus.get_redis()

        with patch("odin.apps.core.redis_bus.redis.Redis.from_url", side_effect=from_url):
            with ThreadPoolExecutor(max_workers=2) as executor:
                future1 = executor.submit(call_get_redis)
                future2 = executor.submit(call_get_redis)
                assert entered.wait(5)
                # Let the second thread pass the `_client is None` check while the
                # first thread is still blocked inside from_url.
                time.sleep(0.1)
                release.set()
                clients = [future1.result(timeout=5), future2.result(timeout=5)]

        assert len(created) == 1
        assert clients[0] is clients[1]

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_publish_message_success(self, mock_get_redis):
        """Test successful message publishing."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        assert RedisBus.publish_message("test_channel", {"key": "value"})
        mock_client.publish.assert_called_once()

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_publish_message_redis_error(self, mock_get_redis):
        """Test that RedisError is handled on failure."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.publish.side_effect = RedisError("Connection failed")

        assert not RedisBus.publish_message("test_channel", {"key": "value"})

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_publish_message_serialization_error(self, mock_get_redis):
        """Test that non-serializable payload returns False."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        assert not RedisBus.publish_message("test_channel", {"key": object()})
        mock_client.publish.assert_not_called()

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_publish_message_circular_reference_error(self, mock_get_redis):
        """Test that circular reference payload returns False."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        payload = {}
        payload["self"] = payload

        assert not RedisBus.publish_message("test_channel", payload)
        mock_client.publish.assert_not_called()

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_publish_message_initialization_error(self, mock_get_redis):
        """Test that client initialization failure returns False."""
        mock_get_redis.side_effect = ValueError("Invalid REDIS_URL")

        assert not RedisBus.publish_message("test_channel", {"key": "value"})

    @patch("odin.apps.core.redis_bus.RedisBus.publish_message")
    def test_publish_relay_control(self, mock_publish_message):
        """Test publish_relay_control formats the canonical envelope correctly."""
        RedisBus.publish_relay_control(relay_id="relay_1", state="ON")
        assert mock_publish_message.call_count == 1
        assert mock_publish_message.call_args.args[0] == settings.REDIS_RELAYS_CHANNEL
        payload = mock_publish_message.call_args.kwargs["payload"]
        assert payload["type"] == "RELAY_STATE_UPDATE"
        assert payload["data"] == {"relay_id": "relay_1", "state": "ON"}
        assert "timestamp" in payload

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_returns_data(self, mock_get_redis):
        """Test that get_relay_state returns data when found."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.get.return_value = b'{"relay_id": "relay_1", "state": "ON"}'

        result = RedisBus.get_relay_state("relay_1")
        assert result == {"relay_id": "relay_1", "state": "ON"}

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_returns_none_when_not_found(self, mock_get_redis):
        """Test that get_relay_state returns None when relay not found."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.get.return_value = None

        assert RedisBus.get_relay_state("relay_1") is None

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_raises_redis_error(self, mock_get_redis):
        """Test that get_relay_state raises RedisReadError on failure."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.get.side_effect = RedisError("Connection failed")

        with pytest.raises(RedisReadError):
            RedisBus.get_relay_state("relay_1")

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_raises_redis_error_on_initialization(self, mock_get_redis):
        """Test that get_relay_state raises RedisReadError when client init fails."""
        mock_get_redis.side_effect = ValueError("Invalid REDIS_URL")

        with pytest.raises(RedisReadError):
            RedisBus.get_relay_state("relay_1")

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_raises_redis_error_on_invalid_json(self, mock_get_redis):
        """Test that get_relay_state raises RedisReadError on malformed JSON."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.get.return_value = b"{invalid json"

        with pytest.raises(RedisReadError):
            RedisBus.get_relay_state("relay_1")

    @patch("odin.apps.core.redis_bus.RedisBus.get_redis")
    def test_get_relay_state_raises_redis_error_on_non_dict_payload(self, mock_get_redis):
        """Test that get_relay_state raises RedisReadError on non-dict payload."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client
        mock_client.get.return_value = b'"ON"'

        with pytest.raises(RedisReadError):
            RedisBus.get_relay_state("relay_1")
