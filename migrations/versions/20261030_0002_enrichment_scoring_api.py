"""Enrichment, scoring and API read models (Prompts 3-5).

Revision ID: 20261030_0002
Revises: 20261029_0001
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry  # noqa: F401  (kept for autogenerate parity)
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0002"
down_revision: str | None = "20261029_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONFIDENCE_CHECK = "confidence IN ('high', 'medium', 'low', 'blocked')"
PRECISIONS = "('address', 'street', 'neighbourhood', 'city', 'unknown', 'none')"


def uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def fk(name: str, table: str, *, nullable: bool, ondelete: str) -> sa.Column[object]:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(f"{table}.id", ondelete=ondelete),
        nullable=nullable,
    )


def evidence_columns() -> list[sa.Column[object]]:
    return [
        fk("source_id", "sources", nullable=False, ondelete="RESTRICT"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("verification_status", sa.Text(), nullable=True),
        sa.Column("transformation", sa.Text(), nullable=False),
    ]


def score_columns(prefix: str) -> list[sa.Column[object]]:
    return [
        sa.Column(f"{prefix}_point", sa.Numeric(6, 2), nullable=True),
        sa.Column(f"{prefix}_lower", sa.Numeric(6, 2), nullable=False),
        sa.Column(f"{prefix}_upper", sa.Numeric(6, 2), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "legal_entities",
        uuid_pk(),
        fk("organization_id", "organizations", nullable=False, ondelete="CASCADE"),
        fk("business_unit_id", "business_units", nullable=True, ondelete="SET NULL"),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("relation", sa.String(32), nullable=False),
        sa.Column("approval_status", sa.String(32), nullable=False),
        sa.Column("relation_evidence", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("trade_name", sa.Text(), nullable=True),
        sa.Column("cvm_status", sa.Text(), nullable=False),
        sa.Column("cvm_status_since", sa.Date(), nullable=True),
        sa.Column("cvm_registration_date", sa.Date(), nullable=True),
        sa.Column("registration_category", sa.Text(), nullable=True),
        sa.Column("address_official", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("postal_code", sa.String(8), nullable=True),
        sa.Column("phone_official", sa.String(20), nullable=True),
        sa.Column("email_institutional", sa.Text(), nullable=True),
        sa.Column("website_official", sa.Text(), nullable=True),
        *evidence_columns(),
        *timestamps(),
        sa.UniqueConstraint("cnpj", name="uq_legal_entity_cnpj"),
        sa.CheckConstraint("is_valid_cnpj(cnpj)", name="ck_legal_entity_cnpj"),
        sa.CheckConstraint(
            "relation IN ('primary_manager', 'affiliate_manager', 'bank_entity')",
            name="ck_legal_entity_relation",
        ),
        sa.CheckConstraint(
            "approval_status IN ('pending_human_review', 'approved', 'rejected')",
            name="ck_legal_entity_approval",
        ),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_legal_entity_confidence"),
    )
    op.create_index("ix_legal_entity_org", "legal_entities", ["organization_id"])

    op.add_column(
        "offices", fk("legal_entity_id", "legal_entities", nullable=True, ondelete="SET NULL")
    )
    op.add_column(
        "offices",
        sa.Column("office_kind", sa.String(16), nullable=False, server_default="workbook"),
    )
    op.add_column("offices", sa.Column("geocode_status", sa.String(32), nullable=True))
    op.add_column("offices", sa.Column("geocode_precision", sa.String(16), nullable=True))
    op.add_column(
        "offices",
        sa.Column("geocode_is_exact", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("offices", sa.Column("geocode_provider", sa.Text(), nullable=True))
    op.add_column("offices", sa.Column("geocoded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("offices", sa.Column("geocode_raw_sha256", sa.String(64), nullable=True))
    op.create_check_constraint(
        "ck_office_kind", "offices", "office_kind IN ('workbook', 'regulatory')"
    )
    op.create_check_constraint(
        "ck_office_precision",
        "offices",
        f"geocode_precision IS NULL OR geocode_precision IN {PRECISIONS}",
    )
    op.create_check_constraint(
        "ck_office_exact_requires_address",
        "offices",
        "NOT geocode_is_exact OR (geocode_precision = 'address' AND location IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_office_location_has_precision",
        "offices",
        "location IS NULL OR geocode_precision IS NOT NULL",
    )
    op.create_index("ix_office_kind_precision", "offices", ["office_kind", "geocode_precision"])

    op.drop_constraint("uq_fund_org_name", "funds", type_="unique")
    fund_columns = [
        sa.Column("fund_cnpj", sa.String(14), nullable=True),
        sa.Column("manager_cnpj", sa.String(14), nullable=True),
        fk("business_unit_id", "business_units", nullable=True, ondelete="SET NULL"),
        sa.Column("fund_type", sa.Text(), nullable=True),
        sa.Column("class_type", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("anbima_classification", sa.Text(), nullable=True),
        sa.Column("benchmark", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_exclusive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_fund_of_funds", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allows_full_offshore", sa.Boolean(), nullable=True),
        sa.Column("constitution_date", sa.Date(), nullable=True),
        sa.Column("target_investor", sa.Text(), nullable=True),
        sa.Column("administrator_name", sa.Text(), nullable=True),
    ]
    for column in fund_columns:
        op.add_column("funds", column)
    op.create_index("ix_fund_org_active", "funds", ["organization_id", "is_active"])
    op.create_index("ix_fund_classification", "funds", ["classification"])

    op.add_column(
        "fund_observations",
        sa.Column("subclass_id", sa.String(32), nullable=False, server_default=""),
    )
    op.drop_constraint("uq_fund_observation_source", "fund_observations", type_="unique")
    op.create_unique_constraint(
        "uq_fund_observation_source",
        "fund_observations",
        ["fund_id", "subclass_id", "observation_date", "source_id"],
    )
    op.drop_index("ix_fund_observation_date", table_name="fund_observations")
    op.create_index(
        "ix_fund_observation_date",
        "fund_observations",
        ["fund_id", "subclass_id", "observation_date"],
    )

    op.create_table(
        "fund_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        fk("fund_id", "funds", nullable=False, ondelete="CASCADE"),
        sa.Column("subclass_id", sa.String(32), nullable=False, server_default=""),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("metric_version", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("first_date", sa.Date(), nullable=True),
        sa.Column("last_date", sa.Date(), nullable=True),
        sa.Column("observations", sa.Integer(), nullable=False),
        sa.Column("latest_nav_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column("latest_investors", sa.Integer(), nullable=True),
        *[
            column
            for window in ("1m", "3m", "6m", "12m", "ytd")
            for column in (
                sa.Column(f"return_{window}", sa.Numeric(14, 8), nullable=True),
                sa.Column(f"return_{window}_status", sa.String(48), nullable=True),
            )
        ],
        sa.Column("net_flow_12m_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column("net_flow_status", sa.String(48), nullable=False),
        sa.Column("volatility_12m", sa.Numeric(14, 8), nullable=True),
        sa.Column("max_drawdown_12m", sa.Numeric(14, 8), nullable=True),
        sa.Column("series_flags", sa.Text(), nullable=True),
        fk("source_id", "sources", nullable=False, ondelete="RESTRICT"),
        *timestamps(),
        sa.UniqueConstraint(
            "fund_id", "subclass_id", "reference_date", "metric_version", name="uq_fund_metric"
        ),
        sa.CheckConstraint("currency = 'BRL'", name="ck_fund_metric_currency"),
        sa.CheckConstraint(
            "return_12m IS NULL OR return_12m_status = 'ok'", name="ck_fund_metric_return_status"
        ),
    )
    op.create_index("ix_fund_metric_reference", "fund_metrics", ["reference_date", "fund_id"])

    op.add_column("product_fit", sa.Column("basis", sa.String(48), nullable=True))
    op.add_column("product_fit", sa.Column("model_version", sa.String(32), nullable=True))
    op.drop_constraint("uq_product_fit", "product_fit", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_product_fit ON product_fit "
        "(organization_id, business_unit_id, product_code, as_of_date) NULLS NOT DISTINCT"
    )

    op.drop_constraint("uq_signal_source", "commercial_signals", type_="unique")
    op.execute(
        "CREATE UNIQUE INDEX uq_signal_source ON commercial_signals "
        "(organization_id, business_unit_id, signal_type, observed_at, source_id) "
        "NULLS NOT DISTINCT"
    )

    op.drop_table("scores")
    op.create_table(
        "score_runs",
        uuid_pk(),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("config_sha256", sa.String(64), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("limitations", postgresql.JSONB(), nullable=False),
        sa.Column("sanity_checks", postgresql.JSONB(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("model_version", "config_sha256", "as_of_date", name="uq_score_run"),
        sa.CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'", name="ck_score_run_sha"),
    )
    op.create_table(
        "opportunity_scores",
        uuid_pk(),
        fk("score_run_id", "score_runs", nullable=False, ondelete="CASCADE"),
        fk("organization_id", "organizations", nullable=False, ondelete="CASCADE"),
        fk("business_unit_id", "business_units", nullable=True, ondelete="CASCADE"),
        sa.Column("unit_key", sa.String(160), nullable=False),
        sa.Column("unit_name", sa.Text(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(64), nullable=False),
        sa.Column("evidence_mode", sa.String(16), nullable=False),
        *score_columns("priority"),
        *score_columns("fit"),
        sa.Column("fit_coverage", sa.Numeric(5, 4), nullable=False),
        sa.Column("fit_assumption_share", sa.Numeric(5, 4), nullable=False),
        *score_columns("timing"),
        sa.Column("timing_coverage", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 2), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("score_run_id", "unit_key", name="uq_opportunity_score_unit"),
        sa.CheckConstraint(
            "evidence_mode IN ('observed', 'assumption')", name="ck_opportunity_evidence_mode"
        ),
        sa.CheckConstraint(
            "fit_lower <= fit_upper AND timing_lower <= timing_upper "
            "AND priority_lower <= priority_upper",
            name="ck_opportunity_bounds",
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 100 AND fit_upper <= 100 AND timing_upper <= 100 "
            "AND fit_lower >= 0 AND timing_lower >= 0",
            name="ck_opportunity_range",
        ),
    )
    op.create_index("ix_opportunity_run_rank", "opportunity_scores", ["score_run_id", "rank"])
    op.create_index("ix_opportunity_org", "opportunity_scores", ["organization_id"])

    op.create_table(
        "data_conflicts",
        sa.Column("conflict_id", sa.String(16), primary_key=True),
        fk("organization_id", "organizations", nullable=False, ondelete="CASCADE"),
        sa.Column("entity_cnpj", sa.String(14), nullable=False),
        sa.Column("field", sa.String(64), nullable=False),
        sa.Column("rule", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("workbook_value", sa.Text(), nullable=False),
        sa.Column("source_value", sa.Text(), nullable=False),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_status", sa.String(32), nullable=False),
        sa.Column("resolved_by", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.Text(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        *timestamps(),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_conflict_severity"),
        sa.CheckConstraint(
            "resolution_status IN ('pending_review', 'accept_source', 'keep_workbook', "
            "'both_valid', 'dismissed', 'no_longer_detected')",
            name="ck_conflict_resolution",
        ),
    )
    op.create_index(
        "ix_conflict_status", "data_conflicts", ["resolution_status", "organization_id"]
    )

    op.create_table(
        "quality_reports",
        uuid_pk(),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fund_reference_date", sa.Date(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "loaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("run_at", name="uq_quality_report_run"),
    )


def downgrade() -> None:
    op.drop_table("quality_reports")
    op.drop_table("data_conflicts")
    op.drop_table("opportunity_scores")
    op.drop_table("score_runs")
    op.create_table(
        "scores",
        uuid_pk(),
        fk("organization_id", "organizations", nullable=False, ondelete="CASCADE"),
        fk("business_unit_id", "business_units", nullable=True, ondelete="CASCADE"),
        sa.Column("score_type", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("score_value", sa.Numeric(8, 4), nullable=False),
        sa.Column("explanation", postgresql.JSONB(), nullable=False),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_score_confidence"),
        sa.CheckConstraint("score_value >= 0 AND score_value <= 100", name="ck_score_range"),
        sa.UniqueConstraint(
            "organization_id",
            "business_unit_id",
            "score_type",
            "model_version",
            "as_of_date",
            name="uq_score_version",
        ),
    )
    op.create_index("ix_score_org_type", "scores", ["organization_id", "score_type"])

    op.execute("DROP INDEX IF EXISTS uq_signal_source")
    op.execute(
        "DELETE FROM commercial_signals a USING commercial_signals b WHERE a.id > b.id "
        "AND a.organization_id = b.organization_id AND a.signal_type = b.signal_type "
        "AND a.observed_at = b.observed_at AND a.source_id = b.source_id"
    )
    op.create_unique_constraint(
        "uq_signal_source",
        "commercial_signals",
        ["organization_id", "signal_type", "observed_at", "source_id"],
    )

    op.execute("DROP INDEX IF EXISTS uq_product_fit")
    op.create_unique_constraint(
        "uq_product_fit",
        "product_fit",
        ["organization_id", "business_unit_id", "product_code", "as_of_date"],
    )
    op.drop_column("product_fit", "model_version")
    op.drop_column("product_fit", "basis")

    op.drop_table("fund_metrics")
    op.drop_index("ix_fund_observation_date", table_name="fund_observations")
    op.drop_constraint("uq_fund_observation_source", "fund_observations", type_="unique")
    op.execute(
        "DELETE FROM fund_observations a USING fund_observations b "
        "WHERE a.id > b.id AND a.fund_id = b.fund_id "
        "AND a.observation_date = b.observation_date AND a.source_id = b.source_id"
    )
    op.create_unique_constraint(
        "uq_fund_observation_source",
        "fund_observations",
        ["fund_id", "observation_date", "source_id"],
    )
    op.create_index(
        "ix_fund_observation_date", "fund_observations", ["fund_id", "observation_date"]
    )
    op.drop_column("fund_observations", "subclass_id")

    op.drop_index("ix_fund_classification", table_name="funds")
    op.drop_index("ix_fund_org_active", table_name="funds")
    for column in (
        "administrator_name",
        "target_investor",
        "constitution_date",
        "allows_full_offshore",
        "is_fund_of_funds",
        "is_exclusive",
        "is_active",
        "status",
        "benchmark",
        "anbima_classification",
        "classification",
        "class_type",
        "fund_type",
        "business_unit_id",
        "manager_cnpj",
        "fund_cnpj",
    ):
        op.drop_column("funds", column)
    op.execute(
        "DELETE FROM funds a USING funds b WHERE a.id > b.id "
        "AND a.organization_id = b.organization_id AND a.canonical_name = b.canonical_name"
    )
    op.create_unique_constraint("uq_fund_org_name", "funds", ["organization_id", "canonical_name"])

    op.drop_index("ix_office_kind_precision", table_name="offices")
    for name in (
        "ck_office_location_has_precision",
        "ck_office_exact_requires_address",
        "ck_office_precision",
        "ck_office_kind",
    ):
        op.drop_constraint(name, "offices", type_="check")
    op.execute("DELETE FROM offices WHERE office_kind = 'regulatory'")
    for column in (
        "geocode_raw_sha256",
        "geocoded_at",
        "geocode_provider",
        "geocode_is_exact",
        "geocode_precision",
        "geocode_status",
        "office_kind",
        "legal_entity_id",
    ):
        op.drop_column("offices", column)

    op.drop_index("ix_legal_entity_org", table_name="legal_entities")
    op.drop_table("legal_entities")
