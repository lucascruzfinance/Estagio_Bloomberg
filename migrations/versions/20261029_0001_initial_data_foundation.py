"""Create the PostgreSQL/PostGIS data foundation.

Revision ID: 20261029_0001
Revises: None
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "20261029_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONFIDENCE_CHECK = "confidence IN ('high', 'medium', 'low', 'blocked')"


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


def evidence_columns() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("verification_status", sa.Text(), nullable=True),
        sa.Column("transformation", sa.Text(), nullable=False),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION is_valid_cnpj(value text)
        RETURNS boolean
        LANGUAGE plpgsql
        IMMUTABLE
        STRICT
        AS $$
        DECLARE
            cleaned text := regexp_replace(value, '[^0-9]', '', 'g');
            weights_one int[] := ARRAY[5,4,3,2,9,8,7,6,5,4,3,2];
            weights_two int[] := ARRAY[6,5,4,3,2,9,8,7,6,5,4,3,2];
            total int := 0;
            digit_one int;
            digit_two int;
            i int;
        BEGIN
            IF cleaned !~ '^[0-9]{14}$' OR cleaned ~ '^([0-9])\1{13}$' THEN
                RETURN false;
            END IF;
            FOR i IN 1..12 LOOP
                total := total + substring(cleaned FROM i FOR 1)::int * weights_one[i];
            END LOOP;
            digit_one := CASE WHEN total % 11 < 2 THEN 0 ELSE 11 - total % 11 END;
            total := 0;
            FOR i IN 1..13 LOOP
                total := total + substring(cleaned FROM i FOR 1)::int * weights_two[i];
            END LOOP;
            digit_two := CASE WHEN total % 11 < 2 THEN 0 ELSE 11 - total % 11 END;
            RETURN digit_one = substring(cleaned FROM 13 FOR 1)::int
               AND digit_two = substring(cleaned FROM 14 FOR 1)::int;
        END;
        $$
        """
    )

    op.create_table(
        "sources",
        uuid_pk(),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        *timestamps(),
        sa.CheckConstraint(
            "file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_sources_file_sha256",
        ),
        sa.UniqueConstraint("source_key", name="uq_sources_source_key"),
    )

    op.create_table(
        "ingestion_runs",
        uuid_pk(),
        sa.Column("pipeline_name", sa.String(64), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("transform_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("staged_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("curated_row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'complete', 'failed')", name="ck_ingestion_status"
        ),
        sa.CheckConstraint("input_sha256 ~ '^[0-9a-f]{64}$'", name="ck_ingestion_sha256"),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="ck_ingestion_time_order"
        ),
        sa.UniqueConstraint(
            "pipeline_name", "input_sha256", "transform_version", name="uq_ingestion_run_input"
        ),
    )

    op.create_table(
        "staging_pilot_accounts",
        uuid_pk(),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_key", sa.String(64), nullable=False),
        sa.Column("account_id", sa.String(96), nullable=False),
        sa.Column("record_hash", sa.String(64), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("record_hash ~ '^[0-9a-f]{64}$'", name="ck_staging_record_hash"),
        sa.UniqueConstraint("run_id", "account_id", name="uq_staging_run_account"),
    )

    op.create_table(
        "organizations",
        uuid_pk(),
        sa.Column("account_id", sa.String(96), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=True),
        sa.Column("group_name", sa.Text(), nullable=False),
        sa.Column("institution_type", sa.String(64), nullable=False),
        sa.Column("strategy_profile", sa.Text(), nullable=False),
        sa.Column("analysis_unit", sa.String(32), nullable=False),
        sa.Column("business_unit_required", sa.Boolean(), nullable=False),
        sa.Column("pilot_wave", sa.Integer(), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("evidence_class", sa.String(24), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("email_public", sa.Text(), nullable=True),
        sa.Column("phone_public", sa.Text(), nullable=True),
        sa.Column("careers_channel", sa.Text(), nullable=True),
        sa.Column("human_approval_required", sa.Boolean(), nullable=False),
        sa.Column("data_quality_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint("account_id ~ '^org-[a-z0-9-]+$'", name="ck_org_account_id"),
        sa.CheckConstraint("pilot_wave >= 1", name="ck_org_pilot_wave"),
        sa.CheckConstraint("cnpj IS NULL OR is_valid_cnpj(cnpj)", name="ck_org_cnpj"),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_org_confidence"),
        sa.CheckConstraint(
            "evidence_class IN ('source_stated', 'verified_fact', 'inference', 'gap')",
            name="ck_org_evidence_class",
        ),
        sa.CheckConstraint(
            "analysis_unit IN ('organização', 'mesa/área')", name="ck_org_analysis_unit"
        ),
        sa.UniqueConstraint("account_id", name="uq_org_account_id"),
        sa.UniqueConstraint("canonical_name", name="uq_org_canonical_name"),
    )
    op.create_index("ix_org_group_name", "organizations", ["group_name"])
    op.create_index("ix_org_institution_type", "organizations", ["institution_type"])

    op.create_table(
        "organization_aliases",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("normalized_alias", sa.Text(), nullable=False),
        sa.Column("alias_kind", sa.String(24), nullable=False),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_alias_confidence"),
        sa.UniqueConstraint(
            "organization_id", "normalized_alias", "alias_kind", name="uq_org_alias"
        ),
    )
    op.create_index("ix_alias_normalized", "organization_aliases", ["normalized_alias"])

    op.create_table(
        "business_units",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unit_key", sa.String(160), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("mapping_status", sa.String(32), nullable=False),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_business_unit_confidence"),
        sa.CheckConstraint(
            "mapping_status IN ('source_stated', 'verified', 'pending')",
            name="ck_business_unit_mapping_status",
        ),
        sa.UniqueConstraint("organization_id", "unit_key", name="uq_business_unit_key"),
    )

    op.create_table(
        "offices",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("office_key", sa.String(64), nullable=False),
        sa.Column("address_raw", sa.Text(), nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=False, server_default="BR"),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=True,
        ),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_office_confidence"),
        sa.CheckConstraint("state IS NULL OR state ~ '^[A-Z]{2}$'", name="ck_office_state"),
        sa.UniqueConstraint("office_key", name="uq_office_key"),
    )
    op.create_index("ix_office_location_gist", "offices", ["location"], postgresql_using="gist")
    op.create_index("ix_office_org", "offices", ["organization_id"])

    op.create_table(
        "people",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role_title", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("public_email", sa.Text(), nullable=True),
        sa.Column(
            "is_public_professional_data", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_person_confidence"),
        sa.UniqueConstraint(
            "organization_id", "full_name", "role_title", name="uq_person_org_name_role"
        ),
    )

    op.create_table(
        "funds",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=True),
        sa.Column("cnpj", sa.String(14), nullable=True),
        sa.Column("asset_class", sa.String(80), nullable=True),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint("cnpj IS NULL OR is_valid_cnpj(cnpj)", name="ck_fund_cnpj"),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_fund_confidence"),
        sa.UniqueConstraint("organization_id", "canonical_name", name="uq_fund_org_name"),
    )
    op.create_index(
        "ix_fund_cnpj", "funds", ["cnpj"], unique=True, postgresql_where=sa.text("cnpj IS NOT NULL")
    )

    op.create_table(
        "fund_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column(
            "fund_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("funds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("nav_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column("quota_value", sa.Numeric(24, 10), nullable=True),
        sa.Column("subscriptions_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column("redemptions_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column("investor_count", sa.Integer(), nullable=True),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_fund_observation_confidence"),
        sa.CheckConstraint(
            "observation_date >= DATE '1900-01-01'", name="ck_fund_observation_date"
        ),
        sa.CheckConstraint("nav_brl IS NULL OR nav_brl >= 0", name="ck_fund_observation_nav"),
        sa.CheckConstraint(
            "investor_count IS NULL OR investor_count >= 0", name="ck_fund_observation_investors"
        ),
        sa.UniqueConstraint(
            "fund_id", "observation_date", "source_id", name="uq_fund_observation_source"
        ),
    )
    op.create_index(
        "ix_fund_observation_date", "fund_observations", ["fund_id", "observation_date"]
    )

    op.create_table(
        "commercial_signals",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("signal_type", sa.String(80), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_signal_confidence"),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at >= observed_at", name="ck_signal_expiry"
        ),
        sa.UniqueConstraint(
            "organization_id", "signal_type", "observed_at", "source_id", name="uq_signal_source"
        ),
    )
    op.create_index(
        "ix_signal_org_observed", "commercial_signals", ["organization_id", "observed_at"]
    )

    op.create_table(
        "product_fit",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_units.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("product_code", sa.String(80), nullable=False),
        sa.Column("fit_status", sa.String(24), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        *evidence_columns(),
        *timestamps(),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_product_fit_confidence"),
        sa.CheckConstraint(
            "fit_status IN ('unknown', 'candidate', 'validated', 'rejected')",
            name="ck_product_fit_status",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "business_unit_id",
            "product_code",
            "as_of_date",
            name="uq_product_fit",
        ),
    )

    op.create_table(
        "scores",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "business_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_units.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("score_type", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(32), nullable=False),
        sa.Column("score_value", sa.Numeric(8, 4), nullable=False),
        sa.Column("explanation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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

    op.create_table(
        "field_provenance",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(96), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=True),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("verification_status", sa.Text(), nullable=True),
        sa.Column("transformation", sa.Text(), nullable=False),
        sa.Column("value_hash", sa.String(64), nullable=False),
        sa.CheckConstraint(CONFIDENCE_CHECK, name="ck_field_provenance_confidence"),
        sa.CheckConstraint("value_hash ~ '^[0-9a-f]{64}$'", name="ck_field_provenance_hash"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "field_name", "source_id", name="uq_field_provenance"
        ),
    )
    op.create_index("ix_field_provenance_entity", "field_provenance", ["entity_type", "entity_id"])


def downgrade() -> None:
    for table_name in (
        "field_provenance",
        "scores",
        "product_fit",
        "commercial_signals",
        "fund_observations",
        "funds",
        "people",
        "offices",
        "business_units",
        "organization_aliases",
        "organizations",
        "staging_pilot_accounts",
        "ingestion_runs",
        "sources",
    ):
        op.drop_table(table_name)
    op.execute("DROP FUNCTION IF EXISTS is_valid_cnpj(text)")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
