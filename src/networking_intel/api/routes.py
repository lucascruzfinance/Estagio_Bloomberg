from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from networking_intel.api import API_VERSION, repository
from networking_intel.api.db import get_session
from networking_intel.api.errors import ApiError
from networking_intel.api.schemas import (
    ACCOUNT_ID_PATTERN,
    CNPJ_PATTERN,
    UNIT_KEY_PATTERN,
    AccountDetail,
    AccountSummary,
    BusinessUnitOut,
    Comparison,
    ConflictOut,
    DataQuality,
    DensityGrid,
    FundPerformance,
    FundRow,
    Health,
    Meta,
    OfficeFeatureCollection,
    Page,
    Problem,
    Readiness,
    ScoreExplanation,
    ScoreRow,
    SearchHit,
    SignalOut,
)

SessionDep = Annotated[Session, Depends(get_session)]
Order = Annotated[Literal["asc", "desc"], Query(description="Direção da ordenação.")]
PageNumber = Annotated[int, Query(ge=1, le=10_000, description="Página, a partir de 1.")]
PageSize = Annotated[int, Query(ge=1, le=200, description="Itens por página (máx. 200).")]
AccountFilter = Annotated[
    str | None, Query(pattern=ACCOUNT_ID_PATTERN, description="Ex.: org-verde-asset.")
]
Tier = Literal[
    "Prioridade agora",
    "Desenvolver relacionamento",
    "Oportunidade tática",
    "Monitorar",
    "Evidência insuficiente",
    "Fit alto — timing desconhecido",
    "Fit baixo — timing desconhecido",
]

ERRORS: dict[int | str, dict[str, Any]] = {
    422: {"model": Problem, "description": "Parâmetro inválido (RFC 7807)."},
    429: {"model": Problem, "description": "Rate limit local excedido; ver Retry-After."},
    500: {"model": Problem, "description": "Erro interno sem detalhes sensíveis."},
}
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    **ERRORS,
    404: {"model": Problem, "description": "Recurso inexistente."},
}

ops = APIRouter(tags=["operação"])
api = APIRouter(prefix="/api/v1", responses=ERRORS)


def _page(
    data: list[Any], total: int, page: int, size: int, sort: str | None, order: str | None
) -> dict[str, Any]:
    return {
        "data": data,
        "meta": {"page": page, "page_size": size, "total": total, "sort": sort, "order": order},
    }


def _bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in value.split(","))
    except ValueError as error:
        raise ApiError(
            422, "bbox deve ser 'min_lon,min_lat,max_lon,max_lat'.", code="validation"
        ) from error
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise ApiError(422, "bbox fora dos limites WGS84 ou invertido.", code="validation")
    return min_lon, min_lat, max_lon, max_lat


# ------------------------------------------------------------------ operation


@ops.get("/health", response_model=Health, summary="Liveness (não consulta o banco)")
def health() -> dict[str, str]:
    return {"status": "ok"}


@ops.get(
    "/ready",
    response_model=Readiness,
    summary="Readiness: banco, migração e dados carregados",
    responses={503: {"model": Readiness}},
)
def ready(request: Request) -> Any:
    from fastapi.responses import JSONResponse

    checks: dict[str, Any] = {}
    try:
        with request.app.state.session_factory() as session:
            checks["database"] = session.execute(text("SELECT 1")).scalar_one() == 1
            checks["migration"] = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            checks["migration_is_head"] = checks["migration"] == request.app.state.migration_head
            checks["score_run"] = (
                session.execute(text("SELECT count(*) FROM score_runs")).scalar_one() > 0
            )
            checks["quality_report"] = (
                session.execute(text("SELECT count(*) FROM quality_reports")).scalar_one() > 0
            )
    except Exception as error:  # report the failure class only — never connection strings
        checks["database"] = False
        checks["error"] = type(error).__name__
    ok = all(
        checks.get(k) is True
        for k in ("database", "migration_is_head", "score_run", "quality_report")
    )
    body = {"status": "ready" if ok else "not_ready", "checks": checks}
    return JSONResponse(body, status_code=200 if ok else 503)


# ------------------------------------------------------------------------ meta


