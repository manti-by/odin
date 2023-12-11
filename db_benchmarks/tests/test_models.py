import logging
import random
from collections import defaultdict
from statistics import median
from time import sleep, time

import pytest

from db_benchmarks.core.models import (
    StatusChoices,
    PlainModel,
    IndexedModel,
    OptimizedModel,
)
from db_benchmarks.tests.factories import (
    PlainModelFactory,
    IndexedModelFactory,
    OptimizedModelFactory,
)

logger = logging.getLogger(__name__)


@pytest.mark.django_db
class TestSelectSpeed:
    cooldown_delay = 10 * 60
    batch_size = 1000 * 1000
    run_count = 100

    def setup_method(self):
        logger.info("Start generating the data")

        PlainModelFactory.create_batch(self.batch_size)
        sleep(self.cooldown_delay)  # Wait a minute for DB cool down

        IndexedModelFactory.create_batch(self.batch_size)
        sleep(self.cooldown_delay)

        OptimizedModelFactory.create_batch(self.batch_size)
        sleep(self.cooldown_delay)

    def test_select_choice_speed(self):
        logger.info("Start test_select_choice_speed")

        results = defaultdict(list)
        random_choice = random.choice(StatusChoices.choices)
        for model in (PlainModel, IndexedModel, OptimizedModel):
            for _ in range(self.run_count):
                start_time = time()
                _ = list(model.objects.filter(choice_field=random_choice))
                results[model.__name__].append(time() - start_time)
            sleep(self.cooldown_delay)

        for model, stats in results.items():
            logger.info(f"{model} exec time {median(stats)}")
