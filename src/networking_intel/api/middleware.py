"""Cross-cutting HTTP concerns as pure ASGI middleware.

Order (outermost first): request context → rate limit → ETag/security headers.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from collections import defaultdict, deque
from collections.abc import Callable

import structlog
from prometheus_client import CollectorRegistry, Counter, Histogram
from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from networking_intel.api.errors import problem

REQUEST_ID_HEADER = "X-Request-ID"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
EXEMPT_PATHS = frozenset({"/health", "/ready", "/metrics"})
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"

logger = structlog.get_logger("networking_intel.api")


class Metrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.requests = Counter(
            "http_requests_total",
            "HTTP requests",
            ["method", "route", "status"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "http_request_duration_seconds",
            "HTTP request latency",
            ["method", "route"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
            registry=self.registry,
        )


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"  # low-cardinality label


class RequestContextMiddleware:
    """Correlation id, structured access log and Prometheus metrics."""

    def __init__(self, app: ASGIApp, metrics: Metrics) -> None:
        self.app = app
        self.metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get(REQUEST_ID_HEADER, "")
        request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - started
            route = _route_template(scope)
            method = scope["method"]
            status = status_holder["status"]
            self.metrics.requests.labels(method, route, str(status)).inc()
            self.metrics.latency.labels(method, route).observe(elapsed)
            logger.info(
                "http_request",
                method=method,
                route=route,
                status=status,
                duration_ms=round(elapsed * 1000, 2),
            )
            structlog.contextvars.clear_contextvars()


class RateLimitMiddleware:
    """Sliding-window limit per client address (local, in-memory).

    Behind a reverse proxy this sees the proxy address; production should rate
    limit at the edge as well.
    """

    def __init__(
        self, app: ASGIApp, limit_per_minute: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.app = app
        self.limit = limit_per_minute
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = client[0] if client else "unknown"
        now = self.clock()
        window = self.hits[key]
        while window and now - window[0] >= 60:
            window.popleft()
        if len(window) >= self.limit:
            retry_after = max(1, int(60 - (now - window[0])) + 1)
            response = problem(
                Request(scope),
                429,
                f"Limite de {self.limit} requisições por minuto excedido.",
                code="rate-limit",
                headers={"Retry-After": str(retry_after)},
            )
            await response(scope, receive, send)
            return
        window.append(now)
        await self.app(scope, receive, send)


class ResponseHeadersMiddleware:
    """Security headers everywhere; ETag revalidation for API JSON.

    `Cache-Control: no-cache` forces revalidation on every request, so a new
    data load is visible immediately — the ETag only saves bandwidth.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope["path"]
        cacheable = scope["method"] == "GET" and path.startswith("/api/")
        if_none_match = Headers(scope=scope).get("if-none-match")
        start: Message | None = None
        chunks: list[bytes] = []

        async def send_wrapper(message: Message) -> None:
            nonlocal start
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    headers.setdefault(name, value)
                if not path.startswith(("/docs", "/redoc")):
                    headers.setdefault("Content-Security-Policy", API_CSP)
                if not (cacheable and message["status"] == 200):
                    headers.setdefault("Cache-Control", "no-store")
                    await send(message)
                    return
                start = message
                return
            if start is None:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            if message.get("more_body", False):
                return
            body = b"".join(chunks)
            etag = f'W/"{hashlib.sha256(body).hexdigest()[:32]}"'
            headers = MutableHeaders(scope=start)
            headers["ETag"] = etag
            headers["Cache-Control"] = "no-cache"
            headers["Vary"] = "Accept, Origin"
            if if_none_match and etag in {tag.strip() for tag in if_none_match.split(",")}:
                start["status"] = 304
                if "content-length" in headers:
                    del headers["content-length"]
                await send(start)
                await send({"type": "http.response.body", "body": b""})
                return
            headers["content-length"] = str(len(body))
            await send(start)
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, send_wrapper)
