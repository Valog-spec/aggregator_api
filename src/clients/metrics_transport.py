import time

import httpx

from src.middleware.metrics_definitions import (
    events_provider_request_duration_seconds,
    events_provider_requests_total,
)


class MetricsTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport):
        self._transport = transport

    async def handle_async_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        start_time = time.monotonic()
        endpoint = self._normalize_path(request.url.path)

        status = "exception"

        try:
            response = await self._transport.handle_async_request(request)
            status = str(response.status_code)
            return response
        finally:
            duration = time.monotonic() - start_time

            events_provider_requests_total.labels(
                endpoint=endpoint,
                status=status,
            ).inc()

            events_provider_request_duration_seconds.labels(
                endpoint=endpoint,
            ).observe(duration)

    def _normalize_path(self, path: str) -> str:
        if "/seats" in path:
            return "/seats"
        if "/register" in path or "/unregister" in path:
            return "/registration"
        if "/events" in path:
            return "/events"
        return "unknown"


def create_http_client(headers: dict[str, str]) -> httpx.AsyncClient:
    base_transport = httpx.AsyncHTTPTransport(retries=0)

    transport = MetricsTransport(base_transport)

    return httpx.AsyncClient(
        headers=headers,
        transport=transport,
        follow_redirects=True,
        timeout=30.0,
    )
