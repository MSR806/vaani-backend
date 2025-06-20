import datetime
import logging

from asgi_correlation_id import CorrelationIdFilter


class ISTFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        # Convert to IST (UTC+5:30)
        ist_time = datetime.datetime.fromtimestamp(record.created)
        # Add 5 hours and 30 minutes for IST
        ist_time = ist_time + datetime.timedelta(hours=5, minutes=30)
        return ist_time.strftime("%Y-%m-%dT%H:%M:%S+0530")


def configure_logging():
    # Create a custom formatter with correlation ID and IST timezone
    formatter = ISTFormatter("%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s")

    # Clear any existing handlers on the root logger
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Create console handler with correlation ID filter
    console_handler = logging.StreamHandler()
    console_handler.addFilter(CorrelationIdFilter(uuid_length=8))
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Add the handler to the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
