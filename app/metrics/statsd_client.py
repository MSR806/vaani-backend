import logging
from typing import Dict, Optional

import statsd as st

from app.config import STATSD

logger = logging.getLogger("metrics")


class StatsdClient:
    def __init__(self):
        self.client = st.StatsClient(
            host=STATSD.HOST,
            port=STATSD.PORT,
            prefix="vaani",
        )

    def timing(self, stat: str, delta: float, rate: int = 1, tags: Optional[Dict[str, str]] = None):
        stat = self._sanitize_metric(stat)
        self.client.timing(stat=stat, delta=delta, rate=rate, tags=tags)

    def increment(
        self, stat: str, count: int = 1, rate: int = 1, tags: Optional[Dict[str, str]] = None
    ):
        stat = self._sanitize_metric(stat)
        self.client.incr(stat=stat, count=count, rate=rate, tags=tags)

    def _sanitize_metric(self, metric: str) -> str:
        return metric.replace("/", ".").replace("-", "_").replace(" ", "_")


statsd = StatsdClient()
