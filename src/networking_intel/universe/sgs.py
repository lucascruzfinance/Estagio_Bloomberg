"""Banco Central SGS benchmark series (CDI, IPCA, PTAX).

SGS 7 (Ibovespa) stopped in 2019 and is deliberately absent: equity funds are
compared with their peer median instead (Prompt 9).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime

from networking_intel.enrichment.cache import RawArtifact
from networking_intel.enrichment.http import Fetcher

SGS_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?formato=json&dataInicial={start}&dataFinal={end}"
)


@dataclass(frozen=True)
class SeriesSpec:
    code: int
    key: str
    name: str
    unit: str


SERIES = (
    SeriesSpec(12, "cdi", "CDI — taxa diária", "percent_per_day"),
    SeriesSpec(433, "ipca", "IPCA — variação mensal", "percent_per_month"),
    SeriesSpec(1, "ptax_usd", "Dólar comercial PTAX — venda", "brl_per_usd"),
)


def fetch_series(
    fetcher: Fetcher, spec: SeriesSpec, start: date, end: date
) -> tuple[RawArtifact, list[dict[str, object]]]:
    url = SGS_URL.format(
        code=spec.code, start=start.strftime("%d/%m/%Y"), end=end.strftime("%d/%m/%Y")
    )
    artifact = fetcher.fetch("bcb_sgs", url, suffix=".json")
    return artifact, parse_series(fetcher.cache.read_bytes(artifact), spec, artifact.sha256)


def parse_series(content: bytes, spec: SeriesSpec, raw_sha256: str) -> list[dict[str, object]]:
    rows = []
    for item in json.loads(content):
        rows.append(
            {
                "series_key": spec.key,
                "sgs_code": spec.code,
                "date": datetime.strptime(item["data"], "%d/%m/%Y").date(),
                "value": float(item["valor"]),
                "unit": spec.unit,
                "raw_sha256": raw_sha256,
            }
        )
    return rows
