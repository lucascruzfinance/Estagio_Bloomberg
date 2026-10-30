from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

import httpx
import polars as pl
import pytest

from networking_intel.enrichment.cache import RawCache
from networking_intel.enrichment.http import Fetcher
from networking_intel.enrichment.identity import RegistryEntity
from networking_intel.enrichment.pipeline import RunContext, try_ifdata
from networking_intel.universe import ifdata
from networking_intel.universe.curated import CuratedAccount
from networking_intel.universe.fund_docs import cda_category
from networking_intel.universe.geo import building_key, centre_of
from networking_intel.universe.groups import name_suggestions, resolve_groups
from networking_intel.universe.pipeline import reconcile_counts
from networking_intel.universe.series import _manager_monthly, trim_daily

ROOT = Path(__file__).resolve().parents[1]


def test_centres_use_avenue_then_neighbourhood() -> None:
    assert (
        centre_of("SP", "SÃO PAULO", "AV. BRIG. FARIA LIMA, 3477", "ITAIM BIBI")[0] == "Faria Lima"
    )
    assert centre_of("SP", "São Paulo", "Rua Desconhecida 10", "Itaim Bibi") == (
        "JK / Vila Olímpia",
        "district",
    )
    assert centre_of("RJ", "RIO DE JANEIRO", "AV. ATAULFO DE PAIVA 153", "LEBLON")[0] == (
        "Leblon / Ipanema (RJ)"
    )
    assert centre_of("SP", "OSASCO", "NUCLEO CIDADE DE DEUS", "VILA YARA")[0] == "Osasco"
    assert centre_of("PE", "RECIFE", "Av. Boa Viagem 1", "Boa Viagem") == (None, None)


def test_building_key_reads_door_number_from_complement_but_never_a_floor() -> None:
    key = building_key("AV. BRIGADEIRO FARIA LIMA", "SÃO PAULO", "SP", "4440, 15 ANDAR")
    assert key == "AVENIDA BRIGADEIRO FARIA LIMA|4440|SAO PAULO|SP"
    assert building_key("AV. BRIGADEIRO FARIA LIMA", "SÃO PAULO", "SP", "14° andar") is None
    assert building_key("AVENIDA CHUCRI ZAIDAN", "SÃO PAULO", "SP", "14 E 15º ANDAR") is None
    assert building_key("AV BRIG FARIA LIMA, 3477", "SÃO PAULO", "SP", "14 ANDAR") == building_key(
        "Avenida Brigadeiro Faria Lima 3477", "SÃO PAULO", "SP"
    )


def _ifdata_fetcher(tmp_path: Path, published: set[str]) -> Fetcher:
    def handler(request: httpx.Request) -> httpx.Response:
        period = next((p for p in published if p in str(request.url)), None)
        rows = [{"CodInst": "C1", "Uf": "SP", "Situacao": "A", "NomeInstituicao": "X"}]
        return httpx.Response(200, json={"value": rows if period else []})

    return Fetcher(
        RawCache(tmp_path / "raw"), client=httpx.Client(transport=httpx.MockTransport(handler))
    )


def test_ifdata_skips_unpublished_quarter_answered_with_empty_list(tmp_path: Path) -> None:
    assert ifdata.candidate_quarters(date(2026, 10, 30))[:2] == ["202609", "202606"]
    fetcher = _ifdata_fetcher(tmp_path, {"202606"})
    found, skipped = ifdata.latest_cadastro(fetcher, date(2026, 10, 30))
    assert found.period == "202606"
    assert skipped == ["202609: resposta vazia (período ainda não publicado)"]


def test_enrichment_reports_ifdata_period_and_unavailability(tmp_path: Path) -> None:
    ok = try_ifdata(
        RunContext(_ifdata_fetcher(tmp_path / "a", {"202606"}), date(2026, 10, 30), "now")
    )
    assert ok.status == "ok" and "202606" in (ok.detail or "")
    down = try_ifdata(RunContext(_ifdata_fetcher(tmp_path / "b", set()), date(2026, 10, 30), "now"))
    assert down.status == "unavailable"


def test_cda_categories() -> None:
    assert cda_category("4", "Mercado Futuro - Posições compradas") == "derivatives"
    assert cda_category("8", "Opções - Posições lançadas") == "derivatives"
    assert cda_category("4", "Debêntures") == "private_credit"
    assert cda_category("4", "Ações") == "equities"
    assert cda_category("7", "Investimento no Exterior") == "foreign"
    assert cda_category("1", "Operações Compromissadas") == "public_bonds_repo"
    assert cda_category("8", "Disponibilidades") == "cash"
    assert cda_category("CONFID", None) == "confidential"


