"""Banco Central IF.data (Olinda OData): institution register and report values.

The service answers HTTP 200 with an empty ``value`` list for quarters not yet
published (202609 on 30/10/2026). An empty answer is a missing period, never data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from networking_intel.enrichment.cache import RawArtifact
from networking_intel.enrichment.http import Fetcher, SourceUnavailableError

BASE = "https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/"
# Prudential conglomerates and independent institutions.
PRUDENTIAL = 1
# Report 1 (Resumo) for size and growth; report 4 (DRE) for the trading/FX/fee mix.
SUMMARY_REPORT = "1"
INCOME_REPORT = "4"
INCOME_LINES = (
    "Rendas de Títulos e Valores Mobiliários",
    "Resultado com Derivativos",
    "Rendas de Operações de Crédito",
    "Resultado de Intermediação Financeira",
    "Rendas de Tarifas Bancárias",
    "Outras Rendas de Prestação de Serviços",
    "Despesas de Pessoal",
    "Lucro Líquido",
)
# Probing is cheap; re-check unpublished quarters weekly instead of trusting a 200-day cache.
PROBE_MAX_AGE_SECONDS = 7 * 86400


class IfDataUnavailableError(RuntimeError):
    def __init__(self, reasons: list[str]) -> None:
        super().__init__("; ".join(reasons))
        self.reasons = reasons


def cadastro_url(period: str) -> str:
    # OData alias parameters ('@', '$') must stay unescaped in the query string.
    return f"{BASE}IfDataCadastro(AnoMes=@AnoMes)?@AnoMes={period}&$format=json"


def valores_url(period: str, report: str, institution_type: int = PRUDENTIAL) -> str:
    return (
        f"{BASE}IfDataValores(AnoMes=@AnoMes,TipoInstituicao=@TipoInstituicao,"
        f"Relatorio=@Relatorio)?@AnoMes={period}&@TipoInstituicao={institution_type}"
        f"&@Relatorio='{report}'&$format=json"
    )


def candidate_quarters(today: date, count: int = 8) -> list[str]:
    """Quarter-end periods (YYYYMM), newest first, from the last quarter already closed."""
    year, month = today.year, today.month - (today.month - 1) % 3 - 1
    if month <= 0:
        year, month = year - 1, month + 12
    periods = []
    for _ in range(count):
        periods.append(f"{year:04d}{month:02d}")
        month -= 3
        if month <= 0:
            year, month = year - 1, month + 12
    return periods


def rows_of(fetcher: Fetcher, artifact: RawArtifact) -> list[dict[str, Any]]:
    payload = json.loads(fetcher.cache.read_bytes(artifact))
    return list(payload.get("value") or [])


@dataclass(frozen=True)
class Period:
    period: str
    artifact: RawArtifact
    rows: list[dict[str, Any]]


def latest_periods(
    fetcher: Fetcher,
    source_id: str,
    url_for: Any,
    today: date,
    *,
    wanted: int,
) -> tuple[list[Period], list[str]]:
    """Newest non-empty periods; empty or failing quarters are skipped and reported."""
    found: list[Period] = []
    skipped: list[str] = []
    for period in candidate_quarters(today):
        try:
            artifact = fetcher.fetch(
                source_id,
                url_for(period),
                suffix=".json",
                max_age_seconds=PROBE_MAX_AGE_SECONDS if not found else None,
            )
        except SourceUnavailableError as error:
            skipped.append(f"{period}: {error.reason}")
            continue
        rows = rows_of(fetcher, artifact)
        if not rows:
            skipped.append(f"{period}: resposta vazia (período ainda não publicado)")
            continue
        found.append(Period(period, artifact, rows))
        if len(found) == wanted:
            break
    return found, skipped


def latest_cadastro(fetcher: Fetcher, today: date) -> tuple[Period, list[str]]:
    found, skipped = latest_periods(fetcher, "bcb_ifdata_cadastro", cadastro_url, today, wanted=1)
    if not found:
        raise IfDataUnavailableError(skipped)
    return found[0], skipped


def institutions(rows: list[dict[str, Any]], states: frozenset[str]) -> list[dict[str, Any]]:
    """Active institutions and conglomerates headquartered in the given states."""
    return [
        {
            "cod_inst": row["CodInst"],
            "name": " ".join(str(row["NomeInstituicao"]).split()),
            "is_conglomerate": str(row["CodInst"]).startswith("C"),
            "tcb": row.get("Tcb"),
            "td": row.get("Td"),
            "tc": row.get("Tc"),
            "segment": row.get("SegmentoTb"),
            "sr": row.get("Sr"),
            "state": row.get("Uf"),
            "city": row.get("Municipio"),
            "financial_conglomerate": row.get("CodConglomeradoFinanceiro"),
            "prudential_conglomerate": row.get("CodConglomeradoPrudencial"),
            "leader_cnpj_root": row.get("CnpjInstituicaoLider"),
            "activity_start": row.get("DataInicioAtividade"),
            "period": row.get("Data"),
        }
        for row in rows
        if row.get("Situacao") == "A" and row.get("Uf") in states
    ]


def clean_column(name: str) -> str:
    """'Resultado com Derivativos \\n(i)' -> 'Resultado com Derivativos'."""
    return " ".join(str(name).split("\n")[0].split())


def report_values(
    rows: list[dict[str, Any]], cod_insts: set[str], *, lines: tuple[str, ...] | None = None
) -> list[dict[str, Any]]:
    """Rows of the wanted institutions; exact duplicates in the BCB file (seen in 202509)
    are dropped by (institution, period, report, account)."""
    out = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in rows:
        if row["CodInst"] not in cod_insts:
            continue
        key = (
            row["CodInst"],
            str(row["AnoMes"]),
            str(row["NumeroRelatorio"]),
            str(row.get("Conta") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        column = clean_column(row["NomeColuna"])
        if lines is not None and column not in lines:
            continue
        out.append(
            {
                "cod_inst": row["CodInst"],
                "period": str(row["AnoMes"]),
                "report": str(row["NumeroRelatorio"]),
                "report_name": row["NomeRelatorio"],
                "group_name": row.get("Grupo") or "",
                "account_code": str(row.get("Conta") or ""),
                "metric": column,
                "value": row.get("Saldo"),
            }
        )
    return out
