from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlsplit

import httpx
import structlog
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from networking_intel.enrichment import ENRICHMENT_VERSION
from networking_intel.enrichment.cache import RawArtifact, RawCache
from networking_intel.enrichment.sources import require_real_source

USER_AGENT = (
    f"networking-intel/{ENRICHMENT_VERSION} "
    "(Bloomberg sales-intelligence internship MVP; low-volume, cached research)"
)
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

logger = structlog.get_logger("networking_intel.enrichment.http")


class RetryableStatusError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"retryable HTTP status {status_code}")
        self.status_code = status_code


class SourceUnavailableError(RuntimeError):
    def __init__(self, source_id: str, url: str, reason: str) -> None:
        super().__init__(f"{source_id} unavailable: {reason}")
        self.source_id = source_id
        self.url = url
        self.reason = reason


def safe_url(url: str) -> str:
    """Host and path only: query strings can carry addresses or tokens."""
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


class Fetcher:
    """Cache-first HTTP fetcher with per-source rate limit and bounded retries."""

    def __init__(
        self,
        cache: RawCache,
        *,
        client: httpx.Client | None = None,
        max_attempts: int = 3,
        max_backoff_seconds: float = 8.0,
        offline: bool = False,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cache = cache
        self.client = client or httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=httpx.Timeout(120.0, connect=15.0),
            follow_redirects=True,
        )
        self.max_attempts = max_attempts
        self.max_backoff_seconds = max_backoff_seconds
        self.offline = offline
        self._sleep = sleep
        self._clock = clock
        self._last_request: dict[str, float] = {}

    def _respect_rate_limit(self, source_id: str, interval: float) -> None:
        last = self._last_request.get(source_id)
        if last is not None:
            wait = interval - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)
        self._last_request[source_id] = self._clock()

    def fetch(
        self,
        source_id: str,
        url: str,
        *,
        params: dict[str, str] | None = None,
        suffix: str = ".bin",
        max_age_seconds: float | None = None,
        now: datetime | None = None,
    ) -> RawArtifact:
        spec = require_real_source(source_id)
        ttl = spec.max_age.total_seconds() if max_age_seconds is None else max_age_seconds
        cached = self.cache.latest(source_id, url, params, max_age_seconds=ttl, now=now)
        if cached is not None:
            return cached
        if self.offline:
            stale = self.cache.latest(source_id, url, params)
            if stale is not None:
                return stale
            raise SourceUnavailableError(source_id, safe_url(url), "offline and not cached")

        retrying = Retrying(
            stop=stop_after_attempt(self.max_attempts),
            wait=wait_exponential(multiplier=1, max=self.max_backoff_seconds),
            retry=retry_if_exception_type((httpx.TransportError, RetryableStatusError)),
            sleep=self._sleep,
            reraise=True,
        )
        try:
            for attempt in retrying:
                with attempt:
                    self._respect_rate_limit(source_id, spec.rate_limit_seconds)
                    response = self.client.get(url, params=params)
                    logger.info(
                        "source_fetch",
                        source_id=source_id,
                        url=safe_url(url),
                        status=response.status_code,
                        attempt=attempt.retry_state.attempt_number,
                    )
                    if response.status_code in RETRYABLE_STATUS:
                        raise RetryableStatusError(response.status_code)
        except RetryableStatusError as error:
            raise SourceUnavailableError(
                source_id, safe_url(url), f"HTTP {error.status_code} after retries"
            ) from error
        except httpx.TransportError as error:
            raise SourceUnavailableError(
                source_id, safe_url(url), f"{type(error).__name__} after retries"
            ) from error

        if response.status_code >= 400:
            raise SourceUnavailableError(source_id, safe_url(url), f"HTTP {response.status_code}")
        return self.cache.store(
            source_id=source_id,
            url=url,
            params=params,
            content=response.content,
            http_status=response.status_code,
            suffix=suffix,
            content_type=response.headers.get("content-type"),
            fetched_at=now or datetime.now(UTC),
        )
