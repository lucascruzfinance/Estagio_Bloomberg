"""Read queries for the territory universe (Prompt 8 tables)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from networking_intel.api.repository import _num, order_clause, search_pattern

UNIVERSE_SORTS = {
    "nav": "nav_brl",
    "net_flow": "net_flow_12m_brl",
    "name": "e.legal_name",
    "registered": "e.registration_date",
    "administered": "e.funds_administered",
    "classes": "e.active_classes",
}
# Accent folding without the unaccent extension (the search term is already folded).
FOLD = "translate(lower({}), 'áàâãäéèêëíìîïóòôõöúùûüç', 'aaaaaeeeeiiiiooooouuuuc')"
UNIVERSE_SELECT = f"""
    WITH latest AS (SELECT max(month) AS month FROM manager_monthly),
    flows AS (
        SELECT mm.manager_cnpj, sum(mm.inflow_brl - mm.outflow_brl) AS net_flow_12m_brl
        FROM manager_monthly mm, latest
        WHERE mm.month > latest.month - interval '12 months'
        GROUP BY mm.manager_cnpj
    )
    SELECT e.cnpj, e.legal_name, e.trade_name, e.group_key, g.group_name, e.kinds,
           e.primary_kind, e.side, e.coverage_tier, e.curated_account_key, e.centre, e.city,
           e.state, e.registration_date, e.active_classes, e.selected_classes,
           nav.nav_end_brl AS nav_brl, nav.month AS nav_month, f.net_flow_12m_brl,
           e.funds_administered, e.nav_administered_brl, ST_Y(e.location) AS latitude,
           ST_X(e.location) AS longitude, e.geocode_precision, e.building_key,
           count(*) OVER () AS total
    FROM universe_entities e
    JOIN economic_groups g ON g.group_key = e.group_key
    CROSS JOIN latest
    LEFT JOIN manager_monthly nav ON nav.manager_cnpj = e.cnpj AND nav.month = latest.month
    LEFT JOIN flows f ON f.manager_cnpj = e.cnpj
    WHERE (CAST(:tier AS text) IS NULL OR e.coverage_tier = :tier)
      AND (CAST(:side AS text) IS NULL OR e.side = :side)
      AND (CAST(:kind AS text) IS NULL OR CAST(:kind AS text) = ANY(e.kinds))
      AND (CAST(:centre AS text) IS NULL OR e.centre = :centre)
      AND (CAST(:cnpj AS text) IS NULL OR e.cnpj = :cnpj)
      AND (CAST(:q AS text) IS NULL OR e.cnpj LIKE :q_digits
           OR {FOLD.format("e.legal_name || ' ' || coalesce(e.trade_name, '') || ' ' || g.group_name")}
              LIKE :q)
"""


def _row(row: Mapping[Any, Any]) -> dict[str, Any]:
    return {
        "cnpj": row["cnpj"],
        "legal_name": row["legal_name"],
        "trade_name": row["trade_name"],
        "group_key": row["group_key"],
        "group_name": row["group_name"],
        "kinds": list(row["kinds"]),
        "primary_kind": row["primary_kind"],
        "side": row["side"],
        "coverage_tier": row["coverage_tier"],
        "curated_account_key": row["curated_account_key"],
        "centre": row["centre"],
        "city": row["city"],
        "state": row["state"],
        "registration_date": row["registration_date"],
        "active_classes": row["active_classes"],
        "selected_classes": row["selected_classes"],
        "nav_brl": _num(row["nav_brl"]),
        "nav_month": row["nav_month"],
        "net_flow_12m_brl": _num(row["net_flow_12m_brl"]),
        "funds_administered": row["funds_administered"],
        "nav_administered_brl": _num(row["nav_administered_brl"]),
        "latitude": _num(row["latitude"]),
        "longitude": _num(row["longitude"]),
        "geocode_precision": row["geocode_precision"],
        "building_key": row["building_key"],
    }


def _params(**filters: Any) -> dict[str, Any]:
    q = filters.pop("q", None)
    digits_only = "".join(ch for ch in (q or "") if ch.isdigit())
    return {
        "tier": None,
        "side": None,
        "kind": None,
        "centre": None,
        "cnpj": None,
        **filters,
        "q": search_pattern(q),
        "q_digits": f"{digits_only}%" if len(digits_only) >= 4 else "__no_match__",
    }


def list_universe(
    session: Session, *, sort: str, order: str, limit: int, offset: int, **filters: Any
) -> tuple[list[dict[str, Any]], int]:
    rows = (
        session.execute(
            text(
                UNIVERSE_SELECT
                + " ORDER BY "
                + order_clause(UNIVERSE_SORTS, sort, order, "e.cnpj ASC")
                + " LIMIT :limit OFFSET :offset"
            ),
            {**_params(**filters), "limit": limit, "offset": offset},
        )
        .mappings()
        .all()
    )
    total = int(rows[0]["total"]) if rows else 0
    return [_row(row) for row in rows], total


MONTHLY_SQL = """
    SELECT month, nav_end_brl, inflow_brl, outflow_brl, inflow_brl - outflow_brl AS net,
           investors_end, classes_reporting
    FROM manager_monthly WHERE manager_cnpj = :cnpj ORDER BY month
