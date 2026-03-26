from unittest.mock import MagicMock, patch

import pytest
from kafka.structs import TopicPartition

from odin.apps.core.exceptions import KafkaReadError
from odin.apps.core.kafka import KafkaService, MessageType


class TestKafkaService:
    @patch("odin.apps.core.kafka.KafkaProducer")
    def test_get_producer_singleton(self, mock_producer_class):
        """Test that get_producer returns the same instance."""
        producer1 = KafkaService.get_producer()
        producer2 = KafkaService.get_producer()

        assert producer1 is producer2
        assert mock_producer_class.call_count == 1

    @patch("odin.apps.core.kafka.KafkaProducer")
    def test_get_producer_initializes_correctly(self, mock_producer_class):
        """Test that producer is initialized with correct settings."""
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

        assert mock_producer.send.call_count == 1
        assert mock_future.get.call_count == 1

    @patch("odin.apps.core.kafka.KafkaService.get_producer")
    def test_send_message_kafka_error(self, mock_get_producer):
        """Test that KafkaError is raised on failure."""
        from kafka.errors import KafkaError

        mock_producer = MagicMock()
        mock_future = MagicMock()
        mock_get_producer.return_value = mock_producer
        mock_producer.send.return_value = mock_future
        mock_future.get.side_effect = KafkaError("Connection failed")

        assert not KafkaService.send_message("test_topic", {"key": "value"})

    @patch("odin.apps.core.kafka.KafkaService.send_message")
    def test_send_relay_update(self, mock_send_message):
        """Test send_relay_update formats message correctly."""
        KafkaService.send_relay_update(relay_id="relay_1", target_state="ON")
        assert mock_send_message.call_count == 1

    @patch("odin.apps.core.kafka.KafkaService.get_consumer")
    def test_get_relay_data_returns_data(self, mock_get_consumer):
        """Test that get_relay_data returns data when found."""
        mock_consumer = MagicMock()
        mock_get_consumer.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = {0}
        mock_consumer.end_offsets.return_value = {TopicPartition("odin", 0): 1}

        mock_message = MagicMock()
        mock_message.value = {
            "type": MessageType.RELAY_STATE_UPDATE.value,
            "data": {"relay_id": "relay_1", "state": "ON"},
        }
        mock_consumer.poll.return_value = {TopicPartition("odin", 0): [mock_message]}

        result = KafkaService.get_relay_data("relay_1")
        assert result == {"relay_id": "relay_1", "state": "ON"}
        mock_consumer.close.assert_called_once()

    @patch("odin.apps.core.kafka.KafkaService.get_consumer")
    def test_get_relay_data_returns_none_when_not_found(self, mock_get_consumer):
        """Test that get_relay_data returns None when relay not found."""
        mock_consumer = MagicMock()
        mock_get_consumer.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = {0}
        mock_consumer.end_offsets.return_value = {TopicPartition("odin", 0): 1}

        mock_message = MagicMock()
        mock_message.value = {
            "type": MessageType.RELAY_STATE_UPDATE.value,
            "data": {"relay_id": "relay_other", "state": "OFF"},
        }
        mock_consumer.poll.return_value = {TopicPartition("odin", 0): [mock_message]}

        assert KafkaService.get_relay_data("relay_1") is None
        mock_consumer.close.assert_called_once()

    @patch("odin.apps.core.kafka.KafkaService.get_consumer")
    def test_get_relay_data_ignores_wrong_message_type(self, mock_get_consumer):
        """Test that get_relay_data ignores messages with wrong type."""
        mock_consumer = MagicMock()
        mock_get_consumer.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = {0}
        mock_consumer.end_offsets.return_value = {TopicPartition("odin", 0): 1}

        mock_message = MagicMock()
        mock_message.value = {
            "type": MessageType.SENSOR_DATA_UPDATE.value,
            "data": {"relay_id": "relay_1", "state": "ON"},
        }
        mock_consumer.poll.return_value = {TopicPartition("odin", 0): [mock_message]}

        assert KafkaService.get_relay_data("relay_1") is None
        mock_consumer.close.assert_called_once()

    @patch("odin.apps.core.kafka.KafkaService.get_consumer")
    def test_get_relay_data_raises_kafka_error(self, mock_get_consumer):
        """Test that get_relay_data raises KafkaReadError on failure and closes consumer."""
        from kafka.errors import KafkaError

        mock_consumer = MagicMock()
        mock_get_consumer.return_value = mock_consumer
        mock_consumer.partitions_for_topic.side_effect = KafkaError("Connection failed")

        with pytest.raises(KafkaReadError):
            KafkaService.get_relay_data("relay_1")
        mock_consumer.close.assert_called_once()
