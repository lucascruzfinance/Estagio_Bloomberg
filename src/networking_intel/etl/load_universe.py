"""Load the territory universe snapshot (data/universe/) into PostgreSQL.

Idempotent by replacement: inside one transaction every universe table is truncated
and reloaded through COPY, so two loads of the same snapshot leave the same rows and a
newer snapshot never leaves stale rows behind. The commercial status table
(crm_status) is never touched. Requires the enrichment load (sources, organizations).
"""

from __future__ import annotations

import csv
import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from networking_intel.db.session import create_database_engine, create_session_factory
from networking_intel.etl.load import file_sha256
from networking_intel.etl.load_enriched import _copy_frame, _dt, _upsert_source

SNAPSHOT = Path("data/universe")
UNIVERSE_TABLES = (
    "buildings",
    "benchmarks",
    "bank_financials",
    "bank_institutions",
    "fund_registry_events",
    "fund_laminas",
    "fund_profile_monthly",
    "fund_holdings_summary",
    "manager_monthly",
    "fund_monthly",
    "fund_daily",
    "universe_fund_classes",
    "curated_account_entities",
    "curated_accounts",
    "group_memberships",
    "universe_entities",
    "economic_groups",
)
INPUT_FILES = (
    "entities.csv",
    "economic_groups.csv",
    "group_memberships.csv",
    "curated_accounts.csv",
    "curated_account_entities.csv",
    "fund_classes.parquet",
    "fund_daily_curated.parquet",
    "fund_monthly.parquet",
    "manager_monthly.parquet",
    "fund_holdings.csv",
    "fund_profiles.csv",
    "fund_laminas.csv",
    "fund_events.csv",
    "bank_institutions.csv",
    "bank_financials.parquet",
    "benchmarks.csv",
    "buildings.csv",
    "source_manifest.csv",
    "quality_report.json",
)


class UniverseLoadError(RuntimeError):
    pass


def _csv(path: Path) -> pl.DataFrame:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), [])
    if not header:
        return pl.DataFrame()
    return pl.read_csv(path, infer_schema_length=0, encoding="utf8")


def _frame(root: Path, name: str) -> pl.DataFrame:
    path = root / SNAPSHOT / name
    frame = _csv(path) if name.endswith(".csv") else pl.read_parquet(path)
    return frame.with_columns(pl.all().cast(pl.Utf8)) if frame.width else frame


# SQL expressions over the all-text temp table; {c} is the quoted column.
TEXT = "NULLIF(t.{c}, '')"
KEEP = "COALESCE(t.{c}, '')"
DATE = "NULLIF(t.{c}, '')::date"
NUM = "round(NULLIF(t.{c}, '')::numeric, 2)"
FLOAT = "NULLIF(t.{c}, '')::double precision"
INT = "NULLIF(t.{c}, '')::numeric::bigint"
BOOL = "lower(NULLIF(t.{c}, ''))::boolean"


def _insert(
    session: Session,
    table: str,
    frame: pl.DataFrame,
    columns: dict[str, str],
    *,
    extra: dict[str, str] | None = None,
    distinct_on: tuple[str, ...] = (),
    source_column: str | None = "raw_sha256",
    source_required: bool = True,
) -> int:
    """COPY the frame and insert it with casts; source_id comes from the raw SHA-256.

    distinct_on drops duplicate keys deterministically (sorted, first row wins)."""
    if frame.is_empty():
        return 0
    if distinct_on:
        frame = frame.sort(frame.columns, nulls_last=True).unique(
            subset=list(distinct_on), keep="first", maintain_order=True
        )
    temp = f"tmp_u_{table}"
    _copy_frame(session, temp, frame)
    targets = list(columns) + list(extra or {})
    expressions = [expr.format(c=f'"{name}"') for name, expr in columns.items()]
    expressions += list((extra or {}).values())
    join = ""
    if source_column:
        targets.append("source_id")
        expressions.append("m.id")
        join = (
            f"{'JOIN' if source_required else 'LEFT JOIN'} tmp_u_source_map m "
            f'ON m.sha = t."{source_column}"'
        )
    result = session.execute(
        text(
            f"INSERT INTO {table} ({', '.join(targets)}) "
            f"SELECT {', '.join(expressions)} FROM {temp} t {join}"
        )
    )
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


