from __future__ import annotations

import csv
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import polars as pl
import pytest
from pydantic import ValidationError

from networking_intel.enrichment.cache import RawCache
from networking_intel.enrichment.conflicts import detect_conflicts, merge_review_queue
from networking_intel.enrichment.cvm import parse_managers
from networking_intel.enrichment.geocode import (
    ParsedAddress,
    classify_precision,
    geocode,
    parse_street,
)
from networking_intel.enrichment.http import Fetcher
from networking_intel.enrichment.identity import IdentityRegistry, load_registry, propose_candidates
from networking_intel.enrichment.pipeline import is_role_email, months_back
from networking_intel.enrichment.quality import SourceRun, check_freshness
from networking_intel.enrichment.returns import broad_reference_date, compute_all
from networking_intel.etl.schemas import load_pilot_csv
from tests.prompt3_helpers import zip_fixtures

ROOT = Path(__file__).resolve().parents[1]
REF = date(2026, 10, 27)


def daily_series(
    class_cnpj: str, quotas: list[float], *, start: date, step_days: int = 1
) -> list[dict[str, Any]]:
    return [
        {
            "class_cnpj": class_cnpj,
            "subclass_id": "",
            "date": start + timedelta(days=index * step_days),
            "quota": quota,
            "nav_brl": 1000.0,
            "inflow_brl": 2.0,
            "outflow_brl": 1.0,
            "investors": 10,
        }
        for index, quota in enumerate(quotas)
    ]


def frame(rows: list[dict[str, Any]]) -> pl.DataFrame:
    return pl.DataFrame(rows)


def by_class(rows: list[dict[str, Any]], **peers: str) -> dict[str, Any]:
    return {m.class_cnpj: m for m in compute_all(frame(rows), REF, peers or None)}


# --- returns -----------------------------------------------------------------


def test_return_requires_full_window_and_reports_status() -> None:
    start = REF - timedelta(days=400)
    full = daily_series("A", [1.0 + 0.001 * i for i in range(401)], start=start)
    short = daily_series("B", [1.0 + 0.001 * i for i in range(60)], start=REF - timedelta(days=59))
    metrics = by_class(full + short)

    assert metrics["A"].return_status["12m"] == "ok"
    expected = (1.0 + 0.001 * 400) / (1.0 + 0.001 * 35) - 1
    assert metrics["A"].returns["12m"] == pytest.approx(expected)
    assert metrics["A"].net_flow_status == "ok"
    assert metrics["A"].net_flow_12m_brl == pytest.approx(365.0)
    assert metrics["A"].currency == "BRL"
    assert metrics["B"].returns["12m"] is None
    assert metrics["B"].return_status["12m"] == "insufficient_history"
    assert metrics["B"].return_status["1m"] == "ok"
    assert metrics["B"].net_flow_12m_brl is None


def test_gaps_and_stale_series_are_not_comparable() -> None:
    gapped = daily_series("G", [1.0] * 60, start=REF - timedelta(days=59))
    gapped = [
        row
        for row in gapped
        if not REF - timedelta(days=20) < row["date"] < REF - timedelta(days=5)
    ]
    stale = daily_series("S", [1.0] * 100, start=REF - timedelta(days=120))
    metrics = by_class(gapped + stale)

    assert metrics["G"].return_status["1m"] == "gap_in_series"
    assert metrics["S"].return_status["1m"] == "stale_series"
    assert "stale_series" in metrics["S"].series_flags


def test_idiosyncratic_quota_jump_is_flagged_but_market_shock_is_kept() -> None:
    start = REF - timedelta(days=40)
    base = [1.0] * 41

    def shocked(factor: float) -> list[float]:
        return base[:30] + [factor] * 11

    rows = (
        daily_series("CRASH1", shocked(0.70), start=start)
        + daily_series("CRASH2", shocked(0.72), start=start)
        + daily_series("CRASH3", shocked(0.71), start=start)
        + daily_series("AMORT", shocked(0.40), start=start)
        + daily_series("FLAT", base, start=start)
    )
    peers = {key: "Ações" for key in ("CRASH1", "CRASH2", "CRASH3", "AMORT")}
    metrics = by_class(rows, **peers, FLAT="Renda Fixa")

    assert metrics["CRASH1"].return_status["1m"] == "ok"
    assert metrics["CRASH1"].returns["1m"] == pytest.approx(-0.30)
    assert metrics["AMORT"].return_status["1m"] == "quota_event_suspected"
    assert metrics["AMORT"].returns["1m"] is None
    assert metrics["FLAT"].returns["1m"] == pytest.approx(0.0)


