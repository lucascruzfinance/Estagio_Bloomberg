"""Read queries. Every ORDER BY comes from a whitelist; every value is a bound parameter."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from networking_intel.etl.transform import normalize_name

LATEST_RUN = "(SELECT id FROM score_runs ORDER BY loaded_at DESC, id LIMIT 1)"
LATEST_QUALITY = "(SELECT payload FROM quality_reports ORDER BY run_at DESC LIMIT 1)"
ATTRIBUTION_OSM = "Geocodificação: © OpenStreetMap contributors (ODbL), via Nominatim."
ATTRIBUTION_CVM = "Fundos, gestores e endereços: CVM — Portal de Dados Abertos."

ACCOUNT_SORTS = {
    "priority": "best.priority_point",
    "fit": "best.fit_point",
    "timing": "best.timing_point",
    "confidence": "best.confidence",
    "rank": "best.rank",
    "name": "org.canonical_name",
    "nav": "(qa->>'nav_brl_non_fic')::numeric",
    "net_flow": "(qa->>'net_flow_12m_brl_non_fic')::numeric",
}
SCORE_SORTS = {
    "rank": "s.rank",
    "priority": "s.priority_point",
    "fit": "s.fit_point",
    "timing": "s.timing_point",
    "confidence": "s.confidence",
    "name": "s.unit_name",
}
FUND_SORTS = {
    "nav": "m.latest_nav_brl",
    "return_12m": "m.return_12m",
    "return_ytd": "m.return_ytd",
    "net_flow_12m": "m.net_flow_12m_brl",
    "volatility": "m.volatility_12m",
    "drawdown": "m.max_drawdown_12m",
    "name": "f.canonical_name",
    "constitution_date": "f.constitution_date",
}


def _num(value: Any) -> Any:
    return float(value) if isinstance(value, Decimal) else value


def _row(mapping: Mapping[Any, Any]) -> dict[str, Any]:
    return {key: _num(value) for key, value in mapping.items()}


def order_clause(sorts: Mapping[str, str], sort: str, order: str, tiebreak: str) -> str:
    expression = sorts[sort]  # KeyError impossible: routes validate against the same keys
    direction = "ASC" if order == "asc" else "DESC"
    return f"{expression} {direction} NULLS LAST, {tiebreak}"


def band(point: Any, lower: Any, upper: Any, coverage: Any = None) -> dict[str, Any]:
    return {
        "point": _num(point),
        "lower": _num(lower),
        "upper": _num(upper),
        "coverage": _num(coverage),
    }


# --------------------------------------------------------------------- scores


def _reasons(explanation: dict[str, Any], polarity: str, limit: int = 3) -> list[str]:
    reasons = [r for r in explanation.get("reasons", []) if r["polarity"] == polarity]
    reasons.sort(key=lambda r: -(r.get("points") or 0.0))
    return [r["text"] for r in reasons[:limit]]


def score_row(row: Mapping[Any, Any]) -> dict[str, Any]:
    explanation = row["explanation"]
    return {
        "rank": row["rank"],
        "unit_key": row["unit_key"],
        "unit_name": row["unit_name"],
        "account_id": row["account_id"],
        "canonical_name": row["canonical_name"],
        "institution_type": row["institution_type"],
        "analysis_unit": row["analysis_unit"],
        "evidence_mode": row["evidence_mode"],
        "tier": row["tier"],
        "priority": band(row["priority_point"], row["priority_lower"], row["priority_upper"]),
        "fit": band(row["fit_point"], row["fit_lower"], row["fit_upper"], row["fit_coverage"]),
        "fit_assumption_share": _num(row["fit_assumption_share"]),
        "timing": band(
            row["timing_point"], row["timing_lower"], row["timing_upper"], row["timing_coverage"]
        ),
        "confidence": _num(row["confidence"]),
        "top_positive": _reasons(explanation, "+"),
        "top_negative": _reasons(explanation, "-"),
        "missing_factors": [
            r["factor"] for r in explanation.get("reasons", []) if r["polarity"] == "?"
        ],
    }


SCORE_SELECT = f"""
    SELECT s.*, org.account_id, org.canonical_name, org.institution_type, org.analysis_unit,
           count(*) OVER () AS total
    FROM opportunity_scores s
    JOIN organizations org ON org.id = s.organization_id
    WHERE s.score_run_id = {LATEST_RUN}