def _source_map(session: Session, root: Path) -> int:
    rows = list(
        csv.DictReader((root / SNAPSHOT / "source_manifest.csv").open(encoding="utf-8-sig"))
    )
    ids: dict[str, uuid.UUID] = {}
    for row in rows:
        ids[row["raw_sha256"]] = _upsert_source(
            session,
            key=f"{row['source_id']}:{row['raw_sha256'][:40]}",
            source_type=row["source_id"],
            locator=f"{row['url']} (sha256 {row['raw_sha256']})",
            url=row["url"],
            sha=row["raw_sha256"],
            collected_at=_dt(row["fetched_at"]),
        )
    session.execute(text("DROP TABLE IF EXISTS tmp_u_source_map"))
    session.execute(
        text("CREATE TEMP TABLE tmp_u_source_map (sha text PRIMARY KEY, id uuid) ON COMMIT DROP")
    )
    if ids:
        session.execute(
            text("INSERT INTO tmp_u_source_map (sha, id) VALUES (:sha, :id)"),
            [{"sha": sha, "id": source_id} for sha, source_id in ids.items()],
        )
    return len(ids)


def inputs_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for name in INPUT_FILES:
        digest.update(name.encode())
        digest.update(file_sha256(root / SNAPSHOT / name).encode())
    return digest.hexdigest()


