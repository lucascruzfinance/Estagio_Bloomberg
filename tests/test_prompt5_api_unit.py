"""API behaviour that does not need a database (security, middleware, contract)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine

from networking_intel.api import repository
from networking_intel.api.app import create_app
from networking_intel.api.db import get_session
from networking_intel.config import Settings

UNREACHABLE = "postgresql+psycopg://user:s3cr3t-pass@127.0.0.1:1/none"
FRONTEND_PATHS = {
    "/api/v1/meta",
    "/api/v1/search",
    "/api/v1/accounts",
    "/api/v1/accounts/{account_id}",
    "/api/v1/business-units",
    "/api/v1/scores",
    "/api/v1/scores/{unit_key}/explanation",
    "/api/v1/comparisons",
    "/api/v1/funds",
    "/api/v1/funds/{class_cnpj}/performance",
    "/api/v1/signals",
    "/api/v1/map/offices",
    "/api/v1/map/density",
    "/api/v1/data-quality",
    "/api/v1/data-quality/conflicts",
}


def settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": UNREACHABLE,
        "api_trusted_hosts": "testserver",
        "api_cors_origins": "http://localhost:5173",
        "log_level": "WARNING",
        **overrides,
    }
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    app = create_app(settings(), engine=create_engine(UNREACHABLE))

    def fake_session() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_session] = fake_session
    monkeypatch.setattr(
        repository,
        "search",
        lambda session, q, limit: [
            {
                "account_id": "org-x",
                "canonical_name": "X",
                "institution_type": "gestora",
                "matched": q,
                "match_kind": "exact",
                "alias_kind": "canonical",
            }
        ],
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


# --- configuration -------------------------------------------------------------


def test_production_settings_are_locked_down() -> None:
    with pytest.raises(ValidationError, match="development password"):
        settings(
            app_env="production",
            database_url="postgresql+psycopg://u:local-development-only-x@h/db",
        )
    with pytest.raises(ValidationError, match="explicit"):
        settings(
            app_env="production", database_url="postgresql+psycopg://u:p@h/db", api_cors_origins="*"
        )
    with pytest.raises(ValidationError, match="https"):
        settings(
            app_env="production",
            database_url="postgresql+psycopg://u:p@h/db",
            api_cors_origins="http://app.example.com",
            api_trusted_hosts="api.example.com",
        )
    prod = settings(
        app_env="production",
        database_url="postgresql+psycopg://u:p@h/db",
        api_cors_origins="https://app.example.com",
        api_trusted_hosts="api.example.com",
    )
    assert prod.docs_enabled is False


def test_docs_disabled_in_production_app() -> None:
    prod = settings(
        app_env="production",
        database_url="postgresql+psycopg://u:p@h/db",
        api_cors_origins="https://app.example.com",
        api_trusted_hosts="testserver",
    )
    with TestClient(create_app(prod, engine=create_engine(UNREACHABLE))) as test_client:
        assert test_client.get("/docs").status_code == 404
        assert test_client.get("/openapi.json").status_code == 404


# --- contract ------------------------------------------------------------------


def test_openapi_lists_every_frontend_endpoint_with_problem_errors(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert set(spec["paths"]) >= FRONTEND_PATHS
    assert "Problem" in spec["components"]["schemas"]
    for path in FRONTEND_PATHS:
        responses = spec["paths"][path]["get"]["responses"]
        assert {"422", "429", "500"} <= set(responses), path
    assert "BRL" in spec["info"]["description"] and "null" in spec["info"]["description"]


def test_health_needs_no_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_readiness_fails_fast_without_leaking_connection_details() -> None:
    app = create_app(settings(api_connect_timeout_s=1))  # real engine factory
    started = time.perf_counter()
    with TestClient(app) as test_client:
        response = test_client.get("/ready")
    assert time.perf_counter() - started < 15
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert "s3cr3t" not in response.text and "127.0.0.1" not in response.text


# --- errors and input validation -------------------------------------------------


def test_validation_errors_are_problem_json_without_echoing_input(client: TestClient) -> None:
    payload = "<script>alert(1)</script>"
    response = client.get("/api/v1/scores", params={"sort": payload})
    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["errors"][0]["loc"] == ["query", "sort"]
    assert payload not in response.text
    assert body["request_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/accounts/ORG-UPPER",
        "/api/v1/funds/123/performance",
        "/api/v1/scores/not-a-key/explanation",
        "/api/v1/accounts?page_size=500",
        "/api/v1/map/density?cell_m=5",
        "/api/v1/map/offices?bbox=10,10,0,0",
        "/api/v1/comparisons?units=org-a",
        "/api/v1/search?q=a",
    ],
)
def test_invalid_inputs_are_rejected(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 422


def test_unhandled_errors_hide_internals(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("password=hunter2 at C:/secret/path.py line 42")

    monkeypatch.setattr(repository, "search", boom)
    response = client.get("/api/v1/search", params={"q": "verde"})
    assert response.status_code == 500
    assert "hunter2" not in response.text and "Traceback" not in response.text
    assert response.json()["request_id"]


# --- middleware --------------------------------------------------------------------


def test_request_id_is_propagated_or_regenerated(client: TestClient) -> None:
    good = client.get("/health", headers={"X-Request-ID": "abc12345-req"})
    assert good.headers["x-request-id"] == "abc12345-req"
    bad = client.get("/health", headers={"X-Request-ID": "bad id\r\ninjected"})
    assert bad.headers["x-request-id"] != "bad id\r\ninjected"
    assert len(bad.headers["x-request-id"]) == 32


def test_security_headers_and_revalidating_cache(client: TestClient) -> None:
    first = client.get("/api/v1/search", params={"q": "verde"})
    assert first.headers["x-content-type-options"] == "nosniff"
    assert first.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert first.headers["cache-control"] == "no-cache"
    etag = first.headers["etag"]
    second = client.get("/api/v1/search", params={"q": "verde"}, headers={"If-None-Match": etag})
    assert second.status_code == 304 and second.content == b""
    changed = client.get("/api/v1/search", params={"q": "kinea"}, headers={"If-None-Match": etag})
    assert changed.status_code == 200
    assert client.get("/api/v1/scores?sort=x").headers["cache-control"] == "no-store"


def test_cors_allows_only_configured_origin_and_get(client: TestClient) -> None:
    allowed = client.options(
        "/api/v1/meta",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    denied = client.options(
        "/api/v1/meta",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in denied.headers
    post = client.options(
        "/api/v1/meta",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert post.status_code == 400


def test_untrusted_host_is_rejected(client: TestClient) -> None:
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400


def test_rate_limit_returns_429_with_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    app = create_app(settings(api_rate_limit_per_minute=3), engine=create_engine(UNREACHABLE))

    def fake_session() -> Iterator[object]:
        yield object()

    app.dependency_overrides[get_session] = fake_session
    monkeypatch.setattr(repository, "search", lambda session, q, limit: [])
    with TestClient(app) as test_client:
        statuses = [
            test_client.get("/api/v1/search", params={"q": "xx"}).status_code for _ in range(5)
        ]
        assert test_client.get("/health").status_code == 200  # operational paths are exempt
        limited = test_client.get("/api/v1/search", params={"q": "xx"})
    assert statuses.count(429) >= 1
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1
    assert limited.json()["status"] == 429


def test_metrics_use_route_templates(client: TestClient) -> None:
    client.get("/api/v1/accounts/org-does-not-exist-but-valid")
    exposition = client.get("/metrics").text
    assert "http_requests_total" in exposition
    assert 'route="/api/v1/accounts/{account_id}"' in exposition
    assert "org-does-not-exist" not in exposition


def test_exception_logs_never_include_frame_locals(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(*args: object, **kwargs: object) -> None:
        api_token = "local-secret-xyz"  # a value that must never reach the logs
        raise RuntimeError(f"failed with {len(api_token)} chars")

    monkeypatch.setattr(repository, "search", boom)
    assert client.get("/api/v1/search", params={"q": "verde"}).status_code == 500
    logs = capsys.readouterr().out
    assert "unhandled_exception" in logs
    assert "local-secret-xyz" not in logs