@api.get(
    "/meta", response_model=Meta, tags=["meta"], summary="Versões, datas de referência e convenções"
)
def get_meta(session: SessionDep, request: Request) -> dict[str, Any]:
    info = repository.meta(session)
    demo = request.app.state.data_mode == "demo"
    reference = info["fund_reference_date"]
    return {
        "api_version": API_VERSION,
        **info,
        "data_mode": request.app.state.data_mode,
        "data_note": (
            f"Base de demonstração congelada (dados públicos até {reference}); "
            "não há atualização ao vivo."
            if demo
            else "Dados carregados pelo pipeline; atualize com o enriquecimento e a carga."
        ),
        "disclaimer": "Apoio à preparação de contas: não é probabilidade de compra nem "
        "recomendação automática. Fit, timing e confiança são saídas separadas.",
        "conventions": {
            "money": "BRL (reais), sem escala.",
            "returns": "Fração decimal (0.05 = 5%); retorno do fundo, não lucro da gestora.",
            "scores": "0-100; point=null quando não há evidência; lower/upper = faixa dos ausentes.",
            "dates": "ISO 8601; timestamps com fuso.",
            "null": "Não observado — nunca equivale a zero.",
            "coordinates": "WGS84 [longitude, latitude]; is_exact só com número de porta conferido.",
        },
        "attributions": [repository.ATTRIBUTION_CVM, repository.ATTRIBUTION_OSM],
    }


