from unittest.mock import MagicMock, patch

import pytest

from odin.apps.core.kafka import KafkaService


class TestKafkaService:
    def test_get_producer_singleton(self):
        """Test that get_producer returns the same instance."""
        with patch("odin.apps.core.kafka.KafkaProducer") as mock_producer_class:
            producer1 = KafkaService.get_producer()
            producer2 = KafkaService.get_producer()

            assert producer1 is producer2
            assert mock_producer_class.call_count == 1

    def test_get_producer_initializes_correctly(self):
        """Test that producer is initialized with correct settings."""
        with patch("odin.apps.core.kafka.KafkaProducer") as mock_producer_class:
            KafkaService._producer = None
            KafkaService.get_producer()

            mock_producer_class.assert_called_once()
            call_kwargs = mock_producer_class.call_args.kwargs
            assert "bootstrap_servers" in call_kwargs
            assert "value_serializer" in call_kwargs
            assert call_kwargs["acks"] == "all"
            assert call_kwargs["retries"] == 3

    @patch("odin.apps.core.kafka.KafkaService.get_producer")
    def test_send_message_success(self, mock_get_producer):
        """Test successful message sending."""
        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_get_producer.return_value = mock_producer
        mock_producer.send.return_value = mock_future

        KafkaService.send_message("test_topic", {"key": "value"})

        mock_producer.send.assert_called_once_with("test_topic", value={"key": "value"})
        mock_future.get.assert_called_once_with(timeout=10)

    @patch("odin.apps.core.kafka.KafkaService.get_producer")
    def test_send_message_kafka_error(self, mock_get_producer):
        """Test that KafkaError is raised on failure."""
        from kafka.errors import KafkaError

        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_get_producer.return_value = mock_producer
        mock_producer.send.return_value = mock_future
        mock_future.get.side_effect = KafkaError("Connection failed")

        with pytest.raises(KafkaError):
            KafkaService.send_message("test_topic", {"key": "value"})

    @patch("odin.apps.core.kafka.KafkaService.send_message")
    def test_send_relay_update(self, mock_send_message):
        """Test send_relay_update formats message correctly."""
        KafkaService.send_relay_update(relay_id="relay_1", target_state="ON")

        mock_send_message.assert_called_once()
        args, _ = mock_send_message.call_args
        assert args[0] == "coruscant"
        assert args[1] == {"relay_id": "relay_1", "target_state": "ON"}

    @patch("odin.apps.core.kafka.KafkaService.send_message")
    def test_send_relay_update_converts_target_state_to_str(self, mock_send_message):
        """Test that target_state is converted to string."""
        KafkaService.send_relay_update(relay_id="relay_2", target_state="OFF")

        mock_send_message.assert_called_once()
        args, _ = mock_send_message.call_args
        assert args[1]["target_state"] == "OFF"
