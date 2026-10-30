from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
import structlog.tracebacks
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from networking_intel.api import API_VERSION
from networking_intel.api.db import create_api_engine
from networking_intel.api.errors import install_error_handlers
from networking_intel.api.middleware import (
    REQUEST_ID_HEADER,
    Metrics,
    RateLimitMiddleware,
    RequestContextMiddleware,
    ResponseHeadersMiddleware,
)
from networking_intel.api.routes import api, ops
from networking_intel.config import Settings, get_settings

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = """
API somente leitura do MVP de *sales intelligence* para o time de vendas.

**Convenções**: valores monetários em BRL; retornos, razões e coberturas em fração decimal
(0.05 = 5%); scores 0-100 com faixa `lower`/`upper` para dados ausentes; datas ISO 8601;
`null` significa *não observado* e nunca zero.

**Limites**: não é probabilidade de compra. Retornos são de fundos para o cotista, não lucro
da gestora. Mesas de bancos marcadas `assumption` são pontuadas por premissa.

**Erros**: `application/problem+json` (RFC 7807) com `request_id` (também em `X-Request-ID`).
"""


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            # Structured tracebacks WITHOUT frame locals: locals can hold request
            # headers, connection objects or credentials.
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
            ),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )


def migration_head() -> str | None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


def create_app(settings: Settings | None = None, *, engine: Engine | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    metrics = Metrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.engine.dispose()

    app = FastAPI(
        title="Networking Sales Intelligence API",
        version=API_VERSION,
        description=DESCRIPTION,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.engine = engine or create_api_engine(settings)
    app.state.session_factory = sessionmaker(bind=app.state.engine, expire_on_commit=False)
    app.state.migration_head = migration_head()
    app.state.metrics = metrics
    app.state.data_mode = settings.app_data_mode

    install_error_handlers(app)
    app.include_router(ops)
    app.include_router(api)

    @app.get("/metrics", include_in_schema=False)
    def prometheus_metrics() -> Response:
        return Response(generate_latest(metrics.registry), media_type=CONTENT_TYPE_LATEST)

    # add_middleware wraps outward: the last one added runs first.
    app.add_middleware(ResponseHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.api_rate_limit_per_minute)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type", "If-None-Match", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "ETag", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    app.add_middleware(RequestContextMiddleware, metrics=metrics)
    return app
