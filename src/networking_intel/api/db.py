from __future__ import annotations

from collections.abc import Generator

from fastapi import Request
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from networking_intel.config import Settings


def create_api_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        connect_args={
            "options": f"-c statement_timeout={settings.api_statement_timeout_ms}",
            "application_name": "networking-intel-api",
            # Fail fast when the database is down so /ready answers within seconds.
            "connect_timeout": settings.api_connect_timeout_s,
        },
    )


def get_session(request: Request) -> Generator[Session, None, None]:
    """One read-only transaction per request: the API can never write."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        try:
            yield session
        finally:
            session.rollback()