"""
TOP_FUNDS_SQL = """
    WITH last AS (SELECT max(month) AS month FROM fund_monthly),
    agg AS (
        SELECT m.class_cnpj,
               sum(m.nav_end_brl) FILTER (WHERE m.month = last.month) AS nav_end_brl,
               sum(m.inflow_brl - m.outflow_brl)
                   FILTER (WHERE m.month > last.month - interval '12 months') AS net_flow,
               max(m.quota_end) FILTER (WHERE m.month = last.month AND m.subclass_id = '')
                   / NULLIF(max(m.quota_end) FILTER (
                       WHERE m.month = last.month - interval '12 months'
                         AND m.subclass_id = ''), 0) - 1 AS return_12m
        FROM fund_monthly m, last
        GROUP BY m.class_cnpj
    )
    SELECT c.class_cnpj, c.class_name, c.classification, c.anbima_classification, c.is_selected,
           a.nav_end_brl, a.net_flow, a.return_12m
    FROM universe_fund_classes c JOIN agg a ON a.class_cnpj = c.class_cnpj
    WHERE c.manager_cnpj = :cnpj AND c.is_active
    ORDER BY a.nav_end_brl DESC NULLS LAST
    LIMIT 15
"""


def universe_detail(session: Session, cnpj: str) -> dict[str, Any] | None:
    row = session.execute(text(UNIVERSE_SELECT + " LIMIT 1"), _params(cnpj=cnpj)).mappings().first()
    if row is None:
        return None
    extra = (
        session.execute(
            text(
                """
                SELECT e.phone_official, e.website_official, e.street, e.complement, e.district,
                       e.as_of_date, s.source_type, s.source_url, s.collected_at, s.file_sha256,
                       (SELECT count(*) FROM universe_entities o WHERE o.group_key = e.group_key)
                           AS group_members
                FROM universe_entities e JOIN sources s ON s.id = e.source_id
                WHERE e.cnpj = :cnpj
                """
            ),
            {"cnpj": cnpj},
        )
        .mappings()
        .one()
    )
    monthly = [
        {
            "month": m["month"],
            "nav_brl": _num(m["nav_end_brl"]),
            "inflow_brl": _num(m["inflow_brl"]),
            "outflow_brl": _num(m["outflow_brl"]),
            "net_flow_brl": _num(m["net"]),
            "investors": m["investors_end"],
            "classes_reporting": m["classes_reporting"],
        }
        for m in session.execute(text(MONTHLY_SQL), {"cnpj": cnpj}).mappings()
    ]
    funds = [
        {
            "class_cnpj": f["class_cnpj"],
            "class_name": f["class_name"],
            "classification": f["classification"],
            "anbima_classification": f["anbima_classification"],
            "nav_brl": _num(f["nav_end_brl"]),
            "return_12m": _num(f["return_12m"]),
            "net_flow_12m_brl": _num(f["net_flow"]),
            "is_selected": f["is_selected"],
        }
        for f in session.execute(text(TOP_FUNDS_SQL), {"cnpj": cnpj}).mappings()
    ]
    return {
        **_row(row),
        "phone_official": extra["phone_official"],
        "website_official": extra["website_official"],
        "street": extra["street"],
        "complement": extra["complement"],
        "district": extra["district"],
        "group_members": extra["group_members"],
        "monthly": monthly,
        "top_funds": funds,
        "source": {
            "source_type": extra["source_type"],
            "url": extra["source_url"],
            "collected_at": extra["collected_at"],
            "as_of_date": extra["as_of_date"],
            "sha256": extra["file_sha256"],
        },
    }


def universe_summary(session: Session) -> dict[str, Any]:
    totals = (
        session.execute(
            text(
                """
                SELECT count(*) AS entities,
                       count(*) FILTER (WHERE side = 'buy_side') AS buy_side,
                       count(*) FILTER (WHERE side = 'sell_side') AS sell_side,
                       count(*) FILTER (WHERE coverage_tier = 'curated') AS curated,
                       count(*) FILTER (WHERE coverage_tier = 'radar') AS radar,
                       count(*) FILTER (WHERE location IS NOT NULL) AS geocoded,
                       count(DISTINCT group_key) AS groups,
                       (SELECT count(*) FROM curated_accounts) AS curated_accounts,
                       (SELECT count(*) FROM universe_fund_classes WHERE is_active)
                           AS active_classes
                FROM universe_entities
                """
            )
        )
        .mappings()
        .one()
    )
    by_centre = [
        dict(r)
        for r in session.execute(
            text(
                """
                SELECT coalesce(centre, 'Fora de SP/RJ') AS centre, count(*) AS entities,
                       count(*) FILTER (WHERE side = 'buy_side') AS buy_side,
                       count(*) FILTER (WHERE side = 'sell_side') AS sell_side,
                       count(*) FILTER (WHERE coverage_tier = 'radar') AS radar
                FROM universe_entities GROUP BY 1 ORDER BY 2 DESC
                """
            )
        ).mappings()
    ]
    by_kind = [
        dict(r)
        for r in session.execute(
            text(
                "SELECT kind, count(*) AS entities FROM universe_entities, unnest(kinds) AS kind"
                " GROUP BY kind ORDER BY 2 DESC"
            )
        ).mappings()
    ]
    as_of = (
        session.execute(
            text(
                "SELECT (SELECT max(month) FROM manager_monthly) AS fund_month,"
                " (SELECT max(as_of_date) FROM universe_entities) AS registry_date,"
                " (SELECT max(period) FROM bank_institutions) AS ifdata_period"
            )
        )
        .mappings()
        .one()
    )
    radar, _ = list_universe(
        session, sort="registered", order="desc", limit=12, offset=0, tier="radar"
    )
    return {
        "as_of": dict(as_of),
        "totals": {k: int(v) for k, v in totals.items()},
        "by_centre": by_centre,
        "by_kind": by_kind,
        "radar_recent": radar,
    }