def test_broad_reference_date_ignores_sparse_last_day() -> None:
    rows = [
        row
        for key in ("A", "B", "C")
        for row in daily_series(key, [1.0, 1.0], start=REF - timedelta(days=1))
    ]
    rows.append({**rows[0], "date": REF + timedelta(days=1)})
    assert broad_reference_date(frame(rows)) == REF


def test_months_back_covers_twelve_month_window() -> None:
    periods = months_back(date(2026, 10, 30), 13)
    assert periods[0] == "202510" and periods[-1] == "202610" and len(periods) == 13


# --- geocoding ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AV BRIGADEIRO FARIA LIMA, 3477", ("Avenida Brigadeiro Faria Lima", "3477")),
        ("AVENIDA BRIGADEIRO FARIA LIMA, N° 3.144", ("Avenida Brigadeiro Faria Lima", "3144")),
        ("RUA HUMAITA , 275 / 5 ANDAR", ("Rua Humaita", "275")),
        ("PRAIA DE BOTAFOGO, N.º 501", ("Praia De Botafogo", "501")),
        ("R. MINAS DE PRATA, 30", ("Rua Minas De Prata", "30")),
        ("Rua Leopoldo Couto Magalhães Júnior", ("Rua Leopoldo Couto Magalhães Júnior", None)),
    ],
)
def test_parse_street(raw: str, expected: tuple[str, str | None]) -> None:
    assert parse_street(raw) == expected


ADDRESS = ParsedAddress("Avenida Cidade Jardim", "803", "São Paulo", "SP", "01453000")


def hit(number: str, road: str, city: str) -> dict[str, Any]:
    return {
        "lat": "-23.58",
        "lon": "-46.68",
        "osm_type": "way",
        "osm_id": 1,
        "display_name": f"{number}, {road}, {city}",
        "addresstype": "building",
        "address": {"house_number": number, "road": road, "city": city},
    }


def test_exact_precision_requires_number_and_street() -> None:
    assert (
        classify_precision(hit("803", "Avenida Cidade Jardim", "São Paulo"), ADDRESS) == "address"
    )
    assert classify_precision(hit("803", "Avenida 29", "São Paulo"), ADDRESS) != "address"
    assert classify_precision(hit("", "Avenida Cidade Jardim", "São Paulo"), ADDRESS) == "street"


def test_geocode_rejects_other_municipality_and_never_marks_exact(tmp_path: Path) -> None:
    responses = [
        [hit("803", "Avenida 29", "Rio Claro")],
        [hit("803", "Avenida 29", "Rio Claro")],
        [],
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0))

    fetcher = Fetcher(
        RawCache(tmp_path),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )
    result = geocode(fetcher, ADDRESS)

    assert result.status == "rejected_wrong_locality"
    assert result.latitude is None and not result.is_exact
    assert result.attribution == "© OpenStreetMap contributors"


def test_geocode_keeps_provider_metadata_and_approximate_precision(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[hit("", "Avenida Cidade Jardim", "São Paulo")])

    fetcher = Fetcher(
        RawCache(tmp_path),
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        sleep=lambda _: None,
    )
    result = geocode(fetcher, ADDRESS)

    assert result.status == "matched_approximate"
    assert result.precision == "street" and result.is_exact is False
    assert result.provider.startswith("Nominatim") and result.raw_sha256 and result.fetched_at
    assert json.loads(result.query)["countrycodes"] == "br"


# --- identity -----------------------------------------------------------------


def test_identity_registry_covers_exactly_the_pilot() -> None:
    registry = load_registry(ROOT / "data/reference/identity_registry.yaml")
    pilots = load_pilot_csv(ROOT / "data/staging/pilot_accounts.csv")

    registry.check_accounts(p.account_id for p in pilots)
    assert all(
        e.approval_status == "pending_human_review"
        for account in registry.accounts.values()
        for e in account.entities
    )
    assert registry.accounts["org-itau-bba"].manager_cnpjs() == ()


