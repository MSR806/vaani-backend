import logging
import time
from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

from app.constants.metrics import Constants
from app.metrics.statsd_client import statsd

# Use the same logger as in the original middleware
logger = logging.getLogger("api")


class MetricsAPIRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def metrics_route_handler(request: Request) -> Response:
            # Get templated route path (available here)
            route_path = request.scope["route"].path
            method = request.method

            # Get client IP - considering forwarded headers (from original middleware)
            client_ip = request.headers.get(
                "X-Forwarded-For", request.client.host if request.client else "unknown"
            )

            # Start timing
            start_time = time.time()

            # Log request details - using format from original middleware
            logger.info(
                f"Request | {method} | {request.url.path} | {client_ip} | {request.query_params if request.query_params else 'No query params'}"
            )

            try:
                # Process the request through the original handler
                response = await original_route_handler(request)

                # Calculate processing time
                process_time = time.time() - start_time
                process_time_ms = process_time * 1000  # Convert to ms

                # Extract status code
                status_code = response.status_code

                # Log response details (from original middleware)
                logger.info(
                    f"Response | {method} | {request.url.path} | {client_ip} | {status_code} | {process_time_ms:.4f}ms"
                )

                # Record metrics
                self._log_metric(method, route_path, status_code, process_time_ms)

                return response
            except Exception as e:
                # Record error metrics
                process_time = time.time() - start_time
                process_time_ms = process_time * 1000

                # Log error details with stack trace (from original middleware)
                logger.error(
                    f"Uncaught exception in request | {method} | {request.url.path} | {client_ip} | {str(e)} | {process_time_ms:.4f}ms",
                    exc_info=True,
                )

                self._log_metric(method, route_path, 500, process_time_ms)

                # Re-raise the exception
                raise

        return metrics_route_handler

    def _log_metric(self, method, path, status_code, process_time_ms):
        tags = {
            Constants.Tag.METHOD: method,
            Constants.Tag.PATH: path,
            Constants.Tag.CODE: status_code,
        }
        statsd.timing(
            Constants.Metric.API_LATENCY,
            process_time_ms,
            Constants.Metric.HUNDRED_SAMPLING_RATE,
            tags,
        )
        statsd.increment(
            Constants.Metric.API_COUNT, 1, Constants.Metric.HUNDRED_SAMPLING_RATE, tags
        )


class MetricsRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        kwargs["route_class"] = MetricsAPIRoute
        super().__init__(*args, **kwargs)
