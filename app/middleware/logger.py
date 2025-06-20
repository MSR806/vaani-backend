import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Get a logger for our API - correlation ID will be automatically added by the filter
logger = logging.getLogger("api")


class RequestResponseLoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Get client IP - considering forwarded headers
        client_ip = request.headers.get(
            "X-Forwarded-For", request.client.host if request.client else "unknown"
        )

        # Start timing
        start_time = time.time()

        # Log request details - correlation ID is automatically added by the filter
        logger.info(
            f"{request.method} {request.url.path} from {client_ip} "
            f"(Query params: {request.query_params})"
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time and round to ms
            process_time = time.time() - start_time

            # Log response details
            logger.info(f"Response: {response.status_code} completed in {process_time:.4f}s")

            return response
        except Exception as e:
            # Log error details with stack trace
            logger.error(f"Request failed: {str(e)}", exc_info=True)
            raise