def test_manager_month_uses_class_row_or_subclass_sum_never_both() -> None:
    day = date(2026, 9, 30)
    frame = pl.DataFrame(
        {
            "manager_cnpj": ["M"] * 4,
            "class_cnpj": ["A", "A", "B", "B"],
            "subclass_id": ["", "S1", "S1", "S2"],
            "date": [day] * 4,
            "nav_brl": [100.0, 100.0, 30.0, 20.0],
            "inflow_brl": [10.0, 10.0, 1.0, 2.0],
            "outflow_brl": [0.0, 0.0, 0.0, 1.0],
            "investors": [5, 5, 1, 2],
        }
    )
    row = _manager_monthly(frame, date(2026, 9, 1), "sha").row(0, named=True)
    assert row["nav_end_brl"] == 150.0  # A: class row only; B: 30 + 20
    assert row["inflow_brl"] == 13.0
    assert row["classes_reporting"] == 2


def test_daily_snapshot_keeps_only_material_recent_series() -> None:
    frame = pl.DataFrame(
        {
            "class_cnpj": ["A", "A", "B", "C"],
            "subclass_id": ["", "", "", ""],
            "date": [date(2026, 9, 1), date(2026, 10, 28), date(2026, 10, 28), date(2026, 6, 1)],
            "nav_brl": [1e9, 9e7, 1e6, 1e9],
        }
    )
    kept = trim_daily(frame, min_nav_brl=5e7, recent_days=45)
    assert sorted(set(kept["class_cnpj"])) == ["A"]


def test_groups_prefer_curated_then_central_bank_then_cnpj_root() -> None:
    entities = {
        "11111111000191": "Curada Gestora",
        "22222222000191": "Banco Exemplo",
        "33333333000191": "Kapitalo Nexo",
        "44444444000191": "Kapitalo Ciclo",
    }
    curated = [
        CuratedAccount(
            account_key="acc",
            display_name="Conta",
            wave="wave2",
            side="buy_side",
            segment="x",
            rationale="x",
            primary_cnpj="11111111000191",
            entities=(
                RegistryEntity(
                    cnpj="11111111000191",
                    relation="primary_manager",
                    relation_evidence="teste",
                    approval_status="pending_human_review",
                ),
            ),
        )
    ]
    institutions = [
        {
            "cod_inst": "C0000001",
            "name": "EXEMPLO - PRUDENCIAL",
            "is_conglomerate": True,
            "prudential_conglomerate": "C0000001",
        },
        {
            "cod_inst": "22222222",
            "name": "BANCO EXEMPLO",
            "is_conglomerate": False,
            "prudential_conglomerate": "C0000001",
        },
    ]
    groups = resolve_groups(entities, curated, institutions)
    assert groups["11111111000191"].basis == "curated_registry"
    assert groups["22222222000191"].group_key == "ifdata:C0000001"
    assert groups["22222222000191"].group_name == "EXEMPLO"
    assert groups["33333333000191"].group_key == "root:33333333"
    suggestions = name_suggestions(groups, entities)
    assert [s["brand_token"] for s in suggestions] == ["kapitalo"]
    # Suggestions never merge groups.
    assert groups["33333333000191"].group_key != groups["44444444000191"].group_key


@pytest.mark.skipif(
    not (ROOT / "data/raw/manifest.jsonl").exists(), reason="raw cache not present (fresh clone)"
)
def test_universe_counts_reconcile_with_raw_registries() -> None:
    raw = reconcile_counts(ROOT / "data/raw")
    with (ROOT / "data/universe/entities.csv").open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    in_scope = [r for r in rows if r["centre"]]
    managers = [
        r
        for r in in_scope
        if "gestora" in r["kinds"].split(";") and "Gestor" in r["registration_category"]
    ]
    intermediaries = [r for r in in_scope if r["source_id"] == "cvm_cad_intermed"] + [
        r
        for r in in_scope
        if r["source_id"] == "cvm_cad_adm_cart"
        and set(r["kinds"].split(";")) - {"gestora", "administrador_fiduciario"}
    ]
    assert len(managers) == raw["managers"]
    assert len(intermediaries) == raw["intermediaries"]
    report = json.loads((ROOT / "data/universe/quality_report.json").read_text(encoding="utf-8"))
    assert report["counts"]["entities"] == len(rows)
