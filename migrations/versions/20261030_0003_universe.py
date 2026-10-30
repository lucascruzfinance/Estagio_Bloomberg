"""Territory universe, sell side and fund series (Prompt 8).

Revision ID: 20261030_0003
Revises: 20261030_0002
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "20261030_0003"
down_revision: str | None = "20261030_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRECISIONS = "('address', 'street', 'neighbourhood', 'city', 'unknown', 'none')"
KINDS = (
    "('banco_multiplo', 'banco_investimento', 'caixa_economica', 'infraestrutura_mercado', "
    "'corretora', 'gestora', 'distribuidora', 'administrador_fiduciario', 'custodiante', "
    "'escriturador', 'outro')"
)
MONEY = sa.Numeric(22, 2)


def source_fk(nullable: bool = False) -> sa.Column[object]:
    return sa.Column(
        "source_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("sources.id", ondelete="RESTRICT"),
        nullable=nullable,
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


def upgrade() -> None:
    op.create_table(
        "economic_groups",
        sa.Column("group_key", sa.String(64), primary_key=True),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("basis", sa.String(32), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "basis IN ('curated_registry', 'ifdata_conglomerate', 'cnpj_root')",
            name="ck_economic_group_basis",
        ),
        sa.CheckConstraint("members > 0", name="ck_economic_group_members"),
    )

    op.create_table(
        "universe_entities",
        sa.Column("cnpj", sa.String(14), primary_key=True),
        sa.Column("cnpj_root", sa.String(8), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("trade_name", sa.Text(), nullable=True),
        sa.Column("kinds", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("primary_kind", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("coverage_tier", sa.String(16), nullable=False),
        sa.Column("curated_account_key", sa.String(64), nullable=True),
        sa.Column("registration_category", sa.Text(), nullable=True),
        sa.Column("registration_date", sa.Date(), nullable=True),
        sa.Column("street", sa.Text(), nullable=True),
        sa.Column("complement", sa.Text(), nullable=True),
        sa.Column("district", sa.Text(), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("postal_code", sa.String(8), nullable=True),
        sa.Column("centre", sa.String(48), nullable=True),
        sa.Column("centre_basis", sa.String(16), nullable=True),
        sa.Column("building_key", sa.Text(), nullable=True),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("geocode_precision", sa.String(16), nullable=False, server_default="none"),
        sa.Column("geocode_is_exact", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("geocode_status", sa.String(32), nullable=True),
        sa.Column("h3_r8", sa.String(16), nullable=True),
        sa.Column("h3_r9", sa.String(16), nullable=True),
        sa.Column("phone_official", sa.String(20), nullable=True),
        sa.Column("website_official", sa.Text(), nullable=True),
        sa.Column(
            "group_key",
            sa.String(64),
            sa.ForeignKey("economic_groups.group_key", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ifdata_cod_inst", sa.String(16), nullable=True),
        sa.Column("ifdata_conglomerate", sa.String(16), nullable=True),
        sa.Column("active_classes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_classes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nav_registry_non_fic_brl", MONEY, nullable=True),
        sa.Column("nav_daily_report_brl", MONEY, nullable=True),
        sa.Column("nav_daily_report_month", sa.Date(), nullable=True),
        sa.Column("funds_administered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("nav_administered_brl", MONEY, nullable=True),
        source_fk(),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        *timestamps(),
        sa.CheckConstraint("is_valid_cnpj(cnpj)", name="ck_universe_entity_cnpj"),
        sa.CheckConstraint("cnpj_root = left(cnpj, 8)", name="ck_universe_entity_root"),
        sa.CheckConstraint(f"primary_kind IN {KINDS}", name="ck_universe_entity_kind"),
        sa.CheckConstraint("side IN ('buy_side', 'sell_side')", name="ck_universe_entity_side"),
        sa.CheckConstraint(
            "coverage_tier IN ('curated', 'radar', 'universe')", name="ck_universe_entity_tier"
        ),
        sa.CheckConstraint(
            "(coverage_tier = 'curated') = (curated_account_key IS NOT NULL)",
            name="ck_universe_entity_curated_key",
        ),
        sa.CheckConstraint(
            f"geocode_precision IN {PRECISIONS}", name="ck_universe_entity_precision"
        ),
        sa.CheckConstraint(
            "NOT geocode_is_exact OR (geocode_precision = 'address' AND location IS NOT NULL)",
            name="ck_universe_entity_exact_requires_address",
        ),
        sa.CheckConstraint(
            "location IS NULL OR geocode_precision <> 'none'",
            name="ck_universe_entity_location_has_precision",
        ),
    )
    for column in ("coverage_tier", "primary_kind", "centre", "group_key", "h3_r8", "building_key"):
        op.create_index(f"ix_universe_entity_{column}", "universe_entities", [column])
    op.create_index("ix_universe_entity_registered", "universe_entities", ["registration_date"])
    op.create_index(
        "ix_universe_entity_location",
        "universe_entities",
        ["location"],
        postgresql_using="gist",
    )

    op.create_table(
        "group_memberships",
        sa.Column(
            "cnpj",
            sa.String(14),
            sa.ForeignKey("universe_entities.cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "group_key",
            sa.String(64),
            sa.ForeignKey("economic_groups.group_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("basis", sa.String(32), nullable=False),
        sa.Column("approval_status", sa.String(32), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "approval_status IN ('pending_human_review', 'approved', 'rejected', 'source_exact')",
            name="ck_group_membership_approval",
        ),
        sa.CheckConstraint(
            "(basis = 'curated_registry') = (approval_status <> 'source_exact')",
            name="ck_group_membership_review_only_for_curated",
        ),
    )
    op.create_index("ix_group_membership_group", "group_memberships", ["group_key"])

    op.create_table(
        "curated_accounts",
        sa.Column("account_key", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("wave", sa.String(16), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("segment", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("primary_cnpj", sa.String(14), nullable=False),
        sa.Column("approval_status", sa.String(32), nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *timestamps(),
        sa.CheckConstraint("wave IN ('pilot', 'wave2')", name="ck_curated_account_wave"),
        sa.CheckConstraint("side IN ('buy_side', 'sell_side')", name="ck_curated_account_side"),
        sa.CheckConstraint(
            "approval_status IN ('pending_human_review', 'approved', 'rejected')",
            name="ck_curated_account_approval",
        ),
    )
    op.create_table(
        "curated_account_entities",
        sa.Column(
            "account_key",
            sa.String(64),
            sa.ForeignKey("curated_accounts.account_key", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "cnpj",
            sa.String(14),
            sa.ForeignKey("universe_entities.cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("relation", sa.String(32), nullable=False),
        sa.Column("business_unit", sa.Text(), nullable=True),
        sa.Column("approval_status", sa.String(32), nullable=False),
        sa.Column("relation_evidence", sa.Text(), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "relation IN ('primary_manager', 'affiliate_manager', 'bank_entity')",
            name="ck_curated_entity_relation",
        ),
        sa.CheckConstraint(
            "approval_status IN ('pending_human_review', 'approved', 'rejected')",
            name="ck_curated_entity_approval",
        ),
    )
    op.create_index("ix_curated_entity_account", "curated_account_entities", ["account_key"])

    op.create_table(
        "universe_fund_classes",
        sa.Column("class_cnpj", sa.String(14), primary_key=True),
        sa.Column("fund_cnpj", sa.String(14), nullable=False),
        sa.Column(
            "manager_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_entities.cnpj", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("administrator_cnpj", sa.String(14), nullable=True),
        sa.Column("custodian_cnpj", sa.String(14), nullable=True),
        sa.Column("class_name", sa.Text(), nullable=False),
        sa.Column("fund_type", sa.Text(), nullable=True),
        sa.Column("class_type", sa.Text(), nullable=True),
        sa.Column("classification", sa.Text(), nullable=True),
        sa.Column("anbima_classification", sa.Text(), nullable=True),
        sa.Column("benchmark", sa.Text(), nullable=True),
        sa.Column("condominium", sa.String(16), nullable=True),
        sa.Column("is_exclusive", sa.Boolean(), nullable=True),
        sa.Column("is_fic", sa.Boolean(), nullable=True),
        sa.Column("target_investor", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False),
        sa.Column("registry_nav_brl", MONEY, nullable=True),
        sa.Column("registry_nav_date", sa.Date(), nullable=True),
        sa.Column("constitution_date", sa.Date(), nullable=True),
        sa.Column("class_start_date", sa.Date(), nullable=True),
        sa.Column("cancel_date", sa.Date(), nullable=True),
        sa.Column("allows_full_offshore", sa.Boolean(), nullable=True),
        sa.Column("nav_anomaly", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("curated_account_key", sa.String(64), nullable=True),
        source_fk(),
        *timestamps(),
        sa.CheckConstraint(
            "NOT is_selected OR (is_active AND condominium = 'Aberto' AND is_exclusive = false "
            "AND is_fic = false)",
            name="ck_universe_class_selection_rule",
        ),
        sa.CheckConstraint(
            "registry_nav_brl IS NULL OR registry_nav_brl <= 300000000000",
            name="ck_universe_class_nav_plausible",
        ),
    )
    op.create_index("ix_universe_class_manager", "universe_fund_classes", ["manager_cnpj"])
    op.create_index("ix_universe_class_selected", "universe_fund_classes", ["is_selected"])

    op.create_table(
        "fund_daily",
        sa.Column(
            "class_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subclass_id", sa.String(32), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("quota", sa.Float(53), nullable=True),
        sa.Column("nav_brl", MONEY, nullable=True),
        sa.Column("inflow_brl", MONEY, nullable=True),
        sa.Column("outflow_brl", MONEY, nullable=True),
        sa.Column("investors", sa.Integer(), nullable=True),
        source_fk(),
    )
    op.create_index("ix_fund_daily_date_brin", "fund_daily", ["date"], postgresql_using="brin")

    op.create_table(
        "fund_monthly",
        sa.Column(
            "class_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subclass_id", sa.String(32), primary_key=True),
        sa.Column("month", sa.Date(), primary_key=True),
        sa.Column("first_date", sa.Date(), nullable=False),
        sa.Column("last_date", sa.Date(), nullable=False),
        sa.Column("quota_first", sa.Float(53), nullable=True),
        sa.Column("quota_end", sa.Float(53), nullable=True),
        sa.Column("nav_end_brl", MONEY, nullable=True),
        sa.Column("investors_end", sa.Integer(), nullable=True),
        sa.Column("inflow_brl", MONEY, nullable=True),
        sa.Column("outflow_brl", MONEY, nullable=True),
        sa.Column("days_reported", sa.Integer(), nullable=False),
        source_fk(),
        sa.CheckConstraint("month = date_trunc('month', month)::date", name="ck_fund_month_start"),
        sa.CheckConstraint("first_date <= last_date", name="ck_fund_month_dates"),
    )
    op.create_index("ix_fund_monthly_month", "fund_monthly", ["month"])

    op.create_table(
        "manager_monthly",
        sa.Column(
            "manager_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_entities.cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("month", sa.Date(), primary_key=True),
        sa.Column("nav_end_brl", MONEY, nullable=True),
        sa.Column("inflow_brl", MONEY, nullable=True),
        sa.Column("outflow_brl", MONEY, nullable=True),
        sa.Column("investors_end", sa.BigInteger(), nullable=True),
        sa.Column("classes_reporting", sa.Integer(), nullable=False),
        source_fk(),
    )

    op.create_table(
        "fund_holdings_summary",
        sa.Column(
            "class_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("month", sa.Date(), primary_key=True),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("nav_brl", MONEY, nullable=True),
        sa.Column("positions", sa.Integer(), nullable=False),
        sa.Column("derivative_positions", sa.Integer(), nullable=False),
        sa.Column("top10_share", sa.Float(53), nullable=True),
        *[
            sa.Column(f"pct_{category}", sa.Float(53), nullable=True)
            for category in (
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
        ],
        source_fk(),
    )

    op.create_table(
        "fund_profile_monthly",
        sa.Column(
            "class_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("as_of_date", sa.Date(), primary_key=True),
        *[
            sa.Column(f"pct_nav_{group}", sa.Float(53), nullable=True)
            for group in (
                "retail",
                "private_banking",
                "institutional",
                "funds",
                "non_resident",
                "distributors",
                "other",
            )
        ],
        sa.Column("investors", sa.Integer(), nullable=True),
        sa.Column("derivatives_notional_brl", MONEY, nullable=True),
        sa.Column("var_pct", sa.Float(53), nullable=True),
        sa.Column("var_model", sa.Text(), nullable=True),
        sa.Column("stress_pct", sa.Float(53), nullable=True),
        sa.Column("private_credit_pct", sa.Float(53), nullable=True),
        sa.Column("largest_investor_pct", sa.Float(53), nullable=True),
        sa.Column("days_to_liquidate_half", sa.Float(53), nullable=True),
        source_fk(),
    )

    op.create_table(
        "fund_laminas",
        sa.Column(
            "class_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("subclass_id", sa.String(32), primary_key=True),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        *[
            sa.Column(name, sa.Text(), nullable=True)
            for name in (
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
        ],
        source_fk(),
    )

    op.create_table(
        "fund_registry_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("fund_cnpj", sa.String(14), nullable=False),
        sa.Column(
            "manager_cnpj",
            sa.String(14),
            sa.ForeignKey("universe_entities.cnpj", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("counterparty_cnpj", sa.String(14), nullable=True),
        sa.Column("counterparty_name", sa.Text(), nullable=True),
        source_fk(),
        sa.UniqueConstraint(
            "fund_cnpj", "manager_cnpj", "event_type", "event_date", name="uq_fund_registry_event"
        ),
        sa.CheckConstraint(
            "event_type IN ('mandate_start', 'mandate_end', 'transfer_in', 'transfer_out')",
            name="ck_fund_registry_event_type",
        ),
    )
    op.create_index(
        "ix_fund_registry_event_manager", "fund_registry_events", ["manager_cnpj", "event_date"]
    )

    op.create_table(
        "bank_institutions",
        sa.Column("cod_inst", sa.String(16), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_conglomerate", sa.Boolean(), nullable=False),
        sa.Column("tcb", sa.Text(), nullable=True),
        sa.Column("td", sa.Text(), nullable=True),
        sa.Column("tc", sa.Text(), nullable=True),
        sa.Column("segment", sa.Text(), nullable=True),
        sa.Column("sr", sa.Text(), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("financial_conglomerate", sa.String(16), nullable=True),
        sa.Column("prudential_conglomerate", sa.String(16), nullable=True),
        sa.Column("leader_cnpj_root", sa.String(8), nullable=True),
        sa.Column("activity_start", sa.Text(), nullable=True),
        sa.Column("period", sa.String(6), nullable=False),
        source_fk(),
    )
    op.create_index(
        "ix_bank_institution_conglomerate", "bank_institutions", ["prudential_conglomerate"]
    )

    op.create_table(
        "bank_financials",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "cod_inst",
            sa.String(16),
            sa.ForeignKey("bank_institutions.cod_inst", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period", sa.String(6), nullable=False),
        sa.Column("report", sa.String(4), nullable=False),
        sa.Column("report_name", sa.Text(), nullable=False),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("account_code", sa.String(16), nullable=False),
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(26, 2), nullable=True),
        source_fk(),
        sa.UniqueConstraint(
            "cod_inst", "period", "report", "account_code", name="uq_bank_financial"
        ),
    )
    op.create_index("ix_bank_financial_metric", "bank_financials", ["metric", "period"])

    op.create_table(
        "benchmarks",
        sa.Column("series_key", sa.String(16), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("value", sa.Float(53), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("sgs_code", sa.Integer(), nullable=False),
        source_fk(),
    )

    op.create_table(
        "buildings",
        sa.Column("building_key", sa.Text(), primary_key=True),
        sa.Column("tenants", sa.Integer(), nullable=False),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=False), nullable=True),
        sa.Column("precision", sa.String(16), nullable=False),
        sa.Column("is_exact", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("h3_r8", sa.String(16), nullable=True),
        sa.Column("h3_r9", sa.String(16), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("attribution", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        source_fk(nullable=True),
        sa.CheckConstraint(f"precision IN {PRECISIONS}", name="ck_building_precision"),
        sa.CheckConstraint(
            "NOT is_exact OR (precision = 'address' AND location IS NOT NULL)",
            name="ck_building_exact_requires_address",
        ),
    )

    op.create_table(
        "crm_status",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("account_key", sa.String(64), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("relationship", sa.String(16), nullable=True),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=False),
        sa.Column(
            "imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "account_key IS NOT NULL OR cnpj IS NOT NULL", name="ck_crm_status_target"
        ),
        sa.CheckConstraint(
            "status IN ('client', 'former_client', 'open_opportunity', 'never_contacted', 'unknown')",
            name="ck_crm_status_value",
        ),
        sa.CheckConstraint(
            "relationship IS NULL OR relationship IN ('new_logo', 'expansion')",
            name="ck_crm_status_relationship",
        ),
    )


def downgrade() -> None:
    for table in (
        "crm_status",
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
    ):
        op.drop_table(table)
