import logging
from typing import Dict, Optional

logger = logging.getLogger("metrics")


class StatsdClient:
    def __init__(self, prefix: str = "vaani"):
        self.prefix = prefix
        logger.info(f"Initialized StatsdClient with prefix: {prefix}")

    def timing(self, metric: str, value_ms: float, tags: Optional[Dict[str, str]] = None):
        formatted_metric = f"{self.prefix}.{self._sanitize_metric(metric)}"
        tag_str = self._format_tags(tags) if tags else ""
        logger.info(f"STATSD TIMING: {formatted_metric}{tag_str} {value_ms:.2f}ms")

    def increment(self, metric: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        formatted_metric = f"{self.prefix}.{self._sanitize_metric(metric)}"
        tag_str = self._format_tags(tags) if tags else ""
        logger.info(f"STATSD COUNT: {formatted_metric}{tag_str} +{value}")

    def gauge(self, metric: str, value: float, tags: Optional[Dict[str, str]] = None):
        formatted_metric = f"{self.prefix}.{self._sanitize_metric(metric)}"
        tag_str = self._format_tags(tags) if tags else ""
        logger.info(f"STATSD GAUGE: {formatted_metric}{tag_str} {value}")

    def _sanitize_metric(self, metric: str) -> str:
        return metric.replace("/", ".").replace("-", "_").replace(" ", "_")

    def _format_tags(self, tags: Dict[str, str]) -> str:
        if not tags:
            return ""
        return "," + ",".join(f"{k}:{v}" for k, v in tags.items())


# Create a singleton instance
statsd = StatsdClient()
