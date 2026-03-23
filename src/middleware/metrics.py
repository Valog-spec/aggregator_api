import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.middleware.metrics_definitions import (
    http_request_total,
    http_request_total_seconds,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            raise
        finally:
            duration = time.monotonic() - start_time

            http_request_total.labels(
                method=request.method, endpoint=request.url.path, status=status
            ).inc()
            http_request_total_seconds.labels(
                method=request.method, endpoint=request.url.path
            ).observe(duration)