def load_snapshot(session: Session, root: Path) -> dict[str, int]:
    counts: dict[str, int] = {"sources": _source_map(session, root)}
    session.execute(text(f"TRUNCATE {', '.join(UNIVERSE_TABLES)}"))
    point = (
        "CASE WHEN NULLIF(t.latitude, '') IS NOT NULL THEN ST_SetSRID(ST_MakePoint("
        "t.longitude::double precision, t.latitude::double precision), 4326) END"
    )
    counts["economic_groups"] = _insert(
        session,
        "economic_groups",
        _frame(root, "economic_groups.csv"),
        {"group_key": TEXT, "group_name": TEXT, "basis": TEXT, "members": INT},
        source_column=None,
    )
    counts["universe_entities"] = _insert(
        session,
        "universe_entities",
        _frame(root, "entities.csv"),
        {
            "cnpj": TEXT,
            "cnpj_root": TEXT,
            "legal_name": TEXT,
            "trade_name": TEXT,
            "primary_kind": TEXT,
            "side": TEXT,
            "coverage_tier": TEXT,
            "curated_account_key": TEXT,
            "registration_category": TEXT,
            "registration_date": DATE,
            "street": TEXT,
            "complement": TEXT,
            "district": TEXT,
            "city": TEXT,
            "state": TEXT,
            "postal_code": TEXT,
            "centre": TEXT,
            "centre_basis": TEXT,
            "building_key": TEXT,
            "geocode_precision": TEXT,
            "geocode_is_exact": BOOL,
            "geocode_status": TEXT,
            "h3_r8": TEXT,
            "h3_r9": TEXT,
            "phone_official": TEXT,
            "website_official": TEXT,
            "group_key": TEXT,
            "ifdata_cod_inst": TEXT,
            "ifdata_conglomerate": TEXT,
            "active_classes": INT,
            "selected_classes": INT,
            "nav_registry_non_fic_brl": NUM,
            "nav_daily_report_brl": NUM,
            "nav_daily_report_month": DATE,
            "funds_administered": INT,
            "nav_administered_brl": NUM,
            "as_of_date": DATE,
        },
        extra={"kinds": "string_to_array(t.kinds, ';')", "location": point},
    )
    counts["group_memberships"] = _insert(
        session,
        "group_memberships",
        _frame(root, "group_memberships.csv"),
        {"cnpj": TEXT, "group_key": TEXT, "basis": TEXT, "approval_status": TEXT, "evidence": TEXT},
        source_column=None,
    )
    counts["curated_accounts"] = _insert(
        session,
        "curated_accounts",
        _frame(root, "curated_accounts.csv"),
        {
            "account_key": TEXT,
            "display_name": TEXT,
            "wave": TEXT,
            "side": TEXT,
            "segment": TEXT,
            "rationale": TEXT,
            "primary_cnpj": TEXT,
            "approval_status": TEXT,
        },
        extra={
            "organization_id": "(SELECT o.id FROM organizations o WHERE o.account_id = t.account_key)"
        },
        source_column=None,
    )
    counts["curated_account_entities"] = _insert(
        session,
        "curated_account_entities",
        _frame(root, "curated_account_entities.csv"),
        {
            "account_key": TEXT,
            "cnpj": TEXT,
            "relation": TEXT,
            "business_unit": TEXT,
            "approval_status": TEXT,
            "relation_evidence": TEXT,
        },
        source_column=None,
    )
    registry_sha = _latest_sha(root, "cvm_registro_fundo_classe")
    classes = _frame(root, "fund_classes.parquet").with_columns(
        pl.lit(registry_sha).alias("raw_sha256")
    )
    counts["universe_fund_classes"] = _insert(
        session,
        "universe_fund_classes",
        classes,
        {
            "class_cnpj": TEXT,
            "fund_cnpj": TEXT,
            "manager_cnpj": TEXT,
            "administrator_cnpj": TEXT,
            "custodian_cnpj": TEXT,
            "class_name": TEXT,
            "fund_type": TEXT,
            "class_type": TEXT,
            "classification": TEXT,
            "anbima_classification": TEXT,
            "benchmark": TEXT,
            "condominium": TEXT,
            "is_exclusive": BOOL,
            "is_fic": BOOL,
            "target_investor": TEXT,
            "status": TEXT,
            "is_active": BOOL,
            "is_selected": BOOL,
            "registry_nav_brl": NUM,
            "registry_nav_date": DATE,
            "constitution_date": DATE,
            "class_start_date": DATE,
            "cancel_date": DATE,
            "allows_full_offshore": BOOL,
            "nav_anomaly": BOOL,
            "curated_account_key": TEXT,
        },
    )
    series_columns = {
        "class_cnpj": TEXT,
        "subclass_id": KEEP,
    }
    counts["fund_daily"] = _insert(
        session,
        "fund_daily",
        _frame(root, "fund_daily_curated.parquet"),
        {
            **series_columns,
            "date": DATE,
            "quota": FLOAT,
            "nav_brl": NUM,
            "inflow_brl": NUM,
            "outflow_brl": NUM,
            "investors": INT,
        },
    )
    counts["fund_monthly"] = _insert(
        session,
        "fund_monthly",
        _frame(root, "fund_monthly.parquet"),
        {
            **series_columns,
            "month": DATE,
            "first_date": DATE,
            "last_date": DATE,
            "quota_first": FLOAT,
            "quota_end": FLOAT,
            "nav_end_brl": NUM,
            "investors_end": INT,
            "inflow_brl": NUM,
            "outflow_brl": NUM,
            "days_reported": INT,
        },
    )
    counts["manager_monthly"] = _insert(
        session,
        "manager_monthly",
        _frame(root, "manager_monthly.parquet"),
        {
            "manager_cnpj": TEXT,
            "month": DATE,
            "nav_end_brl": NUM,
            "inflow_brl": NUM,
            "outflow_brl": NUM,
            "investors_end": INT,
            "classes_reporting": INT,
        },
    )
    month_of_period = "to_date(t.period || '01', 'YYYYMMDD')"
    counts["fund_holdings_summary"] = _insert(
        session,
        "fund_holdings_summary",
        _frame(root, "fund_holdings.csv"),
        {
            "class_cnpj": TEXT,
            "as_of_date": DATE,
            "nav_brl": NUM,
            "positions": INT,
            "derivative_positions": INT,
            "top10_share": FLOAT,
            **{
                f"pct_{c}": FLOAT
                for c in (
                    "public_bonds_repo",
                    "fund_quotas",
                    "equities",
                    "private_credit",
                    "derivatives",
                    "foreign",
                    "cash",
                    "other",
                    "confidential",
                )
            },
        },
        extra={"month": month_of_period},
    )
    counts["fund_profile_monthly"] = _insert(
        session,
        "fund_profile_monthly",
        _frame(root, "fund_profiles.csv"),
        {
            "class_cnpj": TEXT,
            "as_of_date": DATE,
            **{
                f"pct_nav_{g}": FLOAT
                for g in (
                    "retail",
                    "private_banking",
                    "institutional",
                    "funds",
                    "non_resident",
                    "distributors",
                    "other",
                )
            },
            "investors": INT,
            "derivatives_notional_brl": NUM,
            "var_pct": FLOAT,
            "var_model": TEXT,
            "stress_pct": FLOAT,
            "private_credit_pct": FLOAT,
            "largest_investor_pct": FLOAT,
            "days_to_liquidate_half": FLOAT,
        },
        distinct_on=("class_cnpj", "as_of_date"),
    )
    counts["fund_laminas"] = _insert(
        session,
        "fund_laminas",
        _frame(root, "fund_laminas.csv"),
        {
            "class_cnpj": TEXT,
            "subclass_id": KEEP,
            "as_of_date": DATE,
            **{
                c: TEXT
                for c in (
                    "trade_name",
                    "max_foreign_pct",
                    "max_private_credit_pct",
                    "max_leverage_pct",
                    "admin_fee_pct",
                    "performance_fee",
                    "min_initial_investment_brl",
                    "risk_class",
                    "benchmark",
                    "redemption_payment_days",
                )
            },
        },
        distinct_on=("class_cnpj", "subclass_id"),
    )
    counts["fund_registry_events"] = _insert(
        session,
        "fund_registry_events",
        _frame(root, "fund_events.csv"),
        {
            "fund_cnpj": TEXT,
            "manager_cnpj": TEXT,
            "event_type": TEXT,
            "event_date": DATE,
            "counterparty_cnpj": TEXT,
            "counterparty_name": TEXT,
        },
        distinct_on=("fund_cnpj", "manager_cnpj", "event_type", "event_date"),
    )
    counts["bank_institutions"] = _insert(
        session,
        "bank_institutions",
        _frame(root, "bank_institutions.csv"),
        {
            "cod_inst": TEXT,
            "name": TEXT,
            "is_conglomerate": BOOL,
            "tcb": TEXT,
            "td": TEXT,
            "tc": TEXT,
            "segment": TEXT,
            "sr": TEXT,
            "state": TEXT,
            "city": TEXT,
            "financial_conglomerate": TEXT,
            "prudential_conglomerate": TEXT,
            "leader_cnpj_root": TEXT,
            "activity_start": TEXT,
            "period": TEXT,
        },
    )
    counts["bank_financials"] = _insert(
        session,
        "bank_financials",
        _frame(root, "bank_financials.parquet"),
        {
            "cod_inst": TEXT,
            "period": TEXT,
            "report": TEXT,
            "report_name": TEXT,
            "group_name": KEEP,
            "account_code": KEEP,
            "metric": TEXT,
            "value": NUM,
        },
        distinct_on=("cod_inst", "period", "report", "account_code"),
    )
    counts["benchmarks"] = _insert(
        session,
        "benchmarks",
        _frame(root, "benchmarks.csv"),
        {"series_key": TEXT, "date": DATE, "value": FLOAT, "unit": TEXT, "sgs_code": INT},
        distinct_on=("series_key", "date"),
    )
    counts["buildings"] = _insert(
        session,
        "buildings",
        _frame(root, "buildings.csv"),
        {
            "building_key": TEXT,
            "tenants": INT,
            "precision": TEXT,
            "is_exact": BOOL,
            "status": TEXT,
            "display_name": TEXT,
            "h3_r8": TEXT,
            "h3_r9": TEXT,
            "provider": TEXT,
            "attribution": TEXT,
            "fetched_at": "NULLIF(t.fetched_at, '')::timestamptz",
        },
        extra={"location": point},
        source_required=False,
    )
    return counts


