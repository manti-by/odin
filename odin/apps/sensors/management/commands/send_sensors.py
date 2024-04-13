import logging
import os

import requests
from concurrent import futures
from command_log.management.commands import LoggedCommand
from django.conf import settings
from django.utils import timezone

from odin.apps.core.services import get_data_hash
from odin.apps.sensors.models import Sensor, SyncLog

logger = logging.getLogger(__name__)


class Command(LoggedCommand):
    help = description = "Upload the data to Amon-Ra server."
    threads_count = os.cpu_count() * 2

    @staticmethod
    def send_request(data_list: list[dict], thread_index: int):
        url = "https://amon-ra.manti.by/api/v1/sensors/create/"
        sensors_sent = []
        for index, data in enumerate(data_list):
            response = requests.post(url, json=data, timeout=30)
            if response.ok:
                sensors_sent.append(data["external_id"])
            else:
                logger.error(f"Error while sending data to Amon-Ra server: {response.text}")
            if index and index % 500 == 0:
                logger.info(f"{index} sensors is sent to Amon-Ra server in thread {thread_index}")
                Sensor.objects.filter(external_id__in=sensors_sent).update(synced_at=timezone.now())
                SyncLog.objects.create(type="OUT", synced_count=len(sensors_sent))
                sensors_sent = []

    def handle(self, *args, **options):
        data_to_send = []
        logger.info("Preparing sensors data")
        for index, sensor in enumerate(Sensor.objects.filter(synced_at__isnull=True)):
            data = {"key": settings.APP_KEY, **sensor.serialize()}
            data["hash"] = get_data_hash(data, settings.HASH_KEY)
            data_to_send.append(data)

        threads = []
        chunk_size = len(data_to_send) // self.threads_count + 1
        data_chunks = [data_to_send[i : i + chunk_size] for i in range(len(data_to_send))[::chunk_size]]
        logger.info(f"Spawning {self.threads_count} threads")
        with futures.ThreadPoolExecutor() as executor:
            for i in range(len(data_chunks)):
                future = executor.submit(self.send_request, data_chunks[i], i)
                threads.append(future)

        for _ in futures.as_completed(threads):
            """Wait for all threads to finish."""
        logger.info(f"{len(data_to_send)} sensors is sent to Amon-Ra server")
