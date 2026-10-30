"""Load the Prompt 3 enrichment and Prompt 4 scoring outputs into PostgreSQL.

Idempotent: every table is upserted on its natural key, the daily panel goes
through COPY into a temporary table, and score-run children are replaced as a
unit. Requires the Prompt 2 ETL (organizations) to have run first.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any, cast

import polars as pl
from sqlalchemy import Engine, Table, delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from networking_intel.db.models import (
    BusinessUnit,
    CommercialSignal,
    DataConflict,
    FieldProvenance,
    IngestionRun,
    LegalEntity,
    Office,
    OpportunityScore,
    Organization,
    OrganizationAlias,
    Person,
    ProductFit,
    QualityReport,
    ScoreRun,
    Source,
)
from networking_intel.db.session import create_database_engine, create_session_factory
from networking_intel.enrichment import ENRICHMENT_VERSION
from networking_intel.etl.load import file_sha256, json_hash, upsert_returning_id
from networking_intel.etl.schemas import is_valid_cnpj
from networking_intel.etl.transform import normalize_name
from networking_intel.scoring.config import ScoringConfig, load_config
from networking_intel.scoring.features import desk_unit_key

PIPELINE_NAME = "enrichment_scoring_load"
TRANSFORM_VERSION = "prompt5-load-v1"
P3_TRANSFORMATION = f"{ENRICHMENT_VERSION}: public-source enrichment (CVM Dados Abertos, Nominatim)"
DIRECTOR_ROLE = "Diretor responsável pela administração de carteiras (Res. CVM 21)"
SIGNAL_SOURCES = {
    "product_launches": "cvm_registro_fundo_classe",
    "net_flows": "cvm_inf_diario",
    "performance": "cvm_inf_diario",
    "expansion": "cvm_cad_adm_cart",
}
INPUT_FILES = (
    "data/enriched/source_manifest.csv",
    "data/enriched/legal_entities.csv",
    "data/enriched/people_public_registry.csv",
    "data/enriched/fund_classes.csv",
    "data/enriched/fund_metrics.csv",
    "data/enriched/fund_daily.parquet",
    "data/enriched/quality_report.json",
    "data/review/conflicts.csv",
    "data/scored/score_explanations.json",
    "data/scored/product_fit.csv",
    "data/scored/run_manifest.json",
    "data/scored/sanity_checks.csv",
    "config/scoring/opportunity_v1.yaml",
)


class LoadPreconditionError(RuntimeError):
    pass


@dataclass
class LoadContext:
    session: Session
    root: Path
    config: ScoringConfig
    config_sha: str
    loaded_at: datetime
    orgs: dict[str, uuid.UUID]
    sources: dict[str, uuid.UUID]  # raw sha256 -> source id
    source_rows: dict[str, dict[str, str]]  # raw sha256 -> manifest row
    latest_by_source: dict[str, str]  # source_id -> latest raw sha256
    units: dict[str, uuid.UUID]  # unit_key -> business unit id
    entity_units: dict[str, uuid.UUID]  # cnpj -> business unit id


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _none(value: str | None) -> str | None:
    return value if value not in (None, "", "None", "nan") else None


def _date(value: str | None) -> date | None:
    value = _none(value)
    return date.fromisoformat(value[:10]) if value else None


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _bool(value: str | None) -> bool:
    return value == "True"


def inputs_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in INPUT_FILES:
        digest.update(relative.encode())
        digest.update(file_sha256(root / relative).encode())
    return digest.hexdigest()


def _upsert_source(
    session: Session,
    *,
    key: str,
    source_type: str,
    locator: str,
    url: str | None,
    sha: str | None,
    collected_at: datetime,
) -> uuid.UUID:
    return upsert_returning_id(
        session,
        Source.__table__,
        {
            "source_key": key[:64],
            "source_type": source_type[:32],
            "source_locator": locator,
            "source_url": url,
            "file_sha256": sha,
            "collected_at": collected_at,
        },
        ["source_key"],
        ("source_type", "source_locator", "source_url", "file_sha256", "collected_at"),
    )


def load_sources(
    session: Session, root: Path
) -> tuple[dict[str, uuid.UUID], dict[str, dict[str, str]], dict[str, str]]:
    rows = _read_csv(root / "data/enriched/source_manifest.csv")
    ids: dict[str, uuid.UUID] = {}
    by_sha: dict[str, dict[str, str]] = {}
    latest: dict[str, str] = {}
    for row in rows:
        sha = row["raw_sha256"]
        ids[sha] = _upsert_source(
            session,
            key=f"{row['source_id']}:{sha[:40]}",
            source_type=row["source_id"],
            locator=f"{row['url']} (sha256 {sha})",
            url=row["url"],
            sha=sha,
            collected_at=_dt(row["fetched_at"]),
        )
        by_sha[sha] = row
        current = latest.get(row["source_id"])
        # Monthly CVM files: the lexicographically latest URL is the latest period.
        if current is None or (row["url"], row["fetched_at"]) > (
            by_sha[current]["url"],
            by_sha[current]["fetched_at"],
        ):
            latest[row["source_id"]] = sha
    return ids, by_sha, latest


def _source_as_of(ctx: LoadContext, source_id: str) -> date | None:
    quality = json.loads(
        (ctx.root / "data/enriched/quality_report.json").read_text(encoding="utf-8")
    )
    for item in quality["freshness"]:
        if item["source_id"] == source_id and item["data_as_of"]:
            return date.fromisoformat(item["data_as_of"])
    return None


def _evidence(
    ctx: LoadContext,
    sha: str,
    *,
    as_of: date | None,
    confidence: str,
    status: str | None,
    transformation: str = P3_TRANSFORMATION,
) -> dict[str, Any]:
    return {
        "source_id": ctx.sources[sha],
        "collected_at": _dt(ctx.source_rows[sha]["fetched_at"]),
        "as_of_date": as_of,
        "confidence": confidence,
        "verification_status": status,
        "transformation": transformation,
    }


def load_business_units(ctx: LoadContext, model_source: uuid.UUID) -> None:
    existing = {
        unit_key: unit_id
        for unit_id, unit_key in ctx.session.execute(select(BusinessUnit.id, BusinessUnit.unit_key))
    }
    for account_id, desks in ctx.config.bank_desks.items():
        for desk in desks:
            key = desk_unit_key(account_id, desk.key)
            if key in existing:
                # Existence already source-stated by the workbook: keep its evidence.
                unit_id = existing[key]
                ctx.session.execute(
                    update(BusinessUnit).where(BusinessUnit.id == unit_id).values(name=desk.name)
                )
            else:
                observed = bool(desk.entity_cnpjs)
                unit_id = upsert_returning_id(
                    ctx.session,
                    BusinessUnit.__table__,
                    {
                        "organization_id": ctx.orgs[account_id],
                        "unit_key": key,
                        "name": desk.name,
                        "unit_type": "mesa/área",
                        "mapping_status": "source_stated" if observed else "pending",
                        "source_id": model_source,
                        "collected_at": ctx.loaded_at,
                        "as_of_date": None,
                        "confidence": "medium" if observed else "low",
                        "verification_status": (
                            "entidades CVM mapeadas" if observed else "premissa do modelo de mesas"
                        ),
                        "transformation": f"{ctx.config.model_version}: bank desk catalogue",
                    },
                    ["organization_id", "unit_key"],
                    ("name",),
                )
            ctx.units[key] = unit_id
            for cnpj in desk.entity_cnpjs:
                ctx.entity_units[cnpj] = unit_id


def load_legal_entities(ctx: LoadContext) -> dict[str, uuid.UUID]:
    ids: dict[str, uuid.UUID] = {}
    rows = _read_csv(ctx.root / "data/enriched/legal_entities.csv")
    for row in rows:
        relation = row["relation"]
        values = {
            "organization_id": ctx.orgs[row["account_id"]],
            "business_unit_id": ctx.entity_units.get(row["cnpj"]),
            "cnpj": row["cnpj"],
            "relation": relation,
            "approval_status": row["approval_status"],
            "relation_evidence": row["relation_evidence"],
            "legal_name": row["legal_name"],
            "trade_name": _none(row["trade_name"]),
            "cvm_status": row["cvm_status"],
            "cvm_status_since": _date(row["cvm_status_since"]),
            "cvm_registration_date": _date(row["cvm_registration_date"]),
            "registration_category": _none(row["registration_category"]),
            "address_official": _none(row["address_official"]),
            "city": _none(row["city"]),
            "state": _none(row["state"]),
            "postal_code": _none(row["postal_code"]),
            "phone_official": _none(row["phone_official"]),
            "email_institutional": _none(row["email_institutional"]),
            "website_official": _none(row["website_official"]),
            **_evidence(
                ctx,
                row["raw_sha256"],
                as_of=_date(row["source_as_of"]),
                confidence="medium" if relation == "affiliate_manager" else "high",
                status=row["approval_status"],
            ),
        }
        entity_id = upsert_returning_id(
            ctx.session,
            LegalEntity.__table__,
            values,
            ["cnpj"],
            tuple(k for k in values if k != "cnpj"),
        )
        ids[row["cnpj"]] = entity_id
        load_entity_aliases(ctx, row)
        load_regulatory_office(ctx, row, entity_id)
    update_organizations(ctx, rows)
    return ids


def load_entity_aliases(ctx: LoadContext, row: dict[str, str]) -> None:
    """Registered names become canonical search aliases (exact normalised matches only)."""
    for alias, kind in (
        (row["legal_name"], "legal_name"),
        (_none(row["trade_name"]), "trade_name"),
    ):
        if not alias:
            continue
        upsert_returning_id(
            ctx.session,
            OrganizationAlias.__table__,
            {
                "organization_id": ctx.orgs[row["account_id"]],
                "alias": alias,
                "normalized_alias": normalize_name(alias),
                "alias_kind": kind,
                **_evidence(
                    ctx,
                    row["raw_sha256"],
                    as_of=_date(row["source_as_of"]),
                    confidence="high",
                    status=row["approval_status"],
                ),
            },
            ["organization_id", "normalized_alias", "alias_kind"],
            ("alias", "collected_at", "as_of_date", "confidence", "verification_status"),
        )


def load_regulatory_office(ctx: LoadContext, row: dict[str, str], entity_id: uuid.UUID) -> None:
    address = _none(row["address_official"])
    if not address:
        return
    status = row["geocode_status"]
    located = status in {"matched", "matched_approximate"} and _none(row["latitude"])
    precision = row["geocode_precision"] if located or status not in {"not_geocoded", ""} else None
    exact = located and row["geocode_is_exact"] == "True"
    confidence = "high" if exact else "medium" if precision == "street" else "low"
    geocode_sha = _none(row.get("geocode_raw_sha256"))
    values: dict[str, Any] = {
        "organization_id": ctx.orgs[row["account_id"]],
        "business_unit_id": ctx.entity_units.get(row["cnpj"]),
        "legal_entity_id": entity_id,
        "office_key": hashlib.sha256(f"regulatory|{row['cnpj']}|{address}".encode()).hexdigest(),
        "office_kind": "regulatory",
        "address_raw": address,
        "city": _none(row["city"]),
        "state": _none(row["state"]),
        "country_code": "BR",
        "location": (
            text(
                f"ST_SetSRID(ST_MakePoint({float(row['longitude'])}, {float(row['latitude'])}), 4326)"
            )
            if located
            else None
        ),
        "geocode_status": status or None,
        "geocode_precision": precision,
        "geocode_is_exact": bool(exact),
        "geocode_provider": _none(row.get("geocode_provider")),
        "geocoded_at": _dt(row["geocode_fetched_at"])
        if _none(row.get("geocode_fetched_at"))
        else None,
        "geocode_raw_sha256": geocode_sha,
        **_evidence(
            ctx,
            row["raw_sha256"],
            as_of=_date(row["source_as_of"]),
            confidence=confidence,
            status=f"endereço CVM; geocodificação {status or 'não executada'}",
        ),
    }
    upsert_returning_id(
        ctx.session,
        Office.__table__,
        values,
        ["office_key"],
        tuple(k for k in values if k != "office_key"),
    )


def update_organizations(ctx: LoadContext, rows: Sequence[dict[str, str]]) -> None:
    by_account: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_account.setdefault(row["account_id"], []).append(row)
    for account_id, entities in by_account.items():
        chosen = next((e for e in entities if e["relation"] == "bank_entity"), None) or next(
            (e for e in entities if e["relation"] == "primary_manager"), None
        )
        if chosen is None:
            continue
        org_id = ctx.orgs[account_id]
        ctx.session.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(legal_name=chosen["legal_name"], cnpj=chosen["cnpj"])
        )
        for field_name, value in (("legal_name", chosen["legal_name"]), ("cnpj", chosen["cnpj"])):
            evidence = _evidence(
                ctx,
                chosen["raw_sha256"],
                as_of=_date(chosen["source_as_of"]),
                confidence="high",
                status=chosen["approval_status"],
            )
            upsert_returning_id(
                ctx.session,
                FieldProvenance.__table__,
                {
                    "entity_type": "organization",
                    "entity_id": org_id,
                    "field_name": field_name,
                    "source_id": evidence["source_id"],
                    "source_locator": f"cad_adm_cart_pj.csv CNPJ {chosen['cnpj']}",
                    "collected_at": evidence["collected_at"],
                    "as_of_date": evidence["as_of_date"],
                    "confidence": "high",
                    "verification_status": chosen["approval_status"],
                    "transformation": P3_TRANSFORMATION,
                    "value_hash": json_hash(value),
                },
                ["entity_type", "entity_id", "field_name", "source_id"],
                (
                    "source_locator",
                    "collected_at",
                    "as_of_date",
                    "verification_status",
                    "value_hash",
                ),
            )


def load_people(ctx: LoadContext) -> int:
    rows = _read_csv(ctx.root / "data/enriched/people_public_registry.csv")
    for row in rows:
        values = {
            "organization_id": ctx.orgs[row["account_id"]],
            "business_unit_id": None,
            "full_name": row["full_name"],
            "role_title": DIRECTOR_ROLE,
            "linkedin_url": None,
            "public_email": None,
            "is_public_professional_data": True,
            **_evidence(
                ctx,
                row["raw_sha256"],
                as_of=_date(row["source_as_of"]),
                confidence="high",
                status="registro regulatório público",
            ),
        }
        upsert_returning_id(
            ctx.session,
            Person.__table__,
            values,
            ["organization_id", "full_name", "role_title"],
            ("collected_at", "as_of_date", "confidence", "verification_status", "transformation"),
        )
    return len(rows)


def _copy_frame(session: Session, table: str, frame: pl.DataFrame) -> None:
    """COPY a frame into a session-scoped TEMP table with text columns."""
    columns = ", ".join(f'"{name}" text' for name in frame.columns)
    session.execute(text(f"DROP TABLE IF EXISTS {table}"))
    session.execute(text(f"CREATE TEMP TABLE {table} ({columns}) ON COMMIT DROP"))
    buffer = io.BytesIO()
    frame.write_csv(buffer, include_header=False, null_value="")
    raw = session.connection().connection.driver_connection
    assert raw is not None, "a psycopg connection is required for COPY"
    with (
        raw.cursor() as cursor,
        cursor.copy(f"COPY {table} FROM STDIN WITH (FORMAT csv, NULL '')") as copy,
    ):
        copy.write(buffer.getvalue())


def load_funds(ctx: LoadContext) -> int:
    registro_sha = ctx.latest_by_source["cvm_registro_fundo_classe"]
    classes = (
        pl.read_csv(ctx.root / "data/enriched/fund_classes.csv", infer_schema_length=0)
        .sort(["class_cnpj", "is_active"], descending=[False, True])
        .unique(subset=["class_cnpj"], keep="first", maintain_order=True)
        .filter(pl.col("class_cnpj").map_elements(is_valid_cnpj, return_dtype=pl.Boolean))
    )
    units = pl.DataFrame(
        {
            "manager_cnpj": list(ctx.entity_units),
            "business_unit_id": [str(v) for v in ctx.entity_units.values()],
        },
        schema={"manager_cnpj": pl.Utf8, "business_unit_id": pl.Utf8},
    )
    orgs = pl.DataFrame(
        {"account_id": list(ctx.orgs), "organization_id": [str(v) for v in ctx.orgs.values()]}
    )
    frame = (
        classes.join(orgs, on="account_id", how="inner")
        .join(units, on="manager_cnpj", how="left")
        .select(
            "organization_id",
            "business_unit_id",
            "class_cnpj",
            "fund_cnpj",
            "manager_cnpj",
            "class_name",
            "fund_name",
            "fund_type",
            "class_type",
            "classification",
            "anbima_classification",
            "benchmark",
            "status",
            "is_active",
            "is_exclusive",
            "is_fund_of_funds",
            "allows_full_offshore",
            "fund_constitution_date",
            "target_investor",
            "administrator_name",
        )
    )
    _copy_frame(ctx.session, "tmp_funds", frame)
    evidence = _evidence(
        ctx,
        registro_sha,
        as_of=_source_as_of(ctx, "cvm_registro_fundo_classe"),
        confidence="high",
        status="registro CVM",
    )
    ctx.session.execute(
        text(
            """
            INSERT INTO funds (
                organization_id, business_unit_id, canonical_name, legal_name, cnpj, fund_cnpj,
                manager_cnpj, fund_type, class_type, classification, anbima_classification,
                benchmark, status, is_active, is_exclusive, is_fund_of_funds,
                allows_full_offshore, constitution_date, target_investor, administrator_name,
                asset_class, source_id, collected_at, as_of_date, confidence,
                verification_status, transformation
            )
            SELECT organization_id::uuid, NULLIF(business_unit_id, '')::uuid, class_name,
                   fund_name, class_cnpj, fund_cnpj, manager_cnpj, fund_type, class_type,
                   classification, anbima_classification, benchmark, status,
                   is_active = 'True', is_exclusive = 'True', is_fund_of_funds = 'True',
                   CASE allows_full_offshore WHEN 'True' THEN true WHEN 'False' THEN false END,
                   NULLIF(fund_constitution_date, '')::date, target_investor,
                   administrator_name, classification, :source_id, :collected_at, :as_of_date,
                   'high', :verification_status, :transformation
            FROM tmp_funds
            ON CONFLICT (cnpj) WHERE cnpj IS NOT NULL DO UPDATE SET
                organization_id = EXCLUDED.organization_id,
                business_unit_id = EXCLUDED.business_unit_id,
                canonical_name = EXCLUDED.canonical_name,
                legal_name = EXCLUDED.legal_name,
                fund_cnpj = EXCLUDED.fund_cnpj,
                manager_cnpj = EXCLUDED.manager_cnpj,
                fund_type = EXCLUDED.fund_type,
                class_type = EXCLUDED.class_type,
                classification = EXCLUDED.classification,
                anbima_classification = EXCLUDED.anbima_classification,
                benchmark = EXCLUDED.benchmark,
                status = EXCLUDED.status,
                is_active = EXCLUDED.is_active,
                is_exclusive = EXCLUDED.is_exclusive,
                is_fund_of_funds = EXCLUDED.is_fund_of_funds,
                allows_full_offshore = EXCLUDED.allows_full_offshore,
                constitution_date = EXCLUDED.constitution_date,
                target_investor = EXCLUDED.target_investor,
                administrator_name = EXCLUDED.administrator_name,
                asset_class = EXCLUDED.asset_class,
                source_id = EXCLUDED.source_id,
                collected_at = EXCLUDED.collected_at,
                as_of_date = EXCLUDED.as_of_date,
                updated_at = now()
            """
        ),
        evidence,
    )
    return frame.height


def load_daily_observations(ctx: LoadContext) -> int:
    frame = pl.read_parquet(ctx.root / "data/enriched/fund_daily.parquet").select(
        "class_cnpj",
        "subclass_id",
        "date",
        "quota",
        "nav_brl",
        "inflow_brl",
        "outflow_brl",
        "investors",
        "raw_sha256",
    )
    _copy_frame(ctx.session, "tmp_daily", frame)
    result = ctx.session.execute(
        text(
            """
            INSERT INTO fund_observations (
                fund_id, subclass_id, observation_date, nav_brl, quota_value, subscriptions_brl,
                redemptions_brl, investor_count, source_id, collected_at, as_of_date,
                confidence, verification_status, transformation
            )
            SELECT DISTINCT ON (f.id, t.subclass_id, t.date::date, s.id)
                   f.id, COALESCE(t.subclass_id, ''), t.date::date,
                   NULLIF(t.nav_brl, '')::numeric, NULLIF(t.quota, '')::numeric,
                   NULLIF(t.inflow_brl, '')::numeric, NULLIF(t.outflow_brl, '')::numeric,
                   NULLIF(t.investors, '')::integer, s.id, s.collected_at, t.date::date,
                   'high', 'informe diário CVM', :transformation
            FROM tmp_daily t
            JOIN funds f ON f.cnpj = t.class_cnpj
            JOIN sources s ON s.file_sha256 = t.raw_sha256
            ON CONFLICT (fund_id, subclass_id, observation_date, source_id) DO NOTHING
            """
        ),
        {"transformation": P3_TRANSFORMATION},
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def load_fund_metrics(ctx: LoadContext) -> int:
    metrics = pl.read_csv(ctx.root / "data/enriched/fund_metrics.csv", infer_schema_length=0)
    columns = [
        "class_cnpj",
        "subclass_id",
        "reference_date",
        "metric_version",
        "currency",
        "first_date",
        "last_date",
        "observations",
        "latest_nav_brl",
        "latest_investors",
        *[
            c
            for w in ("1m", "3m", "6m", "12m", "ytd")
            for c in (f"return_{w}", f"return_{w}_status")
        ],
        "net_flow_12m_brl",
        "net_flow_status",
        "volatility_12m",
        "max_drawdown_12m",
        "series_flags",
    ]
    _copy_frame(ctx.session, "tmp_metrics", metrics.select(columns))
    returns_sql = ", ".join(
        f"NULLIF(t.return_{w}, '')::numeric, NULLIF(t.return_{w}_status, '')"
        for w in ("1m", "3m", "6m", "12m", "ytd")
    )
    returns_cols = ", ".join(
        f"return_{w}, return_{w}_status" for w in ("1m", "3m", "6m", "12m", "ytd")
    )
    updates = ", ".join(
        f"{c} = EXCLUDED.{c}"
        for c in (
            "first_date",
            "last_date",
            "observations",
            "latest_nav_brl",
            "latest_investors",
            *[
                c
                for w in ("1m", "3m", "6m", "12m", "ytd")
                for c in (f"return_{w}", f"return_{w}_status")
            ],
            "net_flow_12m_brl",
            "net_flow_status",
            "volatility_12m",
            "max_drawdown_12m",
            "series_flags",
            "source_id",
        )
    )
    result = ctx.session.execute(
        text(
            f"""
            INSERT INTO fund_metrics (
                fund_id, subclass_id, reference_date, metric_version, currency, first_date,
                last_date, observations, latest_nav_brl, latest_investors, {returns_cols},
                net_flow_12m_brl, net_flow_status, volatility_12m, max_drawdown_12m,
                series_flags, source_id
            )
            SELECT f.id, COALESCE(t.subclass_id, ''), t.reference_date::date, t.metric_version,
                   t.currency, NULLIF(t.first_date, '')::date, NULLIF(t.last_date, '')::date,
                   t.observations::integer, NULLIF(t.latest_nav_brl, '')::numeric,
                   NULLIF(t.latest_investors, '')::numeric::integer, {returns_sql},
                   NULLIF(t.net_flow_12m_brl, '')::numeric, t.net_flow_status,
                   NULLIF(t.volatility_12m, '')::numeric, NULLIF(t.max_drawdown_12m, '')::numeric,
                   NULLIF(t.series_flags, ''), :source_id
            FROM tmp_metrics t
            JOIN funds f ON f.cnpj = t.class_cnpj
            ON CONFLICT (fund_id, subclass_id, reference_date, metric_version) DO UPDATE SET
                {updates}, updated_at = now()
            """
        ),
        {"source_id": ctx.sources[ctx.latest_by_source["cvm_inf_diario"]]},
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def load_conflicts(ctx: LoadContext) -> int:
    rows = _read_csv(ctx.root / "data/review/conflicts.csv")
    for row in rows:
        values = {
            "conflict_id": row["conflict_id"],
            "organization_id": ctx.orgs[row["account_id"]],
            "entity_cnpj": row["entity_cnpj"],
            "field": row["field"],
            "rule": row["rule"],
            "severity": row["severity"],
            "workbook_value": row["workbook_value"],
            "source_value": row["source_value"],
            "source_key": row["source_id"],
            "detected_at": _dt(row["detected_at"]),
            "resolution_status": row["resolution_status"],
            "resolved_by": _none(row["resolved_by"]),
            "resolved_at": _none(row["resolved_at"]),
            "resolution_note": _none(row["resolution_note"]),
        }
        statement = insert(cast(Table, DataConflict.__table__)).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=["conflict_id"],
            set_={k: statement.excluded[k] for k in values if k != "conflict_id"},
        )
        ctx.session.execute(statement)
    return len(rows)


def load_quality_report(ctx: LoadContext) -> None:
    payload = json.loads(
        (ctx.root / "data/enriched/quality_report.json").read_text(encoding="utf-8")
    )
    upsert_returning_id(
        ctx.session,
        QualityReport.__table__,
        {
            "version": payload["version"],
            "run_at": _dt(payload["run_at"]),
            "fund_reference_date": _date(payload["fund_reference_date"]),
            "payload": payload,
            "loaded_at": ctx.loaded_at,
        },
        ["run_at"],
        ("version", "fund_reference_date", "payload", "loaded_at"),
    )


def _unit_org(ctx: LoadContext, unit: dict[str, Any]) -> tuple[uuid.UUID, uuid.UUID | None]:
    return ctx.orgs[unit["account_id"]], ctx.units.get(unit["unit_key"])


def _signal_source(ctx: LoadContext, factor: dict[str, Any]) -> uuid.UUID:
    source = SIGNAL_SOURCES.get(factor["key"])
    if source:
        return ctx.sources[ctx.latest_by_source[source]]
    url = factor["evidence"][0].rsplit(": ", 1)[-1]
    return _upsert_source(
        ctx.session,
        key=f"curated_signal:{hashlib.sha256(url.encode()).hexdigest()[:40]}",
        source_type="curated_signal",
        locator="data/reference/commercial_signals.csv",
        url=url,
        sha=None,
        collected_at=ctx.loaded_at,
    )


def load_scores(ctx: LoadContext) -> dict[str, int]:
    explanations = json.loads(
        (ctx.root / "data/scored/score_explanations.json").read_text(encoding="utf-8")
    )
    manifest = json.loads((ctx.root / "data/scored/run_manifest.json").read_text(encoding="utf-8"))
    sanity = _read_csv(ctx.root / "data/scored/sanity_checks.csv")
    if manifest["config_sha256"] != ctx.config_sha:
        raise LoadPreconditionError(
            "scored outputs were produced with a different config; rerun scoring"
        )
    as_of = date.fromisoformat(manifest["as_of_date"])
    model_source = _upsert_source(
        ctx.session,
        key=f"opportunity_model:{ctx.config_sha[:40]}",
        source_type="model_config",
        locator=f"config/scoring/opportunity_v1.yaml ({ctx.config.model_version})",
        url=None,
        sha=ctx.config_sha,
        collected_at=ctx.loaded_at,
    )
    run_id = upsert_returning_id(
        ctx.session,
        ScoreRun.__table__,
        {
            "model_version": ctx.config.model_version,
            "config_sha256": ctx.config_sha,
            "as_of_date": as_of,
            "manifest": manifest,
            "limitations": explanations["limitations"],
            "sanity_checks": sanity,
            "loaded_at": ctx.loaded_at,
        },
        ["model_version", "config_sha256", "as_of_date"],
        ("manifest", "limitations", "sanity_checks", "loaded_at"),
    )
    ctx.session.execute(delete(OpportunityScore).where(OpportunityScore.score_run_id == run_id))
    ctx.session.execute(
        delete(ProductFit).where(
            (ProductFit.model_version == ctx.config.model_version)
            & (ProductFit.as_of_date == as_of)
        )
    )
    observed_at = datetime.combine(as_of, time.min, tzinfo=UTC)
    signals = 0
    products = 0
    for rank, unit in enumerate(explanations["units"], start=1):
        org_id, unit_id = _unit_org(ctx, unit)
        fit, timing = unit["fit"], unit["timing"]
        ctx.session.add(
            OpportunityScore(
                score_run_id=run_id,
                organization_id=org_id,
                business_unit_id=unit_id,
                unit_key=unit["unit_key"],
                unit_name=unit["unit_name"],
                rank=rank,
                tier=unit["tier"],
                evidence_mode=unit["evidence_mode"],
                priority_point=unit["priority_point"],
                priority_lower=unit["priority_lower"],
                priority_upper=unit["priority_upper"],
                fit_point=fit["point"],
                fit_lower=fit["lower"],
                fit_upper=fit["upper"],
                fit_coverage=fit["coverage"],
                fit_assumption_share=fit["assumption_share"],
                timing_point=timing["point"],
                timing_lower=timing["lower"],
                timing_upper=timing["upper"],
                timing_coverage=timing["coverage"],
                confidence=unit["confidence"],
                explanation={
                    "weights": {
                        "fit": ctx.config.weights("fit"),
                        "timing": ctx.config.weights("timing"),
                    },
                    "fit_contributions": fit["contributions"],
                    "timing_contributions": timing["contributions"],
                    "confidence_components": unit["confidence_components"],
                    "factors": unit["factors"],
                    "reasons": unit["reasons"],
                    "products": unit["products"],
                },
            )
        )
        for product in unit["products"]:
            ctx.session.add(
                ProductFit(
                    organization_id=org_id,
                    business_unit_id=unit_id,
                    product_code=product["product_code"],
                    fit_status="candidate",
                    rationale=product["rationale"],
                    basis=product["basis"],
                    model_version=ctx.config.model_version,
                    source_id=model_source,
                    collected_at=ctx.loaded_at,
                    as_of_date=as_of,
                    confidence="low",
                    verification_status="hipótese de workflow",
                    transformation=f"{ctx.config.model_version}: product rules",
                )
            )
            products += 1
        for factor in unit["factors"]:
            if factor["group"] != "timing" or factor["value"] is None:
                continue
            values = {
                "organization_id": org_id,
                "business_unit_id": unit_id,
                "signal_type": factor["key"],
                "observed_at": observed_at,
                "expires_at": observed_at + timedelta(days=365),
                "payload": {
                    "unit_key": unit["unit_key"],
                    "label": factor["label"],
                    "value": factor["value"],
                    "status": factor["status"],
                    "raw": factor["raw"],
                    "explanation": factor["explanation"],
                    "evidence": factor["evidence"],
                    "model_version": ctx.config.model_version,
                },
                "source_id": _signal_source(ctx, factor),
                "collected_at": ctx.loaded_at,
                "as_of_date": as_of,
                "confidence": "high" if factor["status"] == "observed" else "medium",
                "verification_status": factor["status"],
                "transformation": f"{ctx.config.model_version}: timing factor",
            }
            statement = insert(cast(Table, CommercialSignal.__table__)).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[
                    "organization_id",
                    "business_unit_id",
                    "signal_type",
                    "observed_at",
                    "source_id",
                ],
                set_={
                    k: statement.excluded[k]
                    for k in (
                        "expires_at",
                        "payload",
                        "collected_at",
                        "confidence",
                        "verification_status",
                    )
                },
            )
            ctx.session.execute(statement)
            signals += 1
    ctx.session.flush()
    return {"units": len(explanations["units"]), "products": products, "signals": signals}


def _start_run(session: Session, input_hash: str, started_at: datetime) -> uuid.UUID:
    values = {
        "pipeline_name": PIPELINE_NAME,
        "input_sha256": input_hash,
        "transform_version": TRANSFORM_VERSION,
        "status": "running",
        "started_at": started_at,
        "completed_at": None,
        "source_row_count": 0,
        "staged_row_count": 0,
        "curated_row_count": 0,
        "error_message": None,
    }
    return upsert_returning_id(
        session,
        IngestionRun.__table__,
        values,
        ["pipeline_name", "input_sha256", "transform_version"],
        tuple(k for k in values if k not in {"pipeline_name", "input_sha256", "transform_version"}),
    )


def run_enriched_load(
    root: Path, database_url: str, *, engine: Engine | None = None
) -> dict[str, Any]:
    missing = [relative for relative in INPUT_FILES if not (root / relative).exists()]
    if missing:
        raise LoadPreconditionError(f"missing inputs (run Prompts 3 and 4 first): {missing}")
    config, config_sha = load_config(root / "config/scoring/opportunity_v1.yaml")
    input_hash = inputs_sha256(root)
    started_at = datetime.now(UTC)
    database_engine = engine or create_database_engine(database_url)
    session_factory: sessionmaker[Session] = create_session_factory(database_engine)

    with session_factory.begin() as session:
        orgs = {
            account_id: org_id
            for org_id, account_id in session.execute(
                select(Organization.id, Organization.account_id)
            )
        }
        if len(orgs) < 12:
            raise LoadPreconditionError("organizations missing: run the Prompt 2 ETL first")
        run_id = _start_run(session, input_hash, started_at)

    counts: dict[str, Any] = {}
    try:
        with session_factory.begin() as session:
            sources, source_rows, latest = load_sources(session, root)
            ctx = LoadContext(
                session=session,
                root=root,
                config=config,
                config_sha=config_sha,
                loaded_at=started_at,
                orgs=orgs,
                sources=sources,
                source_rows=source_rows,
                latest_by_source=latest,
                units={},
                entity_units={},
            )
            model_source = _upsert_source(
                session,
                key=f"opportunity_model:{config_sha[:40]}",
                source_type="model_config",
                locator=f"config/scoring/opportunity_v1.yaml ({config.model_version})",
                url=None,
                sha=config_sha,
                collected_at=started_at,
            )
            load_business_units(ctx, model_source)
            counts["legal_entities"] = len(load_legal_entities(ctx))
            counts["people"] = load_people(ctx)
            counts["funds"] = load_funds(ctx)
            counts["fund_observations_inserted"] = load_daily_observations(ctx)
            counts["fund_metrics"] = load_fund_metrics(ctx)
            counts["conflicts"] = load_conflicts(ctx)
            load_quality_report(ctx)
            counts["scores"] = load_scores(ctx)
            session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="complete",
                    completed_at=datetime.now(UTC),
                    source_row_count=len(sources),
                    staged_row_count=counts["funds"],
                    curated_row_count=counts["funds"] + counts["legal_entities"],
                    error_message=None,
                )
            )
    except Exception as exc:
        with session_factory.begin() as session:
            session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="failed",
                    completed_at=datetime.now(UTC),
                    error_message=type(exc).__name__ + ": " + str(exc)[:500],
                )
            )
        raise
    return {"run_id": str(run_id), "input_sha256": input_hash, **counts}


def main() -> int:
    from networking_intel.config import get_settings

    result = run_enriched_load(Path("."), get_settings().database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
