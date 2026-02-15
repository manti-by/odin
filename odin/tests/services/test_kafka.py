from unittest.mock import MagicMock, patch

import pytest

from odin.apps.core.kafka import KafkaService


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

    @patch("odin.apps.core.kafka.KafkaConsumer")
    def test_get_relay_state_from_kafka_returns_state(self, mock_consumer_class):
        """Test that get_relay_state_from_kafka returns state when found."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = {0}

        mock_message = MagicMock()
        mock_message.value = {"relay_id": "relay_1", "state": "ON"}
        mock_consumer.poll.return_value = {MagicMock(): [mock_message]}

        state = KafkaService.get_relay_state_from_kafka("relay_1")

        assert state == "ON"
        mock_consumer.close.assert_called_once()

    @patch("odin.apps.core.kafka.KafkaConsumer")
    def test_get_relay_state_from_kafka_returns_none_when_not_found(self, mock_consumer_class):
        """Test that get_relay_state_from_kafka returns None when relay not found."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = {0}

        mock_message = MagicMock()
        mock_message.value = {"relay_id": "relay_other", "state": "OFF"}
        mock_consumer.poll.return_value = {MagicMock(): [mock_message]}

        state = KafkaService.get_relay_state_from_kafka("relay_1")

        assert state is None

    @patch("odin.apps.core.kafka.KafkaConsumer")
    def test_get_relay_state_from_kafka_raises_kafka_error(self, mock_consumer_class):
        """Test that get_relay_state_from_kafka raises KafkaError on failure."""
        from kafka.errors import KafkaError

        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_consumer.partitions_for_topic.side_effect = KafkaError("Connection failed")

        with pytest.raises(KafkaError):
            KafkaService.get_relay_state_from_kafka("relay_1")

    @patch("odin.apps.core.kafka.KafkaConsumer")
    def test_get_relay_state_from_kafka_returns_none_when_no_partitions(self, mock_consumer_class):
        """Test that get_relay_state_from_kafka returns None when no partitions."""
        mock_consumer = MagicMock()
        mock_consumer_class.return_value = mock_consumer
        mock_consumer.partitions_for_topic.return_value = None

        state = KafkaService.get_relay_state_from_kafka("relay_1")

        assert state is None
        mock_consumer.close.assert_called_once()
