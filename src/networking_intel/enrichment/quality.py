from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from networking_intel.enrichment.sources import get_source


@dataclass(frozen=True)
class SourceRun:
    source_id: str
    status: str  # ok | unavailable | not_used
    fetched_at: str | None
    data_as_of: date | None
    artifacts: int
    detail: str = ""


@dataclass(frozen=True)
class Freshness:
    source_id: str
    title: str
    status: str  # fresh | stale | unavailable | not_used
    data_as_of: str | None
    fetched_at: str | None
    age_days: int | None
    max_age_days: int
    artifacts: int
    detail: str


def check_freshness(run: SourceRun, today: date) -> Freshness:
    spec = get_source(run.source_id)
    max_age_days = spec.max_age.days
    if run.status != "ok":
        return Freshness(
            run.source_id,
            spec.title,
            run.status,
            None,
            run.fetched_at,
            None,
            max_age_days,
            run.artifacts,
            run.detail,
        )
    reference = run.data_as_of or (
        datetime.fromisoformat(run.fetched_at).date() if run.fetched_at else None
    )
    age = (today - reference).days if reference else None
    status = "fresh" if age is not None and age <= max_age_days else "stale"
    return Freshness(
        run.source_id,
        spec.title,
        status,
        reference.isoformat() if reference else None,
        run.fetched_at,
        age,
        max_age_days,
        run.artifacts,
        run.detail,
    )


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _brl_mm(value: float | None) -> str:
    return "—" if value is None else f"R$ {value / 1e6:,.0f} mi".replace(",", ".")


def write_reports(output_dir: Path, docs_path: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "quality_report.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    docs_path.parent.mkdir(parents=True, exist_ok=True)
    docs_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, docs_path


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prompt 3 — Relatório de enriquecimento e qualidade",
        "",
        f"Execução: {payload['run_at']}  ",
        f"Data de referência dos fundos: {payload['fund_reference_date'] or '—'}  ",
        f"Versão: {payload['version']}",
        "",
        "> Retornos são variações de cota dos fundos (líquidas de taxas, para o cotista). "
        "Não representam receita nem lucro da gestora.",
        "",
        "## Freshness das fontes",
        "",
        "| Fonte | Status | Dados de | Idade (dias) | Limite | Artefatos | Detalhe |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for item in payload["freshness"]:
        lines.append(
            f"| {item['title']} | {item['status']} | {item['data_as_of'] or '—'} | "
            f"{item['age_days'] if item['age_days'] is not None else '—'} | "
            f"{item['max_age_days']} | {item['artifacts']} | {item['detail'] or ''} |"
        )
    lines += [
        "",
        "## Cobertura por conta",
        "",
        "| Conta | CNPJ principal | Entidades | Endereço oficial | Geo exato | "
        "Classes ativas | c/ Informe | Retorno 12m comparável | PL (não-FIC) | "
        "Captação líq. 12m | Conflitos abertos |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for acc in payload["accounts"]:
        lines.append(
            f"| {acc['canonical_name']} | {acc['primary_cnpj_formatted']} | "
            f"{acc['entities_found']}/{acc['entities_registered']} | "
            f"{'sim' if acc['official_address'] else 'não'} | "
            f"{acc['geocode_precision'] or '—'} | {acc['active_classes']} | "
            f"{acc['classes_with_daily_report']} | {_pct(acc['comparable_12m_share'])} | "
            f"{_brl_mm(acc['nav_brl_non_fic'])} | {_brl_mm(acc['net_flow_12m_brl_non_fic'])} | "
            f"{acc['open_conflicts']} |"
        )
    lines += ["", "## Lacunas por conta", ""]
    for acc in payload["accounts"]:
        gaps = acc["gaps"] or ["nenhuma lacuna crítica nas fontes deste prompt"]
        lines.append(f"- **{acc['canonical_name']}**: " + "; ".join(gaps) + ".")
    lines += [
        "",
        "## Regras aplicadas",
        "",
        *[f"- {rule}" for rule in payload["rules"]],
        "",
        "## Revisão humana",
        "",
        f"- Fila de conflitos: `{payload['review_queue']}` "
        f"({payload['conflicts_pending']} pendentes de {payload['conflicts_total']}).",
        "- Registro de identidade: `data/reference/identity_registry.yaml` "
        "(todas as entidades em `pending_human_review`).",
        "- Para resolver, preencha `resolution_status`, `resolved_by`, `resolved_at` e "
        "`resolution_note`; a próxima execução preserva a decisão.",
        "",
    ]
    return "\n".join(lines)


def as_dict(item: Freshness) -> dict[str, Any]:
    return asdict(item)
