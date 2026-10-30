"""End-to-end API tests against PostgreSQL/PostGIS loaded by the real pipeline."""

from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from networking_intel.api.app import create_app
from networking_intel.api.db import get_session
from networking_intel.config import Settings
from networking_intel.etl.load import run_etl
from networking_intel.etl.load_enriched import run_enriched_load

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
ROLE_EMAIL = re.compile(
    r"^(compliance|juridico|legal|grc|relacionamento|contato|institucional|atendimento|"
    r"reguladores|info|ri|risco|ouvidoria|ol-)",
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def loaded_database() -> str:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = DATABASE_URL
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    run_etl(ROOT / "data/staging/pilot_accounts.csv", DATABASE_URL)
    first = run_enriched_load(ROOT, DATABASE_URL)
    second = run_enriched_load(ROOT, DATABASE_URL)
    assert second["fund_observations_inserted"] == 0  # idempotent reload
    assert first["funds"] == second["funds"]
    return DATABASE_URL


@pytest.fixture(scope="module")
def client(loaded_database: str) -> Iterator[TestClient]:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        database_url=loaded_database,
        api_trusted_hosts="testserver",
        api_rate_limit_per_minute=10_000,
        log_level="WARNING",
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def get(client: TestClient, path: str, **params: Any) -> Any:
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_readiness_reports_head_migration_and_data(client: TestClient) -> None:
    body = get(client, "/ready")
    assert body["status"] == "ready"
    assert body["checks"]["migration_is_head"] is True


def test_session_is_read_only(client: TestClient) -> None:
    app = client.app
    request = type("R", (), {"app": app})()
    sessions = get_session(request)
    session = next(sessions)
    with pytest.raises(DBAPIError, match="read-only"):
        session.execute(text("UPDATE organizations SET legal_name = 'x'"))
    sessions.close()


def test_accounts_are_paginated_sorted_and_searchable(client: TestClient) -> None:
    page = get(client, "/api/v1/accounts", page_size=5, sort="priority", order="desc")
    assert page["meta"]["total"] == 12 and len(page["data"]) == 5
    points = [a["priority"]["point"] for a in page["data"] if a["priority"]["point"] is not None]
    assert points == sorted(points, reverse=True)
    second = get(client, "/api/v1/accounts", page_size=5, page=2, sort="priority", order="desc")
    assert not {a["account_id"] for a in page["data"]} & {a["account_id"] for a in second["data"]}

    patria = get(client, "/api/v1/accounts", q="patria")["data"]
    assert [a["account_id"] for a in patria] == ["org-patria"]
    rj = get(client, "/api/v1/accounts", state="RJ")["data"]
    assert rj and all(a["headquarters"]["state"] == "RJ" for a in rj)


def test_account_360_has_sources_and_no_unnecessary_personal_data(client: TestClient) -> None:
    detail = get(client, "/api/v1/accounts/org-verde-asset")
    assert detail["cnpj"] == "19749539000176"
    assert detail["legal_entities"] and all(e["source"]["sha256"] for e in detail["legal_entities"])
    for entity in detail["legal_entities"]:
        email = entity["email_institutional"]
        assert email is None or ROLE_EMAIL.match(email), email
    for office in detail["offices"]:
        location = office["location"]
        if location["is_exact"]:
            assert location["precision"] == "address" and location["latitude"] is not None
    assert all(
        set(p) == {"full_name", "role_title", "basis", "as_of_date"} for p in detail["people"]
    )
    assert "email_public" not in detail and "linkedin_url" not in detail
    assert detail["scores"] and detail["products"]
    assert detail["quality"]["account_id"] == "org-verde-asset"


def test_banks_are_scored_by_desk(client: TestClient) -> None:
    units = get(client, "/api/v1/business-units", account_id="org-itau-bba")
    keys = {u["unit_key"] for u in units}
    assert "org-itau-bba:sales-trading-treasury" in keys
    assert all(u["score"] and u["score"]["evidence_mode"] == "assumption" for u in units)
    ranking = get(client, "/api/v1/scores", page_size=200)
    assert "org-itau-bba" not in {s["unit_key"] for s in ranking["data"]}


def test_ranking_and_explanations_are_consistent(client: TestClient) -> None:
    ranking = get(client, "/api/v1/scores", page_size=200)
    assert ranking["meta"]["total"] == 22
    assert [s["rank"] for s in ranking["data"]] == list(range(1, 23))
    top = ranking["data"][0]
    explanation = get(client, f"/api/v1/scores/{top['unit_key']}/explanation")
    fit_points = sum(
        f["contribution_points"] or 0 for f in explanation["factors"] if f["group"] == "fit"
    )
    assert fit_points == pytest.approx(top["fit"]["point"], abs=0.05)
    assert all(f["weight"] is not None for f in explanation["factors"])
    assert all(f["evidence"] for f in explanation["factors"] if f["value"] is not None)
    assert explanation["limitations"]
    by_mode = get(client, "/api/v1/scores", evidence_mode="assumption")["data"]
    assert all(s["priority"]["point"] is None for s in by_mode)


def test_comparison_warns_when_mixing_evidence_modes(client: TestClient) -> None:
    body = get(
        client,
        "/api/v1/comparisons",
        units="org-verde-asset,org-btg-pactual:sales-trading-treasury",
    )
    assert len(body["units"]) == 2 and body["warnings"]
    factor = next(f for f in body["factors"] if f["key"] == "net_flows")
    assert factor["values"]["org-btg-pactual:sales-trading-treasury"]["value"] is None
    assert (
        client.get("/api/v1/comparisons", params={"units": "org-verde-asset,org-zzz"}).status_code
        == 404
    )


def test_funds_metrics_respect_comparability(client: TestClient) -> None:
    funds = get(
        client,
        "/api/v1/funds",
        account_id="org-verde-asset",
        with_metrics="true",
        sort="return_12m",
        page_size=200,
    )
    assert funds["data"]
    for fund in funds["data"]:
        metrics = fund["metrics"]
        assert metrics["currency"] == "BRL"
        if metrics["return_12m_status"] != "ok":
            assert metrics["return_12m"] is None
    best = funds["data"][0]
    perf = get(
        client, f"/api/v1/funds/{best['class_cnpj']}/performance", subclass_id=best["subclass_id"]
    )
    assert perf["points"][0]["quota_index"] == pytest.approx(100.0)
    assert perf["sources"] and all("dados.cvm.gov.br" in s for s in perf["sources"])
    assert "não representa" in perf["note"]
    assert client.get("/api/v1/funds/00000000000000/performance").status_code == 404


def test_map_geojson_respects_bbox_precision_and_density(client: TestClient) -> None:
    bbox = (-46.75, -23.65, -46.6, -23.5)
    collection = get(client, "/api/v1/map/offices", bbox=",".join(map(str, bbox)))
    assert collection["features"] and "OpenStreetMap" in collection["meta"]["attribution"]
    for feature in collection["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        assert bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]
        if feature["properties"]["is_exact"]:
            assert feature["properties"]["precision"] == "address"
    exact = get(client, "/api/v1/map/offices", exact_only="true")
    assert all(f["properties"]["is_exact"] for f in exact["features"])
    everything = get(client, "/api/v1/map/offices")
    density = get(client, "/api/v1/map/density", cell_m=2000)
    assert sum(c["offices"] for c in density["cells"]) == everything["meta"]["count"]


def test_signals_and_data_quality(client: TestClient) -> None:
    signals = get(client, "/api/v1/signals", account_id="org-kinea")
    assert signals["data"] and all(s["source"]["url"] for s in signals["data"])
    quality = get(client, "/api/v1/data-quality")
    status = {f["source_id"]: f["status"] for f in quality["freshness"]}
    assert status["cvm_inf_diario"] in {"fresh", "stale"}
    assert quality["database"]["fund_classes"] > 6000
    conflicts = get(client, "/api/v1/data-quality/conflicts", status="pending_review")
    assert conflicts["meta"]["total"] == sum(a["open_conflicts"] for a in quality["accounts"])


def test_search_by_cnpj_and_accents(client: TestClient) -> None:
    by_cnpj = get(client, "/api/v1/search", q="19.749.539/0001-76")
    assert by_cnpj[0]["account_id"] == "org-verde-asset" and by_cnpj[0]["match_kind"] == "cnpj"
    accent = get(client, "/api/v1/search", q="Ibiúna")
    assert accent[0]["account_id"] == "org-ibiuna"


def _plan(loaded_database: str, sql: str, params: dict[str, Any]) -> str:
    engine = create_engine(loaded_database)
    with engine.connect() as connection:
        connection.execute(text("SET enable_seqscan = off"))
        rows = connection.execute(text("EXPLAIN " + sql), params).scalars().all()
    engine.dispose()
    return "\n".join(rows)


def test_map_and_ranking_queries_can_use_their_indexes(loaded_database: str) -> None:
    bbox_plan = _plan(
        loaded_database,
        "SELECT office_key FROM offices WHERE location && ST_MakeEnvelope(-46.8,-23.7,-46.5,-23.4,4326)",
        {},
    )
    assert "ix_office_location_gist" in bbox_plan
    rank_plan = _plan(
        loaded_database,
        "SELECT unit_key FROM opportunity_scores WHERE score_run_id = "
        "(SELECT id FROM score_runs ORDER BY loaded_at DESC LIMIT 1) ORDER BY rank LIMIT 50",
        {},
    )
    assert "ix_opportunity_run_rank" in rank_plan
    series_plan = _plan(
        loaded_database,
        "SELECT observation_date FROM fund_observations WHERE fund_id = "
        "(SELECT id FROM funds LIMIT 1) AND subclass_id = '' ORDER BY observation_date",
        {},
    )
    assert "ix_fund_observation_date" in series_plan or "uq_fund_observation_source" in series_plan


def test_demo_mode_is_declared_by_meta(loaded_database: str) -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        app_env="test",
        app_data_mode="demo",
        database_url=loaded_database,
        api_trusted_hosts="testserver",
        log_level="WARNING",
    )
    with TestClient(create_app(settings)) as demo_client:
        meta = get(demo_client, "/api/v1/meta")
    assert meta["data_mode"] == "demo"
    assert "congelada" in meta["data_note"] and meta["fund_reference_date"] in meta["data_note"]