def _latest_sha(root: Path, source_id: str) -> str:
    rows = [
        row
        for row in csv.DictReader(
            (root / SNAPSHOT / "source_manifest.csv").open(encoding="utf-8-sig")
        )
        if row["source_id"] == source_id
    ]
    if not rows:
        raise UniverseLoadError(f"{source_id} ausente do manifesto do universo")
    return max(rows, key=lambda row: row["fetched_at"])["raw_sha256"]


def expected_counts(root: Path) -> dict[str, int]:
    report = json.loads((root / SNAPSHOT / "quality_report.json").read_text(encoding="utf-8"))
    counts = report["counts"]
    return {
        "universe_entities": counts["entities"],
        "curated_accounts": counts["curated_accounts"],
        "curated_account_entities": counts["curated_entities"],
        "universe_fund_classes": counts["classes"],
        "fund_daily": counts["daily_rows_curated"],
        "fund_monthly": counts["monthly_rows"],
        "manager_monthly": counts["manager_month_rows"],
        "bank_institutions": counts["ifdata_institutions"],
        "benchmarks": counts["benchmark_points"],
        "buildings": counts["buildings"],
    }


def run_universe_load(
    root: Path, database_url: str, *, engine: Engine | None = None
) -> dict[str, Any]:
    missing = [name for name in INPUT_FILES if not (root / SNAPSHOT / name).exists()]
    if missing:
        raise UniverseLoadError(f"snapshot do universo incompleto (rode o pipeline): {missing}")
    database_engine = engine or create_database_engine(database_url)
    session_factory: sessionmaker[Session] = create_session_factory(database_engine)
    started = datetime.now(UTC)
    with session_factory.begin() as session:
        counts = load_snapshot(session, root)
        expected = expected_counts(root)
        mismatched = {k: (counts[k], v) for k, v in expected.items() if counts[k] != v}
        if mismatched:
            raise UniverseLoadError(f"contagens divergentes (carregado, esperado): {mismatched}")
    return {
        "input_sha256": inputs_sha256(root),
        "seconds": round((datetime.now(UTC) - started).total_seconds(), 1),
        **counts,
    }


def main() -> int:
    from networking_intel.config import get_settings

    result = run_universe_load(Path("."), get_settings().database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