"""


def list_scores(
    session: Session,
    *,
    tier: str | None,
    evidence_mode: str | None,
    account_id: str | None,
    institution_type: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                SCORE_SELECT
                + """
              AND (CAST(:tier AS text) IS NULL OR s.tier = :tier)
              AND (CAST(:mode AS text) IS NULL OR s.evidence_mode = :mode)
              AND (CAST(:account AS text) IS NULL OR org.account_id = :account)
              AND (CAST(:itype AS text) IS NULL OR org.institution_type = :itype)
            ORDER BY """
                + order_clause(SCORE_SORTS, sort, order, "s.rank ASC")
                + " LIMIT :limit OFFSET :offset"
            ),
            {
                "tier": tier,
                "mode": evidence_mode,
                "account": account_id,
                "itype": institution_type,
                "limit": limit,
                "offset": offset,
            },
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    return [score_row(row) for row in rows], total


def scores_for_units(session: Session, unit_keys: Sequence[str]) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            text(SCORE_SELECT + " AND s.unit_key = ANY(:keys) ORDER BY s.rank"),
            {"keys": list(unit_keys)},
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


def score_explanation(session: Session, unit_key: str) -> dict[str, Any] | None:
    rows = scores_for_units(session, [unit_key])
    if not rows:
        return None
    row = rows[0]
    run = (
        session.execute(
            text(
                f"SELECT model_version, as_of_date, limitations, sanity_checks FROM score_runs "
                f"WHERE id = {LATEST_RUN}"
            )
        )
        .mappings()
        .one()
    )
    explanation = row["explanation"]
    weights = explanation.get("weights", {})
    contributions = {
        "fit": explanation.get("fit_contributions", {}),
        "timing": explanation.get("timing_contributions", {}),
    }
    factors = [
        {
            "key": f["key"],
            "group": f["group"],
            "label": f["label"],
            "weight": weights.get(f["group"], {}).get(f["key"]),
            "value": f["value"],
            "status": f["status"],
            "contribution_points": contributions[f["group"]].get(f["key"]),
            "explanation": f["explanation"],
            "evidence": list(f["evidence"]),
            "raw": f["raw"],
        }
        for f in explanation["factors"]
    ]
    involved = {unit_key, unit_key.split(":")[0]}
    sanity = [
        check
        for check in run["sanity_checks"]
        if check.get("higher") in involved or check.get("lower") in involved
    ]
    return {
        "score": score_row(row),
        "model_version": run["model_version"],
        "as_of_date": run["as_of_date"],
        "factors": factors,
        "reasons": explanation["reasons"],
        "confidence_components": explanation["confidence_components"],
        "products": explanation["products"],
        "limitations": run["limitations"],
        "sanity_checks": sanity,
    }


# ------------------------------------------------------------------- accounts

ACCOUNT_CTE = f"""
WITH best AS (
    SELECT DISTINCT ON (s.organization_id) s.*
    FROM opportunity_scores s
    WHERE s.score_run_id = {LATEST_RUN}
    ORDER BY s.organization_id, s.rank
),
units AS (
    SELECT organization_id, count(*) AS n
    FROM opportunity_scores WHERE score_run_id = {LATEST_RUN}
    GROUP BY organization_id
),
hq AS (
    SELECT DISTINCT ON (o.organization_id)
           o.organization_id, o.address_raw, o.city, o.state, o.geocode_precision,
           o.geocode_is_exact, ST_X(o.location) AS longitude, ST_Y(o.location) AS latitude
    FROM offices o
    JOIN legal_entities e ON e.id = o.legal_entity_id
    WHERE o.office_kind = 'regulatory'
    ORDER BY o.organization_id,
             CASE e.relation WHEN 'primary_manager' THEN 0 WHEN 'bank_entity' THEN 1 ELSE 2 END,
             o.geocode_is_exact DESC, e.cnpj
),
conflicts AS (
    SELECT organization_id, count(*) FILTER (WHERE resolution_status = 'pending_review') AS open
    FROM data_conflicts GROUP BY organization_id
),
quality AS (
    SELECT a AS qa FROM jsonb_array_elements({LATEST_QUALITY}->'accounts') a
)
"""

ACCOUNT_SELECT = (
    ACCOUNT_CTE
    + """
SELECT org.*, best.unit_key AS best_unit_key, best.rank AS best_rank, best.tier,
       best.priority_point, best.priority_lower, best.priority_upper,
       best.fit_point, best.fit_lower, best.fit_upper, best.fit_coverage,
       best.timing_point, best.timing_lower, best.timing_upper, best.timing_coverage,
       best.confidence AS score_confidence, COALESCE(units.n, 0) AS units_scored,
       hq.address_raw AS hq_address, hq.city AS hq_city, hq.state AS hq_state,
       hq.geocode_precision AS hq_precision, hq.geocode_is_exact AS hq_exact,
       hq.longitude AS hq_longitude, hq.latitude AS hq_latitude,
       COALESCE(conflicts.open, 0) AS open_conflicts,
       (qa->>'nav_brl_non_fic')::numeric AS nav_brl_non_fic,
       (qa->>'net_flow_12m_brl_non_fic')::numeric AS net_flow_12m_brl,
       qa, count(*) OVER () AS total