@api.get(
    "/search",
    response_model=list[SearchHit],
    tags=["busca"],
    summary="Busca canônica por nome, alias, razão social ou CNPJ",
)
def search(
    session: SessionDep,
    q: Annotated[
        str, Query(min_length=2, max_length=80, description="Texto livre ou CNPJ (≥ 8 dígitos).")
    ],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[dict[str, Any]]:
    return repository.search(session, q, limit)


# -------------------------------------------------------------------- accounts


@api.get(
    "/accounts",
    response_model=Page[AccountSummary],
    tags=["contas"],
    summary="Contas do piloto com melhor unidade pontuada",
)
def list_accounts(
    session: SessionDep,
    q: Annotated[
        str | None,
        Query(min_length=2, max_length=80, description="Busca por nome/alias normalizado."),
    ] = None,
    institution_type: Annotated[str | None, Query(max_length=64)] = None,
    tier: Tier | None = None,
    state: Annotated[
        str | None, Query(pattern=r"^[A-Z]{2}$", description="UF da sede (CVM).")
    ] = None,
    sort: Literal[
        "priority", "fit", "timing", "confidence", "rank", "name", "nav", "net_flow"
    ] = "priority",
    order: Order = "desc",
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> dict[str, Any]:
    data, total = repository.list_accounts(
        session,
        q=q,
        institution_type=institution_type,
        tier=tier,
        state=state,
        sort=sort,
        order=order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return _page(data, total, page, page_size, sort, order)


@api.get(
    "/accounts/{account_id}",
    response_model=AccountDetail,
    tags=["contas"],
    summary="Account 360",
    responses=NOT_FOUND,
)
def get_account(
    session: SessionDep,
    account_id: Annotated[str, Path(pattern=ACCOUNT_ID_PATTERN)],
) -> dict[str, Any]:
    detail = repository.account_detail(session, account_id)
    if detail is None:
        raise ApiError(404, f"Conta {account_id} não existe no piloto.", code="not-found")
    return detail


@api.get(
    "/business-units",
    response_model=list[BusinessUnitOut],
    tags=["contas"],
    summary="Mesas/áreas (bancos) com score",
)
def list_business_units(
    session: SessionDep, account_id: AccountFilter = None
) -> list[dict[str, Any]]:
    return repository.list_business_units(session, account_id)


# ---------------------------------------------------------------------- scores


@api.get(
    "/scores",
    response_model=Page[ScoreRow],
    tags=["scores"],
    summary="Ranking explicável (última rodada)",
)
def list_scores(
    session: SessionDep,
    tier: Tier | None = None,
    evidence_mode: Literal["observed", "assumption"] | None = None,
    account_id: AccountFilter = None,
    institution_type: Annotated[str | None, Query(max_length=64)] = None,
    sort: Literal["rank", "priority", "fit", "timing", "confidence", "name"] = "rank",
    order: Order = "asc",
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> dict[str, Any]:
    data, total = repository.list_scores(
        session,
        tier=tier,
        evidence_mode=evidence_mode,
        account_id=account_id,
        institution_type=institution_type,
        sort=sort,
        order=order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return _page(data, total, page, page_size, sort, order)


@api.get(
    "/scores/{unit_key}/explanation",
    response_model=ScoreExplanation,
    tags=["scores"],
    summary="Fatores, contribuições, evidências e limitações de uma unidade",
    responses=NOT_FOUND,
)
def get_explanation(
    session: SessionDep,
    unit_key: Annotated[
        str, Path(pattern=UNIT_KEY_PATTERN, description="Ex.: org-btg-pactual:asset-management.")
    ],
) -> dict[str, Any]:
    explanation = repository.score_explanation(session, unit_key)
    if explanation is None:
        raise ApiError(404, f"Unidade {unit_key} sem score na rodada atual.", code="not-found")
    return explanation


@api.get(
    "/comparisons",
    response_model=Comparison,
    tags=["scores"],
    summary="Comparar 2 a 5 unidades",
    responses=NOT_FOUND,
)
def compare(
    session: SessionDep,
    units: Annotated[
        str, Query(description="unit_keys separados por vírgula (2 a 5).", max_length=600)
    ],
) -> dict[str, Any]:
    keys = list(dict.fromkeys(part.strip() for part in units.split(",") if part.strip()))
    import re

    if not 2 <= len(keys) <= 5 or not all(re.match(UNIT_KEY_PATTERN, k) for k in keys):
        raise ApiError(422, "Informe de 2 a 5 unit_keys válidos e distintos.", code="validation")
    rows = repository.scores_for_units(session, keys)
    found = {row["unit_key"] for row in rows}
    if missing := [k for k in keys if k not in found]:
        raise ApiError(404, f"Sem score para: {', '.join(missing)}.", code="not-found")
    ordered = sorted(rows, key=lambda r: keys.index(r["unit_key"]))
    factors: dict[str, dict[str, Any]] = {}
    for row in ordered:
        explanation = row["explanation"]
        contributions = {
            "fit": explanation.get("fit_contributions", {}),
            "timing": explanation.get("timing_contributions", {}),
        }
        for factor in explanation["factors"]:
            entry = factors.setdefault(
                factor["key"],
                {
                    "key": factor["key"],
                    "group": factor["group"],
                    "label": factor["label"],
                    "values": {},
                },
            )
            entry["values"][row["unit_key"]] = {
                "value": factor["value"],
                "status": factor["status"],
                "points": contributions[factor["group"]].get(factor["key"]),
            }
    modes = {row["evidence_mode"] for row in ordered}
    warnings = []
    if len(modes) > 1:
        warnings.append("Comparação mistura unidades observadas e mesas pontuadas por premissa.")
    if any(row["timing_point"] is None for row in ordered):
        warnings.append("Ao menos uma unidade não tem timing avaliável.")
    return {
        "units": [repository.score_row(r) for r in ordered],
        "factors": list(factors.values()),
        "warnings": warnings,
    }


# ----------------------------------------------------------------------- funds


@api.get(
    "/funds",
    response_model=Page[FundRow],
    tags=["fundos"],
    summary="Classes/subclasses com métricas de retorno e fluxo",
)
def list_funds(
    session: SessionDep,
    account_id: AccountFilter = None,
    unit_key: Annotated[str | None, Query(pattern=UNIT_KEY_PATTERN)] = None,
    classification: Annotated[
        str | None, Query(max_length=64, description="Classificação CVM, ex.: Multimercado.")
    ] = None,
    active: bool | None = True,
    fund_of_funds: bool | None = None,
    exclusive: bool | None = None,
    with_metrics: bool = False,
    q: Annotated[
        str | None,
        Query(min_length=2, max_length=80, description="Nome (ILIKE) ou CNPJ da classe."),
    ] = None,
    sort: Literal[
        "nav",
        "return_12m",
        "return_ytd",
        "net_flow_12m",
        "volatility",
        "drawdown",
        "name",
        "constitution_date",
    ] = "nav",
    order: Order = "desc",
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> dict[str, Any]:
    data, total = repository.list_funds(
        session,
        account_id=account_id,
        unit_key=unit_key,
        classification=classification,
        active=active,
        fund_of_funds=fund_of_funds,
        exclusive=exclusive,
        with_metrics=with_metrics,
        q=q,
        sort=sort,
        order=order,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return _page(data, total, page, page_size, sort, order)


@api.get(
    "/funds/{class_cnpj}/performance",
    response_model=FundPerformance,
    tags=["fundos"],
    summary="Série diária de cota, PL e fluxo (CVM Informe Diário)",
    responses=NOT_FOUND,
)
def get_performance(
    session: SessionDep,
    class_cnpj: Annotated[
        str, Path(pattern=CNPJ_PATTERN, description="CNPJ da classe, 14 dígitos.")
    ],
    subclass_id: Annotated[str, Query(max_length=32, pattern=r"^[A-Za-z0-9]*$")] = "",
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    if start and end and start > end:
        raise ApiError(422, "start deve ser anterior a end.", code="validation")
    performance = repository.fund_performance(session, class_cnpj, subclass_id, start, end)
    if performance is None:
        raise ApiError(
            404, f"Classe {class_cnpj} não mapeada às contas do piloto.", code="not-found"
        )
    return performance


# --------------------------------------------------------------------- signals


@api.get(
    "/signals",
    response_model=Page[SignalOut],
    tags=["sinais"],
    summary="Sinais de timing com evidência",
)
def list_signals(
    session: SessionDep,
    account_id: AccountFilter = None,
    unit_key: Annotated[str | None, Query(pattern=UNIT_KEY_PATTERN)] = None,
    signal_type: Literal[
        "product_launches",
        "net_flows",
        "expansion",
        "hiring",
        "m_and_a",
        "operational_change",
        "performance",
    ]
    | None = None,
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> dict[str, Any]:
    data, total = repository.list_signals(
        session,
        account_id=account_id,
        unit_key=unit_key,
        signal_type=signal_type,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return _page(data, total, page, page_size, "observed_at", "desc")


# ------------------------------------------------------------------------- map


@api.get(
    "/map/offices",
    response_model=OfficeFeatureCollection,
    tags=["mapa"],
    summary="Escritórios georreferenciados (GeoJSON)",
)
def map_offices(
    session: SessionDep,
    bbox: Annotated[
        str | None, Query(description="min_lon,min_lat,max_lon,max_lat (WGS84).", max_length=100)
    ] = None,
    institution_type: Annotated[str | None, Query(max_length=64)] = None,
    tier: Tier | None = None,
    exact_only: bool = False,
) -> dict[str, Any]:
    return repository.map_offices(
        session,
        bbox=_bbox(bbox),
        institution_type=institution_type,
        tier=tier,
        exact_only=exact_only,
    )


@api.get(
    "/map/density",
    response_model=DensityGrid,
    tags=["mapa"],
    summary="Densidade de prospects em grade (heatmap)",
)
def map_density(
    session: SessionDep,
    cell_m: Annotated[
        int, Query(ge=100, le=20_000, description="Lado da célula em metros.")
    ] = 1_000,
    bbox: Annotated[str | None, Query(max_length=100)] = None,
) -> dict[str, Any]:
    return repository.density_grid(session, cell_m=cell_m, bbox=_bbox(bbox))


# ----------------------------------------------------------------- data quality


@api.get(
    "/data-quality",
    response_model=DataQuality,
    tags=["qualidade"],
    summary="Freshness, cobertura, lacunas e conflitos",
    responses=NOT_FOUND,
)
def get_data_quality(session: SessionDep) -> dict[str, Any]:
    report = repository.data_quality(session)
    if report is None:
        raise ApiError(404, "Nenhum relatório de qualidade carregado.", code="not-found")
    return report


@api.get(
    "/data-quality/conflicts",
    response_model=Page[ConflictOut],
    tags=["qualidade"],
    summary="Fila de revisão humana",
)
def list_conflicts(
    session: SessionDep,
    status: Literal[
        "pending_review",
        "accept_source",
        "keep_workbook",
        "both_valid",
        "dismissed",
        "no_longer_detected",
    ]
    | None = None,
    account_id: AccountFilter = None,
    page: PageNumber = 1,
    page_size: PageSize = 50,
) -> dict[str, Any]:
    data, total = repository.list_conflicts(
        session,
        status=status,
        account_id=account_id,
        limit=page_size,
        offset=(page - 1) * page_size,
    )
    return _page(data, total, page, page_size, "severity", "asc")
