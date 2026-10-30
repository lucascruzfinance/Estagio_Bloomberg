from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from networking_intel.enrichment.cache import RawCache
from networking_intel.enrichment.cvm import (
    normalize_phone,
    parse_daily_report,
    parse_fund_classes,
    parse_managers,
    parse_portfolio_directors,
)
from networking_intel.enrichment.http import Fetcher, SourceUnavailableError, safe_url
from networking_intel.enrichment.sources import SandboxDataError, require_real_source
from tests.prompt3_helpers import zip_fixtures

URL = "https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip"


def make_fetcher(
    tmp_path: Path, handler: httpx.MockTransport, **kwargs: object
) -> tuple[Fetcher, list[float]]:
    sleeps: list[float] = []
    fetcher = Fetcher(
        RawCache(tmp_path / "raw"),
        client=httpx.Client(transport=handler),
        sleep=sleeps.append,
        **kwargs,  # type: ignore[arg-type]
    )
    return fetcher, sleeps


def test_cache_is_write_once_and_deduplicated(tmp_path: Path) -> None:
    cache = RawCache(tmp_path)
    first = cache.store(
        source_id="cvm_cad_adm_cart", url=URL, content=b"abc", http_status=200, suffix=".zip"
    )
    second = cache.store(
        source_id="cvm_cad_adm_cart", url=URL, content=b"abc", http_status=200, suffix=".zip"
    )

    assert first.path == second.path
    assert len(cache.entries()) == 2
    assert not os.access(cache.path_of(first), os.W_OK)
    assert cache.read_bytes(first) == b"abc"


def test_cache_detects_tampering(tmp_path: Path) -> None:
    cache = RawCache(tmp_path)
    artifact = cache.store(
        source_id="cvm_cad_adm_cart", url=URL, content=b"abc", http_status=200, suffix=".zip"
    )
    target = cache.path_of(artifact)
    os.chmod(target, 0o600)
    target.write_bytes(b"tampered")

    with pytest.raises(RuntimeError, match="integrity"):
        cache.read_bytes(artifact)


def test_cache_ttl_controls_reuse(tmp_path: Path) -> None:
    cache = RawCache(tmp_path)
    old = datetime(2026, 1, 1, tzinfo=UTC)
    cache.store(
        source_id="cvm_cad_adm_cart",
        url=URL,
        content=b"x",
        http_status=200,
        suffix=".zip",
        fetched_at=old,
    )

    assert cache.latest("cvm_cad_adm_cart", URL, max_age_seconds=86400, now=old) is not None
    later = old + timedelta(days=2)
    assert cache.latest("cvm_cad_adm_cart", URL, max_age_seconds=86400, now=later) is None


def test_sandbox_sources_never_enter_as_real(tmp_path: Path) -> None:
    with pytest.raises(SandboxDataError):
        require_real_source("anbima_sandbox")
    with pytest.raises(SandboxDataError):
        RawCache(tmp_path).store(
            source_id="anbima_sandbox",
            url="https://x",
            content=b"{}",
            http_status=200,
            suffix=".json",
        )


def test_fetcher_retries_are_bounded_then_succeed(tmp_path: Path) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503 if len(calls) < 3 else 200, content=b"payload")

    fetcher, _ = make_fetcher(tmp_path, httpx.MockTransport(handler))
    artifact = fetcher.fetch("cvm_cad_adm_cart", URL, suffix=".zip")

    assert len(calls) == 3
    assert fetcher.cache.read_bytes(artifact) == b"payload"


def test_fetcher_gives_up_after_max_attempts(tmp_path: Path) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(500)

    fetcher, _ = make_fetcher(tmp_path, httpx.MockTransport(handler))
    with pytest.raises(SourceUnavailableError, match="HTTP 500 after retries"):
        fetcher.fetch("cvm_cad_adm_cart", URL)
    assert len(calls) == 3
    assert fetcher.cache.entries() == []


def test_fetcher_does_not_retry_client_errors(tmp_path: Path) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(404)

    fetcher, _ = make_fetcher(tmp_path, httpx.MockTransport(handler))
    with pytest.raises(SourceUnavailableError, match="HTTP 404"):
        fetcher.fetch("cvm_cad_adm_cart", URL)
    assert len(calls) == 1


def test_fetcher_uses_cache_and_offline_mode(tmp_path: Path) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(200, content=b"ok")

    fetcher, _ = make_fetcher(tmp_path, httpx.MockTransport(handler))
    fetcher.fetch("cvm_cad_adm_cart", URL)
    fetcher.fetch("cvm_cad_adm_cart", URL)
    assert len(calls) == 1

    offline, _ = make_fetcher(tmp_path, httpx.MockTransport(handler), offline=True)
    offline.fetch("cvm_cad_adm_cart", URL, max_age_seconds=0)
    assert len(calls) == 1
    with pytest.raises(SourceUnavailableError, match="offline"):
        offline.fetch("cvm_cad_adm_cart", URL + "?other")


def test_fetcher_rate_limits_per_source(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    fetcher, sleeps = make_fetcher(tmp_path, httpx.MockTransport(handler))
    url = "https://nominatim.openstreetmap.org/search"
    fetcher.fetch("osm_nominatim", url, params={"q": "a"})
    fetcher.fetch("osm_nominatim", url, params={"q": "b"})

    assert sleeps and sleeps[0] > 1.0


def test_logged_urls_drop_query_strings() -> None:
    url = "https://nominatim.openstreetmap.org/search?q=Rua+X+123&email=a@b.c"
    assert safe_url(url) == "https://nominatim.openstreetmap.org/search"


def test_parse_managers_normalizes_official_contacts() -> None:
    managers = parse_managers(zip_fixtures("cad_adm_cart_pj.csv"))

    verde = managers["19749539000176"]
    assert verde.phone == "+551149358500"
    assert verde.postal_code == "04538132"
    assert verde.is_active
    assert verde.address_line and "CEP 04538-132" in verde.address_line
    constellation = managers["06182127000155"]
    assert constellation.phone is None
    assert constellation.phone_raw == "11 145010025"
    assert not managers["30306294000145"].is_active


def test_phone_normalization_handles_country_code_in_ddd() -> None:
    assert normalize_phone("55", "1135723700") == "+551135723700"
    assert normalize_phone("55", "113572370") is None
    assert normalize_phone("11", "987654321") == "+5511987654321"


def test_portfolio_directors_are_minimal() -> None:
    directors = parse_portfolio_directors(
        zip_fixtures("cad_adm_cart_diretor.csv"), ["19749539000176"]
    )
    assert directors == {"19749539000176": ["Diretor Exemplo A"]}


def test_fund_mapping_is_exact_cnpj_join_without_name_matching() -> None:
    content = zip_fixtures("registro_fundo.csv", "registro_classe.csv")
    classes = parse_fund_classes(content, ["19749539000176"])

    assert {c.class_cnpj for c in classes} == {"11111111000191", "22222222000191"}
    assert all(c.manager_cnpj == "19749539000176" for c in classes)
    fic = next(c for c in classes if c.class_cnpj == "22222222000191")
    assert fic.is_fund_of_funds
    assert fic.anbima_classification == "Multimercados Macro"


def test_daily_report_is_filtered_to_mapped_classes() -> None:
    frame = parse_daily_report(zip_fixtures("inf_diario_fi_202610.csv"), ["11111111000191"])

    assert frame.height == 2
    assert set(frame["class_cnpj"]) == {"11111111000191"}
    assert frame["quota"].to_list() == [10.0, 10.01]
    assert frame["subclass_id"].to_list() == ["", ""]