def test_identity_registry_rejects_bad_or_shared_cnpj() -> None:
    entity = {
        "relation": "primary_manager",
        "relation_evidence": "x",
        "approval_status": "pending_human_review",
    }
    with pytest.raises(ValidationError, match="check digits"):
        IdentityRegistry.model_validate(
            {
                "version": "t",
                "as_of_date": "2026-10-29",
                "accounts": {
                    "org-a": {
                        "primary_cnpj": "20429285000176",
                        "entities": [{**entity, "cnpj": "20429285000176"}],
                    }
                },
            }
        )
    shared = {"primary_cnpj": "19749539000176", "entities": [{**entity, "cnpj": "19749539000176"}]}
    with pytest.raises(ValidationError, match="mapped to"):
        IdentityRegistry.model_validate(
            {
                "version": "t",
                "as_of_date": "2026-10-29",
                "accounts": {"org-a": shared, "org-b": shared},
            }
        )


def test_candidates_are_proposals_by_distinctive_tokens() -> None:
    registered = [
        ("19749539000176", "VERDE ASSET MANAGEMENT S.A.", ""),
        ("55777175000100", "VERDE ASSET AGRO E IMOBILIÁRIO LTDA", ""),
        ("1", "VERDELHO GESTAO LTDA", ""),
    ]
    found = propose_candidates("Verde Asset Management", registered)
    assert [cnpj for cnpj, _ in found] == ["19749539000176", "55777175000100"]


# --- conflicts, privacy and freshness ----------------------------------------


def test_conflicts_compare_floor_sets_phones_and_city_prefix() -> None:
    managers = parse_managers(zip_fixtures("cad_adm_cart_pj.csv"))
    pilots = {p.account_id: p for p in load_pilot_csv(ROOT / "data/staging/pilot_accounts.csv")}

    verde = detect_conflicts(
        pilots["org-verde-asset"],
        ["São Paulo: Avenida Brigadeiro Faria Lima, 3600, 11º andar, CEP 04538-132"],
        [managers["19749539000176"]],
        "2026-10-30",
    )
    assert verde == []

    constellation = detect_conflicts(
        pilots["org-constellation"],
        ["Av. Brigadeiro Faria Lima, 3311, 9º andar — Itaim Bibi, São Paulo/SP"],
        [managers["06182127000155"]],
        "2026-10-30",
    )
    assert {c.rule for c in constellation} == {"official_phone_malformed", "floor_differs"}


def test_review_queue_preserves_human_decisions(tmp_path: Path) -> None:
    managers = parse_managers(zip_fixtures("cad_adm_cart_pj.csv"))
    pilot = next(
        p
        for p in load_pilot_csv(ROOT / "data/staging/pilot_accounts.csv")
        if p.account_id == "org-constellation"
    )
    queue = tmp_path / "conflicts.csv"
    detected = detect_conflicts(pilot, [], [managers["06182127000155"]], "2026-10-30")
    merge_review_queue(queue, detected)

    with queue.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0].update(
        resolution_status="keep_workbook",
        resolved_by="analista",
        resolution_note="telefone confirmado no site",
    )
    with queue.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    again = merge_review_queue(
        queue, detect_conflicts(pilot, [], [managers["06182127000155"]], "2026-10-31")
    )
    assert again[0].resolution_status == "keep_workbook"
    assert again[0].detected_at == "2026-10-30"

    cleared = merge_review_queue(queue, [])
    assert cleared[0].resolution_status == "keep_workbook"


def test_only_institutional_emails_are_kept() -> None:
    assert is_role_email("compliance@verdeasset.com.br")
    assert is_role_email("ol-juridico-societario@btgpactual.com")
    assert not is_role_email("joao.silva@const.com.br")
    assert not is_role_email("razevedo@ibiunainvest.com.br")


def test_freshness_statuses() -> None:
    today = date(2026, 10, 30)
    fresh = check_freshness(SourceRun("cvm_inf_diario", "ok", None, date(2026, 10, 27), 13), today)
    stale = check_freshness(SourceRun("cvm_inf_diario", "ok", None, date(2026, 9, 1), 1), today)
    down = check_freshness(
        SourceRun("bcb_ifdata_cadastro", "unavailable", None, None, 0, "HTTP 500"), today
    )

    assert (fresh.status, fresh.age_days) == ("fresh", 3)
    assert stale.status == "stale"
    assert down.status == "unavailable" and down.detail == "HTTP 500"