FROM organizations org
LEFT JOIN best ON best.organization_id = org.id
LEFT JOIN units ON units.organization_id = org.id
LEFT JOIN hq ON hq.organization_id = org.id
LEFT JOIN conflicts ON conflicts.organization_id = org.id
LEFT JOIN quality ON quality.qa->>'account_id' = org.account_id
WHERE (CAST(:account AS text) IS NULL OR org.account_id = :account)
  AND (CAST(:itype AS text) IS NULL OR org.institution_type = :itype)
  AND (CAST(:tier AS text) IS NULL OR best.tier = :tier)
  AND (CAST(:state AS text) IS NULL OR hq.state = :state)
  AND (CAST(:q AS text) IS NULL OR org.id IN (
        SELECT organization_id FROM organization_aliases WHERE normalized_alias LIKE :q
      ))
"""
)


def account_summary(row: Mapping[Any, Any]) -> dict[str, Any]:
    has_score = row["best_unit_key"] is not None
    headquarters = (
        {
            "address": row["hq_address"],
            "city": row["hq_city"],
            "state": row["hq_state"],
            "latitude": _num(row["hq_latitude"]),
            "longitude": _num(row["hq_longitude"]),
            "precision": row["hq_precision"],
            "is_exact": bool(row["hq_exact"]),
        }
        if row["hq_address"]
        else None
    )
    return {
        "account_id": row["account_id"],
        "canonical_name": row["canonical_name"],
        "legal_name": row["legal_name"],
        "cnpj": row["cnpj"],
        "institution_type": row["institution_type"],
        "analysis_unit": row["analysis_unit"],
        "strategy_profile": row["strategy_profile"],
        "headquarters": headquarters,
        "best_unit_key": row["best_unit_key"],
        "best_rank": row["best_rank"],
        "tier": row["tier"],
        "priority": band(row["priority_point"], row["priority_lower"], row["priority_upper"])
        if has_score
        else None,
        "fit": band(row["fit_point"], row["fit_lower"], row["fit_upper"], row["fit_coverage"])
        if has_score
        else None,
        "timing": band(
            row["timing_point"], row["timing_lower"], row["timing_upper"], row["timing_coverage"]
        )
        if has_score
        else None,
        "confidence": _num(row["score_confidence"]),
        "units_scored": int(row["units_scored"]),
        "nav_brl_non_fic": _num(row["nav_brl_non_fic"]),
        "net_flow_12m_brl": _num(row["net_flow_12m_brl"]),
        "open_conflicts": int(row["open_conflicts"]),
    }


def search_pattern(q: str | None) -> str | None:
    if not q:
        return None
    normalized = normalize_name(q)
    return f"%{normalized}%" if normalized else None


def list_accounts(
    session: Session,
    *,
    q: str | None,
    institution_type: str | None,
    tier: str | None,
    state: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                ACCOUNT_SELECT
                + " ORDER BY "
                + order_clause(ACCOUNT_SORTS, sort, order, "org.canonical_name ASC")
                + " LIMIT :limit OFFSET :offset"
            ),
            {
                "account": None,
                "itype": institution_type,
                "tier": tier,
                "state": state,
                "q": search_pattern(q),
                "limit": limit,
                "offset": offset,
            },
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    return [account_summary(row) for row in rows], total


def _source(row: Mapping[Any, Any], prefix: str = "src_") -> dict[str, Any]:
    return {
        "source_type": row[f"{prefix}type"],
        "url": row[f"{prefix}url"],
        "collected_at": row[f"{prefix}collected_at"],
        "as_of_date": row.get(f"{prefix}as_of"),
        "sha256": row[f"{prefix}sha"],
    }


def account_detail(session: Session, account_id: str) -> dict[str, Any] | None:
    base = (
        session.execute(
            text(ACCOUNT_SELECT + " LIMIT 1"),
            {"account": account_id, "itype": None, "tier": None, "state": None, "q": None},
        )
        .mappings()
        .first()
    )
    if base is None:
        return None
    detail = account_summary(base)
    org_id = base["id"]
    detail["website_url"] = base["website_url"]
    detail["phone_public_workbook"] = base["phone_public"]

    entities = (
        session.execute(
            text(
                """
            SELECT e.*, bu.unit_key AS business_unit_key, s.source_type AS src_type,
                   s.source_url AS src_url, s.collected_at AS src_collected_at,
                   e.as_of_date AS src_as_of, s.file_sha256 AS src_sha
            FROM legal_entities e
            JOIN sources s ON s.id = e.source_id
            LEFT JOIN business_units bu ON bu.id = e.business_unit_id
            WHERE e.organization_id = :org
            ORDER BY CASE e.relation WHEN 'primary_manager' THEN 0 WHEN 'bank_entity' THEN 1 ELSE 2 END,
                     e.legal_name
            """
            ),
            {"org": org_id},
        )
        .mappings()
        .all()
    )
    detail["legal_entities"] = [{**_row(e), "source": _source(e)} for e in entities]

    offices = (
        session.execute(
            text(
                """
            SELECT o.office_key, o.office_kind, o.address_raw, o.city, o.state,
                   ST_X(o.location) AS longitude, ST_Y(o.location) AS latitude,
                   o.geocode_precision, o.geocode_is_exact, o.geocode_status, o.confidence,
                   e.cnpj AS legal_entity_cnpj
            FROM offices o LEFT JOIN legal_entities e ON e.id = o.legal_entity_id
            WHERE o.organization_id = :org
            ORDER BY o.office_kind DESC, o.geocode_is_exact DESC, o.address_raw
            """
            ),
            {"org": org_id},
        )
        .mappings()
        .all()
    )
    detail["offices"] = [
        {
            "office_key": o["office_key"],
            "office_kind": o["office_kind"],
            "legal_entity_cnpj": o["legal_entity_cnpj"],
            "geocode_status": o["geocode_status"],
            "confidence": o["confidence"],
            "location": {
                "address": o["address_raw"],
                "city": o["city"],
                "state": o["state"],
                "latitude": _num(o["latitude"]),
                "longitude": _num(o["longitude"]),
                "precision": o["geocode_precision"],
                "is_exact": bool(o["geocode_is_exact"]),
            },
        }
        for o in offices
    ]

    people = (
        session.execute(
            text(
                """
            SELECT full_name, role_title, verification_status, as_of_date
            FROM people WHERE organization_id = :org AND is_public_professional_data
            ORDER BY full_name
            """
            ),
            {"org": org_id},
        )
        .mappings()
        .all()
    )
    detail["people"] = [
        {
            "full_name": p["full_name"],
            "role_title": p["role_title"],
            "basis": p["verification_status"] or "registro público",
            "as_of_date": p["as_of_date"],
        }
        for p in people
    ]

    scores = scores_for_account(session, account_id)
    detail["scores"] = [score_row(s) for s in scores]
    by_unit = {s["unit_key"]: s for s in detail["scores"]}
    units = (
        session.execute(
            text(
                "SELECT unit_key, name, mapping_status FROM business_units "
                "WHERE organization_id = :org ORDER BY unit_key"
            ),
            {"org": org_id},
        )
        .mappings()
        .all()
    )
    detail["business_units"] = [
        {**dict(u), "account_id": account_id, "score": by_unit.get(u["unit_key"])} for u in units
    ]
    seen: set[tuple[str, str]] = set()
    products: list[dict[str, Any]] = []
    for score in scores:
        for product in score["explanation"].get("products", []):
            key = (product["product_code"], product["basis"])
            if key not in seen:
                seen.add(key)
                products.append(product)
    detail["products"] = products
    detail["signals"] = list_signals(
        session, account_id=account_id, unit_key=None, signal_type=None, limit=200, offset=0
    )[0]
    quality = base["qa"]
    detail["quality"] = account_quality(quality) if quality else None
    return detail


def scores_for_account(session: Session, account_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in session.execute(
            text(SCORE_SELECT + " AND org.account_id = :account ORDER BY s.rank"),
            {"account": account_id},
        ).mappings()
    ]


def list_business_units(session: Session, account_id: str | None) -> list[dict[str, Any]]:
    rows = (
        session.execute(
            text(
                """
            SELECT bu.unit_key, bu.name, bu.mapping_status, org.account_id
            FROM business_units bu JOIN organizations org ON org.id = bu.organization_id
            WHERE CAST(:account AS text) IS NULL OR org.account_id = :account
            ORDER BY org.account_id, bu.unit_key
            """
            ),
            {"account": account_id},
        )
        .mappings()
        .all()
    )
    scores = {
        s["unit_key"]: score_row(s)
        for s in scores_for_units(session, [r["unit_key"] for r in rows])
    }
    return [{**dict(r), "score": scores.get(r["unit_key"])} for r in rows]


def account_quality(qa: Mapping[Any, Any]) -> dict[str, Any]:
    return {
        "account_id": qa["account_id"],
        "canonical_name": qa["canonical_name"],
        "entities_found": qa["entities_found"],
        "entities_registered": qa["entities_registered"],
        "official_address": bool(qa["official_address"]),
        "geocode_precision": qa["geocode_precision"],
        "active_classes": qa["active_classes"],
        "classes_with_daily_report": qa["classes_with_daily_report"],
        "comparable_12m_share": qa["comparable_12m_share"],
        "open_conflicts": qa.get("open_conflicts", 0),
        "gaps": qa["gaps"],
    }


# ---------------------------------------------------------------------- funds

METRIC_COLUMNS = (
    "latest_nav_brl",
    "latest_investors",
    "return_1m",
    "return_1m_status",
    "return_3m",
    "return_3m_status",
    "return_6m",
    "return_6m_status",
    "return_12m",
    "return_12m_status",
    "return_ytd",
    "return_ytd_status",
    "net_flow_12m_brl",
    "net_flow_status",
    "volatility_12m",
    "max_drawdown_12m",
)


def _metrics(row: Mapping[Any, Any]) -> dict[str, Any] | None:
    if row.get("reference_date") is None:
        return None
    return {
        "reference_date": row["reference_date"],
        **{column: _num(row[column]) for column in METRIC_COLUMNS},
    }


def list_funds(
    session: Session,
    *,
    account_id: str | None,
    unit_key: str | None,
    classification: str | None,
    active: bool | None,
    fund_of_funds: bool | None,
    exclusive: bool | None,
    with_metrics: bool,
    q: str | None,
    sort: str,
    order: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                """
            SELECT f.cnpj AS class_cnpj, f.fund_cnpj, COALESCE(m.subclass_id, '') AS subclass_id,
                   f.canonical_name AS name, f.legal_name AS fund_name, org.account_id,
                   f.manager_cnpj, bu.unit_key, f.class_type, f.classification,
                   f.anbima_classification, f.benchmark, f.is_active, f.is_exclusive,
                   f.is_fund_of_funds, f.allows_full_offshore, f.constitution_date,
                   m.reference_date, """
                + ", ".join(f"m.{c}" for c in METRIC_COLUMNS)
                + """, count(*) OVER () AS total
            FROM funds f
            JOIN organizations org ON org.id = f.organization_id
            LEFT JOIN business_units bu ON bu.id = f.business_unit_id
            LEFT JOIN fund_metrics m ON m.fund_id = f.id
                 AND m.reference_date = (SELECT max(reference_date) FROM fund_metrics)
            WHERE (CAST(:account AS text) IS NULL OR org.account_id = :account)
              AND (CAST(:unit AS text) IS NULL OR bu.unit_key = :unit)
              AND (CAST(:classification AS text) IS NULL OR f.classification = :classification)
              AND (CAST(:active AS boolean) IS NULL OR f.is_active = :active)
              AND (CAST(:fof AS boolean) IS NULL OR f.is_fund_of_funds = :fof)
              AND (CAST(:exclusive AS boolean) IS NULL OR f.is_exclusive = :exclusive)
              AND (NOT :with_metrics OR m.id IS NOT NULL)
              AND (CAST(:q AS text) IS NULL OR f.canonical_name ILIKE :q OR f.cnpj = :q_digits)
            ORDER BY """
                + order_clause(FUND_SORTS, sort, order, "f.cnpj ASC, subclass_id ASC")
                + " LIMIT :limit OFFSET :offset"
            ),
            {
                "account": account_id,
                "unit": unit_key,
                "classification": classification,
                "active": active,
                "fof": fund_of_funds,
                "exclusive": exclusive,
                "with_metrics": with_metrics,
                "q": f"%{q}%" if q else None,
                "q_digits": re.sub(r"\D", "", q or "") or None,
                "limit": limit,
                "offset": offset,
            },
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    funds = []
    for row in rows:
        item = {
            k: _num(v)
            for k, v in row.items()
            if k not in METRIC_COLUMNS and k not in {"reference_date", "total"}
        }
        item["metrics"] = _metrics(row)
        funds.append(item)
    return funds, total


def fund_performance(
    session: Session, class_cnpj: str, subclass_id: str, start: date | None, end: date | None
) -> dict[str, Any] | None:
    fund = (
        session.execute(
            text(
                """
            SELECT f.id, f.cnpj, f.canonical_name, org.account_id
            FROM funds f JOIN organizations org ON org.id = f.organization_id
            WHERE f.cnpj = :cnpj
            """
            ),
            {"cnpj": class_cnpj},
        )
        .mappings()
        .first()
    )
    if fund is None:
        return None
    points = (
        session.execute(
            text(
                """
            SELECT DISTINCT ON (o.observation_date)
                   o.observation_date, o.quota_value, o.nav_brl, o.subscriptions_brl,
                   o.redemptions_brl, o.investor_count, s.source_url
            FROM fund_observations o JOIN sources s ON s.id = o.source_id
            WHERE o.fund_id = :fund AND o.subclass_id = :subclass
              AND (CAST(:start AS date) IS NULL OR o.observation_date >= :start)
              AND (CAST(:end AS date) IS NULL OR o.observation_date <= :end)
            ORDER BY o.observation_date, s.collected_at DESC
            """
            ),
            {"fund": fund["id"], "subclass": subclass_id, "start": start, "end": end},
        )
        .mappings()
        .all()
    )
    metric = (
        session.execute(
            text(
                "SELECT reference_date, " + ", ".join(METRIC_COLUMNS) + " FROM fund_metrics "
                "WHERE fund_id = :fund AND subclass_id = :subclass "
                "ORDER BY reference_date DESC LIMIT 1"
            ),
            {"fund": fund["id"], "subclass": subclass_id},
        )
        .mappings()
        .first()
    )
    base = next((float(p["quota_value"]) for p in points if p["quota_value"]), None)
    series = []
    for p in points:
        quota = _num(p["quota_value"])
        inflow, outflow = _num(p["subscriptions_brl"]), _num(p["redemptions_brl"])
        series.append(
            {
                "date": p["observation_date"],
                "quota": quota,
                "quota_index": round(100 * quota / base, 6) if quota and base else None,
                "nav_brl": _num(p["nav_brl"]),
                "net_flow_brl": (inflow or 0.0) - (outflow or 0.0)
                if inflow is not None or outflow is not None
                else None,
                "investors": p["investor_count"],
            }
        )
    return {
        "class_cnpj": fund["cnpj"],
        "subclass_id": subclass_id,
        "name": fund["canonical_name"],
        "account_id": fund["account_id"],
        "start": series[0]["date"] if series else None,
        "end": series[-1]["date"] if series else None,
        "points": series,
        "metrics": _metrics(metric) if metric else None,
        "sources": sorted({p["source_url"] for p in points if p["source_url"]}),
        "note": "Cota e PL do Informe Diário da CVM, em BRL. Retorno do fundo para o cotista; "
        "não representa receita ou lucro da gestora.",
    }


# -------------------------------------------------------------------- signals


def list_signals(
    session: Session,
    *,
    account_id: str | None,
    unit_key: str | None,
    signal_type: str | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                """
            SELECT c.*, org.account_id, bu.unit_key AS bu_key, s.source_type AS src_type,
                   s.source_url AS src_url, s.collected_at AS src_collected_at,
                   c.as_of_date AS src_as_of, s.file_sha256 AS src_sha, count(*) OVER () AS total
            FROM commercial_signals c
            JOIN organizations org ON org.id = c.organization_id
            JOIN sources s ON s.id = c.source_id
            LEFT JOIN business_units bu ON bu.id = c.business_unit_id
            WHERE (CAST(:account AS text) IS NULL OR org.account_id = :account)
              AND (CAST(:unit AS text) IS NULL OR c.payload->>'unit_key' = :unit)
              AND (CAST(:stype AS text) IS NULL OR c.signal_type = :stype)
            ORDER BY c.observed_at DESC, org.account_id, c.payload->>'unit_key', c.signal_type
            LIMIT :limit OFFSET :offset
            """
            ),
            {
                "account": account_id,
                "unit": unit_key,
                "stype": signal_type,
                "limit": limit,
                "offset": offset,
            },
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    signals = [
        {
            "account_id": r["account_id"],
            "unit_key": r["payload"].get("unit_key") or r["bu_key"],
            "signal_type": r["signal_type"],
            "label": r["payload"].get("label"),
            "observed_at": r["observed_at"],
            "expires_at": r["expires_at"],
            "value": r["payload"].get("value"),
            "status": r["payload"].get("status"),
            "explanation": r["payload"].get("explanation"),
            "evidence": r["payload"].get("evidence", []),
            "source": _source(r),
        }
        for r in rows
    ]
    return signals, total


# ------------------------------------------------------------------------ map

MAP_BEST = f"""
WITH best AS (
    SELECT DISTINCT ON (s.organization_id) s.organization_id, s.tier, s.priority_point,
           s.fit_point, s.timing_point, s.confidence
    FROM opportunity_scores s WHERE s.score_run_id = {LATEST_RUN}
    ORDER BY s.organization_id, s.rank
),
quality AS (SELECT a AS qa FROM jsonb_array_elements({LATEST_QUALITY}->'accounts') a)
"""


def map_offices(
    session: Session,
    *,
    bbox: tuple[float, float, float, float] | None,
    institution_type: str | None,
    tier: str | None,
    exact_only: bool,
) -> dict[str, Any]:
    params = {
        "has_bbox": bbox is not None,
        "minx": bbox[0] if bbox else 0.0,
        "miny": bbox[1] if bbox else 0.0,
        "maxx": bbox[2] if bbox else 0.0,
        "maxy": bbox[3] if bbox else 0.0,
        "itype": institution_type,
        "tier": tier,
        "exact_only": exact_only,
    }
    rows = (
        session.execute(
            text(
                MAP_BEST
                + """
            SELECT o.office_key, ST_X(o.location) AS longitude, ST_Y(o.location) AS latitude,
                   o.address_raw, o.city, o.state, o.geocode_precision, o.geocode_is_exact,
                   e.cnpj AS entity_cnpj, e.legal_name, e.relation, e.phone_official,
                   org.account_id, org.canonical_name, org.institution_type,
                   best.tier, best.priority_point, best.fit_point, best.timing_point,
                   best.confidence,
                   (qa->>'nav_brl_non_fic')::numeric AS nav_brl_non_fic,
                   (qa->>'net_flow_12m_brl_non_fic')::numeric AS net_flow_12m_brl
            FROM offices o
            JOIN organizations org ON org.id = o.organization_id
            LEFT JOIN legal_entities e ON e.id = o.legal_entity_id
            LEFT JOIN best ON best.organization_id = org.id
            LEFT JOIN quality ON quality.qa->>'account_id' = org.account_id
            WHERE o.location IS NOT NULL
              AND (NOT :has_bbox OR o.location && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))
              AND (CAST(:itype AS text) IS NULL OR org.institution_type = :itype)
              AND (CAST(:tier AS text) IS NULL OR best.tier = :tier)
              AND (NOT :exact_only OR o.geocode_is_exact)
            ORDER BY org.account_id, o.office_key
            """
            ),
            params,
        )
        .mappings()
        .all()
    )
    missing = session.execute(
        text(
            MAP_BEST
            + """
            SELECT count(*) FROM offices o
            JOIN organizations org ON org.id = o.organization_id
            LEFT JOIN best ON best.organization_id = org.id
            WHERE o.location IS NULL
              AND (CAST(:itype AS text) IS NULL OR org.institution_type = :itype)
              AND (CAST(:tier AS text) IS NULL OR best.tier = :tier)
            """
        ),
        params,
    ).scalar_one()
    features = [
        {
            "geometry": {"coordinates": (float(r["longitude"]), float(r["latitude"]))},
            "properties": {
                "office_key": r["office_key"],
                "account_id": r["account_id"],
                "canonical_name": r["canonical_name"],
                "institution_type": r["institution_type"],
                "legal_name": r["legal_name"],
                "entity_cnpj": r["entity_cnpj"],
                "relation": r["relation"],
                "address": r["address_raw"],
                "city": r["city"],
                "state": r["state"],
                "phone_official": r["phone_official"],
                "precision": r["geocode_precision"],
                "is_exact": bool(r["geocode_is_exact"]),
                "tier": r["tier"],
                "priority_point": _num(r["priority_point"]),
                "fit_point": _num(r["fit_point"]),
                "timing_point": _num(r["timing_point"]),
                "confidence": _num(r["confidence"]),
                "nav_brl_non_fic": _num(r["nav_brl_non_fic"]),
                "net_flow_12m_brl": _num(r["net_flow_12m_brl"]),
            },
        }
        for r in rows
    ]
    return {
        "features": features,
        "meta": {
            "count": len(features),
            "without_location": int(missing),
            "attribution": f"{ATTRIBUTION_OSM} {ATTRIBUTION_CVM}",
            "precision_note": "Pontos com is_exact=false são aproximados (rua ou bairro) e devem "
            "ser exibidos como tal.",
        },
    }


def density_grid(
    session: Session, *, cell_m: int, bbox: tuple[float, float, float, float] | None
) -> dict[str, Any]:
    rows = (
        session.execute(
            text(
                """
            SELECT ST_X(c) AS longitude, ST_Y(c) AS latitude, n, accounts FROM (
                SELECT ST_Transform(ST_Centroid(ST_Collect(ST_Transform(o.location, 3857))), 4326) AS c,
                       count(*) AS n,
                       array_agg(DISTINCT org.account_id ORDER BY org.account_id) AS accounts
                FROM offices o JOIN organizations org ON org.id = o.organization_id
                WHERE o.location IS NOT NULL
                  AND (NOT :has_bbox OR o.location && ST_MakeEnvelope(:minx, :miny, :maxx, :maxy, 4326))
                GROUP BY ST_SnapToGrid(ST_Transform(o.location, 3857), :cell)
            ) cells
            ORDER BY n DESC, longitude
            """
            ),
            {
                "cell": cell_m,
                "has_bbox": bbox is not None,
                "minx": bbox[0] if bbox else 0.0,
                "miny": bbox[1] if bbox else 0.0,
                "maxx": bbox[2] if bbox else 0.0,
                "maxy": bbox[3] if bbox else 0.0,
            },
        )
        .mappings()
        .all()
    )
    return {
        "cell_m": cell_m,
        "cells": [
            {
                "longitude": float(r["longitude"]),
                "latitude": float(r["latitude"]),
                "offices": int(r["n"]),
                "accounts": list(r["accounts"]),
            }
            for r in rows
        ],
        "attribution": ATTRIBUTION_OSM,
        "note": "Densidade de escritórios de prospects (inclui pontos aproximados); "
        "não representa performance.",
    }


# ---------------------------------------------------------------- data quality


def data_quality(session: Session) -> dict[str, Any] | None:
    report = (
        session.execute(
            text(
                "SELECT version, run_at, fund_reference_date, payload FROM quality_reports ORDER BY run_at DESC LIMIT 1"
            )
        )
        .mappings()
        .first()
    )
    if report is None:
        return None
    payload = report["payload"]
    conflicts: dict[str, int] = dict(
        session.execute(
            text("SELECT resolution_status, count(*) FROM data_conflicts GROUP BY 1 ORDER BY 1")
        ).all()
    )
    database = (
        session.execute(
            text(
                """
            SELECT
              (SELECT count(*) FROM organizations) AS organizations,
              (SELECT count(*) FROM legal_entities) AS legal_entities,
              (SELECT count(*) FROM offices WHERE office_kind = 'regulatory') AS regulatory_offices,
              (SELECT count(*) FROM offices WHERE location IS NOT NULL) AS located_offices,
              (SELECT count(*) FROM offices WHERE geocode_is_exact) AS exact_offices,
              (SELECT count(*) FROM funds) AS fund_classes,
              (SELECT count(*) FROM funds WHERE is_active) AS active_fund_classes,
              (SELECT count(*) FROM fund_metrics) AS fund_metric_rows,
              (SELECT max(last_date) FROM fund_metrics) AS latest_observation,
              (SELECT count(*) FROM commercial_signals) AS signals,
              (SELECT max(completed_at) FROM ingestion_runs WHERE status = 'complete') AS last_load
            """
            )
        )
        .mappings()
        .one()
    )
    return {
        "report_version": report["version"],
        "run_at": report["run_at"],
        "fund_reference_date": report["fund_reference_date"],
        "freshness": payload["freshness"],
        "accounts": [account_quality(a) for a in payload["accounts"]],
        "rules": payload["rules"],
        "conflicts_by_status": {k: int(v) for k, v in conflicts.items()},
        "database": {k: (int(v) if isinstance(v, int) else v) for k, v in database.items()},
    }


def list_conflicts(
    session: Session, *, status: str | None, account_id: str | None, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                """
            SELECT c.*, org.account_id, count(*) OVER () AS total
            FROM data_conflicts c JOIN organizations org ON org.id = c.organization_id
            WHERE (CAST(:status AS text) IS NULL OR c.resolution_status = :status)
              AND (CAST(:account AS text) IS NULL OR org.account_id = :account)
            ORDER BY CASE c.severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                     org.account_id, c.conflict_id
            LIMIT :limit OFFSET :offset
            """
            ),
            {"status": status, "account": account_id, "limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    return [dict(r) for r in rows], total


# ---------------------------------------------------------------------- search


def search(session: Session, q: str, limit: int) -> list[dict[str, Any]]:
    normalized = normalize_name(q)
    digits = re.sub(r"\D", "", q)
    rows = (
        session.execute(
            text(
                """
            SELECT org.account_id, org.canonical_name, org.institution_type, a.alias AS matched,
                   a.alias_kind,
                   CASE WHEN a.normalized_alias = :n THEN 'exact'
                        WHEN a.normalized_alias LIKE :n || '%' THEN 'prefix'
                        ELSE 'contains' END AS match_kind
            FROM organization_aliases a JOIN organizations org ON org.id = a.organization_id
            WHERE :n <> '' AND a.normalized_alias LIKE '%' || :n || '%'
            UNION ALL
            SELECT org.account_id, org.canonical_name, org.institution_type, e.cnpj, 'cnpj', 'cnpj'
            FROM legal_entities e JOIN organizations org ON org.id = e.organization_id
            WHERE length(:d) >= 8 AND e.cnpj LIKE :d || '%'
            """
            ),
            {"n": normalized, "d": digits},
        )
        .mappings()
        .all()
    )
    rank = {"cnpj": 0, "exact": 1, "prefix": 2, "contains": 3}
    best: dict[str, dict[str, Any]] = {}
    for row in sorted(
        rows, key=lambda r: (rank[r["match_kind"]], r["canonical_name"], r["matched"])
    ):
        best.setdefault(row["account_id"], dict(row))
    return sorted(best.values(), key=lambda r: (rank[r["match_kind"]], r["canonical_name"]))[:limit]


# ------------------------------------------------------------------------ meta


def meta(session: Session) -> dict[str, Any]:
    run = (
        session.execute(
            text(
                f"SELECT model_version, as_of_date, loaded_at, limitations FROM score_runs "
                f"WHERE id = {LATEST_RUN}"
            )
        )
        .mappings()
        .first()
    )
    reference = session.execute(
        text("SELECT fund_reference_date FROM quality_reports ORDER BY run_at DESC LIMIT 1")
    ).scalar()
    return {
        "model_version": run["model_version"] if run else None,
        "score_as_of_date": run["as_of_date"] if run else None,
        "score_run_loaded_at": run["loaded_at"] if run else None,
        "fund_reference_date": reference,
        "limitations": list(run["limitations"]) if run else [],
    }
