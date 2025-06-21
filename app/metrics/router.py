import logging
import time
from typing import Callable

from fastapi import APIRouter, Request, Response
from fastapi.routing import APIRoute

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
                f"{method} {request.url.path} from {client_ip} "
                f"(Query params: {request.query_params})"
            )

            # Resource path logging (templated route path)
            logger.info(f"Resource path: {request.url.path}, Route pattern: {route_path}")

            try:
                # Process the request through the original handler
                response = await original_route_handler(request)

                # Calculate processing time
                process_time = time.time() - start_time
                process_time_ms = process_time * 1000  # Convert to ms

                # Extract status code
                status_code = response.status_code

                # Log response details (from original middleware)
                logger.info(f"Response: {status_code} completed in {process_time:.4f}s")

                # Record metrics
                tags = {"method": method, "path": route_path, "status_code": str(status_code)}

                # Log metrics to StatsD
                statsd.timing("http.request.duration", process_time_ms, tags)
                statsd.increment("http.request.count", 1, tags)

                return response
            except Exception as e:
                # Record error metrics
                process_time = time.time() - start_time
                process_time_ms = process_time * 1000

                # Log error details with stack trace (from original middleware)
                logger.error(f"Request failed: {str(e)}", exc_info=True)

                tags = {
                    "method": method,
                    "path": route_path,
                    "status_code": "500",  # Assuming 500 for exceptions
                    "error_type": type(e).__name__,
                }

                statsd.timing("http.request.duration", process_time_ms, tags)
                statsd.increment("http.request.errors", 1, tags)

                # Re-raise the exception
                raise

        return metrics_route_handler


class MetricsRouter(APIRouter):
    def __init__(self, *args, **kwargs):
        kwargs["route_class"] = MetricsAPIRoute
        super().__init__(*args, **kwargs)
