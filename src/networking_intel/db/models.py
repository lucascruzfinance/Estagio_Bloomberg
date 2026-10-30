from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from networking_intel.db.base import Base

CONFIDENCE_CHECK = "confidence IN ('high', 'medium', 'low', 'blocked')"
EVIDENCE_CHECK = "evidence_class IN ('source_stated', 'verified_fact', 'inference', 'gap')"
PRECISIONS = "('address', 'street', 'neighbourhood', 'city', 'unknown', 'none')"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class EvidenceMixin:
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    verification_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    transformation: Mapped[str] = mapped_column(Text, nullable=False)


class Source(Base, TimestampMixin):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "file_sha256 IS NULL OR file_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_sources_file_sha256",
        ),
    )


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    pipeline_name: Mapped[str] = mapped_column(String(64), nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    transform_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    staged_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    curated_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "pipeline_name", "input_sha256", "transform_version", name="uq_ingestion_run_input"
        ),
        CheckConstraint("status IN ('running', 'complete', 'failed')", name="ck_ingestion_status"),
        CheckConstraint("input_sha256 ~ '^[0-9a-f]{64}$'", name="ck_ingestion_sha256"),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= started_at", name="ck_ingestion_time_order"
        ),
    )


class StagingPilotAccount(Base):
    __tablename__ = "staging_pilot_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False
    )
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    account_id: Mapped[str] = mapped_column(String(96), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("run_id", "account_id", name="uq_staging_run_account"),
        CheckConstraint("record_hash ~ '^[0-9a-f]{64}$'", name="ck_staging_record_hash"),
    )


class Organization(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    account_id: Mapped[str] = mapped_column(String(96), nullable=False, unique=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_name: Mapped[str] = mapped_column(Text, nullable=False)
    institution_type: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_profile: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    business_unit_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    pilot_wave: Mapped[int] = mapped_column(Integer, nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    evidence_class: Mapped[str] = mapped_column(String(24), nullable=False)
    website_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_public: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_public: Mapped[str | None] = mapped_column(Text, nullable=True)
    careers_channel: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    data_quality_flags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("account_id ~ '^org-[a-z0-9-]+$'", name="ck_org_account_id"),
        CheckConstraint("pilot_wave >= 1", name="ck_org_pilot_wave"),
        CheckConstraint("cnpj IS NULL OR is_valid_cnpj(cnpj)", name="ck_org_cnpj"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_org_confidence"),
        CheckConstraint(EVIDENCE_CHECK, name="ck_org_evidence_class"),
        CheckConstraint(
            "analysis_unit IN ('organização', 'mesa/área')", name="ck_org_analysis_unit"
        ),
        Index("ix_org_group_name", "group_name"),
        Index("ix_org_institution_type", "institution_type"),
    )


class OrganizationAlias(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "organization_aliases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(Text, nullable=False)
    alias_kind: Mapped[str] = mapped_column(String(24), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "normalized_alias", "alias_kind", name="uq_org_alias"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_alias_confidence"),
        Index("ix_alias_normalized", "normalized_alias"),
    )


class BusinessUnit(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "business_units"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    unit_key: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    mapping_status: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        UniqueConstraint("organization_id", "unit_key", name="uq_business_unit_key"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_business_unit_confidence"),
        CheckConstraint(
            "mapping_status IN ('source_stated', 'verified', 'pending')",
            name="ck_business_unit_mapping_status",
        ),
    )


class Office(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "offices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True
    )
    office_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    address_raw: Mapped[str] = mapped_column(Text, nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, default="BR")
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    legal_entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_entities.id", ondelete="SET NULL"), nullable=True
    )
    office_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="workbook")
    geocode_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    geocode_precision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    geocode_is_exact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    geocode_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    geocode_raw_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint(CONFIDENCE_CHECK, name="ck_office_confidence"),
        CheckConstraint("state IS NULL OR state ~ '^[A-Z]{2}$'", name="ck_office_state"),
        CheckConstraint("office_kind IN ('workbook', 'regulatory')", name="ck_office_kind"),
        CheckConstraint(
            f"geocode_precision IS NULL OR geocode_precision IN {PRECISIONS}",
            name="ck_office_precision",
        ),
        CheckConstraint(
            "NOT geocode_is_exact OR (geocode_precision = 'address' AND location IS NOT NULL)",
            name="ck_office_exact_requires_address",
        ),
        CheckConstraint(
            "location IS NULL OR geocode_precision IS NOT NULL",
            name="ck_office_location_has_precision",
        ),
        Index("ix_office_location_gist", "location", postgresql_using="gist"),
        Index("ix_office_org", "organization_id"),
        Index("ix_office_kind_precision", "office_kind", "geocode_precision"),
    )


class Person(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "people"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    public_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public_professional_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "full_name", "role_title", name="uq_person_org_name_role"
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_person_confidence"),
    )


class Fund(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "funds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    asset_class: Mapped[str | None] = mapped_column(String(80), nullable=True)
    fund_cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    manager_cnpj: Mapped[str | None] = mapped_column(String(14), nullable=True)
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True
    )
    fund_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    class_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str | None] = mapped_column(Text, nullable=True)
    anbima_classification: Mapped[str | None] = mapped_column(Text, nullable=True)
    benchmark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_exclusive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_fund_of_funds: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_full_offshore: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    constitution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_investor: Mapped[str | None] = mapped_column(Text, nullable=True)
    administrator_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("cnpj IS NULL OR is_valid_cnpj(cnpj)", name="ck_fund_cnpj"),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_fund_confidence"),
        Index("ix_fund_cnpj", "cnpj", unique=True, postgresql_where=text("cnpj IS NOT NULL")),
        Index("ix_fund_org_active", "organization_id", "is_active"),
        Index("ix_fund_classification", "classification"),
    )


class FundObservation(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "fund_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fund_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("funds.id", ondelete="CASCADE"), nullable=False
    )
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    subclass_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    nav_brl: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    quota_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    subscriptions_brl: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    redemptions_brl: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    investor_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fund_id",
            "subclass_id",
            "observation_date",
            "source_id",
            name="uq_fund_observation_source",
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_fund_observation_confidence"),
        CheckConstraint("observation_date >= DATE '1900-01-01'", name="ck_fund_observation_date"),
        CheckConstraint("nav_brl IS NULL OR nav_brl >= 0", name="ck_fund_observation_nav"),
        CheckConstraint(
            "investor_count IS NULL OR investor_count >= 0", name="ck_fund_observation_investors"
        ),
        Index("ix_fund_observation_date", "fund_id", "subclass_id", "observation_date"),
    )


class CommercialSignal(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "commercial_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True
    )
    signal_type: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        Index(
            "uq_signal_source",
            "organization_id",
            "business_unit_id",
            "signal_type",
            "observed_at",
            "source_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_signal_confidence"),
        CheckConstraint("expires_at IS NULL OR expires_at >= observed_at", name="ck_signal_expiry"),
        Index("ix_signal_org_observed", "organization_id", "observed_at"),
    )


class ProductFit(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "product_fit"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="CASCADE"), nullable=True
    )
    product_code: Mapped[str] = mapped_column(String(80), nullable=False)
    fit_status: Mapped[str] = mapped_column(String(24), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    basis: Mapped[str | None] = mapped_column(String(48), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    __table_args__ = (
        Index(
            "uq_product_fit",
            "organization_id",
            "business_unit_id",
            "product_code",
            "as_of_date",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_product_fit_confidence"),
        CheckConstraint(
            "fit_status IN ('unknown', 'candidate', 'validated', 'rejected')",
            name="ck_product_fit_status",
        ),
    )


class ScoreRun(Base):
    __tablename__ = "score_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    config_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    limitations: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    sanity_checks: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("model_version", "config_sha256", "as_of_date", name="uq_score_run"),
        CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'", name="ck_score_run_sha"),
    )


class OpportunityScore(Base, TimestampMixin):
    __tablename__ = "opportunity_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    score_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("score_runs.id", ondelete="CASCADE"), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="CASCADE"), nullable=True
    )
    unit_key: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_name: Mapped[str] = mapped_column(Text, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    tier: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    priority_point: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    priority_lower: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    priority_upper: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fit_point: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    fit_lower: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fit_upper: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    fit_coverage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    fit_assumption_share: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    timing_point: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    timing_lower: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    timing_upper: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    timing_coverage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (
        UniqueConstraint("score_run_id", "unit_key", name="uq_opportunity_score_unit"),
        CheckConstraint(
            "evidence_mode IN ('observed', 'assumption')", name="ck_opportunity_evidence_mode"
        ),
        CheckConstraint(
            "fit_lower <= fit_upper AND timing_lower <= timing_upper "
            "AND priority_lower <= priority_upper",
            name="ck_opportunity_bounds",
        ),
        CheckConstraint(
            "confidence BETWEEN 0 AND 100 AND fit_upper <= 100 AND timing_upper <= 100 "
            "AND fit_lower >= 0 AND timing_lower >= 0",
            name="ck_opportunity_range",
        ),
        Index("ix_opportunity_run_rank", "score_run_id", "rank"),
        Index("ix_opportunity_org", "organization_id"),
    )


class LegalEntity(Base, TimestampMixin, EvidenceMixin):
    __tablename__ = "legal_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    business_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("business_units.id", ondelete="SET NULL"), nullable=True
    )
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False, unique=True)
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    relation_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    cvm_status: Mapped[str] = mapped_column(Text, nullable=False)
    cvm_status_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    cvm_registration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_category: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_official: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    phone_official: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email_institutional: Mapped[str | None] = mapped_column(Text, nullable=True)
    website_official: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("is_valid_cnpj(cnpj)", name="ck_legal_entity_cnpj"),
        CheckConstraint(
            "relation IN ('primary_manager', 'affiliate_manager', 'bank_entity')",
            name="ck_legal_entity_relation",
        ),
        CheckConstraint(
            "approval_status IN ('pending_human_review', 'approved', 'rejected')",
            name="ck_legal_entity_approval",
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_legal_entity_confidence"),
        Index("ix_legal_entity_org", "organization_id"),
    )


class FundMetric(Base, TimestampMixin):
    __tablename__ = "fund_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fund_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("funds.id", ondelete="CASCADE"), nullable=False
    )
    subclass_id: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    metric_version: Mapped[str] = mapped_column(String(32), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    first_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    observations: Mapped[int] = mapped_column(Integer, nullable=False)
    latest_nav_brl: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    latest_investors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    return_1m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    return_1m_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    return_3m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    return_3m_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    return_6m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    return_6m_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    return_12m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    return_12m_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    return_ytd: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    return_ytd_status: Mapped[str | None] = mapped_column(String(48), nullable=True)
    net_flow_12m_brl: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    net_flow_status: Mapped[str] = mapped_column(String(48), nullable=False)
    volatility_12m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    max_drawdown_12m: Mapped[Decimal | None] = mapped_column(Numeric(14, 8), nullable=True)
    series_flags: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "fund_id", "subclass_id", "reference_date", "metric_version", name="uq_fund_metric"
        ),
        CheckConstraint("currency = 'BRL'", name="ck_fund_metric_currency"),
        CheckConstraint(
            "return_12m IS NULL OR return_12m_status = 'ok'", name="ck_fund_metric_return_status"
        ),
        Index("ix_fund_metric_reference", "reference_date", "fund_id"),
    )


class DataConflict(Base, TimestampMixin):
    __tablename__ = "data_conflicts"

    conflict_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    entity_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    rule: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    workbook_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_value: Mapped[str] = mapped_column(Text, nullable=False)
    source_key: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_conflict_severity"),
        CheckConstraint(
            "resolution_status IN ('pending_review', 'accept_source', 'keep_workbook', "
            "'both_valid', 'dismissed', 'no_longer_detected')",
            name="ck_conflict_resolution",
        ),
        Index("ix_conflict_status", "resolution_status", "organization_id"),
    )


class QualityReport(Base):
    __tablename__ = "quality_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, unique=True)
    fund_reference_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FieldProvenance(Base):
    __tablename__ = "field_provenance"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    field_name: Mapped[str] = mapped_column(String(96), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    as_of_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    verification_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    transformation: Mapped[str] = mapped_column(Text, nullable=False)
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "entity_type", "entity_id", "field_name", "source_id", name="uq_field_provenance"
        ),
        CheckConstraint(CONFIDENCE_CHECK, name="ck_field_provenance_confidence"),
        CheckConstraint("value_hash ~ '^[0-9a-f]{64}$'", name="ck_field_provenance_hash"),
        Index("ix_field_provenance_entity", "entity_type", "entity_id"),
    )


# --- Territory universe (Prompt 8, migration 0003). Constraints live in the migration. ---


class EconomicGroup(Base, TimestampMixin):
    __tablename__ = "economic_groups"

    group_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    group_name: Mapped[str] = mapped_column(Text, nullable=False)
    basis: Mapped[str] = mapped_column(String(32), nullable=False)
    members: Mapped[int] = mapped_column(Integer, nullable=False)


class UniverseEntity(Base, TimestampMixin):
    __tablename__ = "universe_entities"

    cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    cnpj_root: Mapped[str] = mapped_column(String(8), nullable=False)
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    trade_name: Mapped[str | None] = mapped_column(Text)
    kinds: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    primary_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    coverage_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    curated_account_key: Mapped[str | None] = mapped_column(String(64))
    registration_category: Mapped[str | None] = mapped_column(Text)
    registration_date: Mapped[date | None] = mapped_column(Date)
    street: Mapped[str | None] = mapped_column(Text)
    complement: Mapped[str | None] = mapped_column(Text)
    district: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(2))
    postal_code: Mapped[str | None] = mapped_column(String(8))
    centre: Mapped[str | None] = mapped_column(String(48))
    centre_basis: Mapped[str | None] = mapped_column(String(16))
    building_key: Mapped[str | None] = mapped_column(Text)
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    geocode_precision: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    geocode_is_exact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    geocode_status: Mapped[str | None] = mapped_column(String(32))
    h3_r8: Mapped[str | None] = mapped_column(String(16))
    h3_r9: Mapped[str | None] = mapped_column(String(16))
    phone_official: Mapped[str | None] = mapped_column(String(20))
    website_official: Mapped[str | None] = mapped_column(Text)
    group_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("economic_groups.group_key", ondelete="RESTRICT"), nullable=False
    )
    ifdata_cod_inst: Mapped[str | None] = mapped_column(String(16))
    ifdata_conglomerate: Mapped[str | None] = mapped_column(String(16))
    active_classes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_classes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nav_registry_non_fic_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    nav_daily_report_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    nav_daily_report_month: Mapped[date | None] = mapped_column(Date)
    funds_administered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nav_administered_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)


class GroupMembership(Base, TimestampMixin):
    __tablename__ = "group_memberships"

    cnpj: Mapped[str] = mapped_column(
        String(14), ForeignKey("universe_entities.cnpj", ondelete="CASCADE"), primary_key=True
    )
    group_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("economic_groups.group_key", ondelete="CASCADE"), nullable=False
    )
    basis: Mapped[str] = mapped_column(String(32), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)


class CuratedAccountRecord(Base, TimestampMixin):
    __tablename__ = "curated_accounts"

    account_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    wave: Mapped[str] = mapped_column(String(16), nullable=False)
    side: Mapped[str] = mapped_column(String(16), nullable=False)
    segment: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    primary_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL")
    )


class CuratedAccountEntity(Base, TimestampMixin):
    __tablename__ = "curated_account_entities"

    account_key: Mapped[str] = mapped_column(
        String(64), ForeignKey("curated_accounts.account_key", ondelete="CASCADE"), nullable=False
    )
    cnpj: Mapped[str] = mapped_column(
        String(14), ForeignKey("universe_entities.cnpj", ondelete="CASCADE"), primary_key=True
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False)
    business_unit: Mapped[str | None] = mapped_column(Text)
    approval_status: Mapped[str] = mapped_column(String(32), nullable=False)
    relation_evidence: Mapped[str] = mapped_column(Text, nullable=False)


class UniverseFundClass(Base, TimestampMixin):
    __tablename__ = "universe_fund_classes"

    class_cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    fund_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    manager_cnpj: Mapped[str] = mapped_column(
        String(14), ForeignKey("universe_entities.cnpj", ondelete="CASCADE"), nullable=False
    )
    administrator_cnpj: Mapped[str | None] = mapped_column(String(14))
    custodian_cnpj: Mapped[str | None] = mapped_column(String(14))
    class_name: Mapped[str] = mapped_column(Text, nullable=False)
    fund_type: Mapped[str | None] = mapped_column(Text)
    class_type: Mapped[str | None] = mapped_column(Text)
    classification: Mapped[str | None] = mapped_column(Text)
    anbima_classification: Mapped[str | None] = mapped_column(Text)
    benchmark: Mapped[str | None] = mapped_column(Text)
    condominium: Mapped[str | None] = mapped_column(String(16))
    is_exclusive: Mapped[bool | None] = mapped_column(Boolean)
    is_fic: Mapped[bool | None] = mapped_column(Boolean)
    target_investor: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    registry_nav_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    registry_nav_date: Mapped[date | None] = mapped_column(Date)
    constitution_date: Mapped[date | None] = mapped_column(Date)
    class_start_date: Mapped[date | None] = mapped_column(Date)
    cancel_date: Mapped[date | None] = mapped_column(Date)
    allows_full_offshore: Mapped[bool | None] = mapped_column(Boolean)
    nav_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    curated_account_key: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundDaily(Base):
    __tablename__ = "fund_daily"

    class_cnpj: Mapped[str] = mapped_column(
        String(14),
        ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
        primary_key=True,
    )
    subclass_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    quota: Mapped[float | None] = mapped_column(Float(53))
    nav_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    inflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    outflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    investors: Mapped[int | None] = mapped_column(Integer)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundMonthly(Base):
    __tablename__ = "fund_monthly"

    class_cnpj: Mapped[str] = mapped_column(
        String(14),
        ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
        primary_key=True,
    )
    subclass_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    first_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_date: Mapped[date] = mapped_column(Date, nullable=False)
    quota_first: Mapped[float | None] = mapped_column(Float(53))
    quota_end: Mapped[float | None] = mapped_column(Float(53))
    nav_end_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    investors_end: Mapped[int | None] = mapped_column(Integer)
    inflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    outflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    days_reported: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class ManagerMonthly(Base):
    __tablename__ = "manager_monthly"

    manager_cnpj: Mapped[str] = mapped_column(
        String(14), ForeignKey("universe_entities.cnpj", ondelete="CASCADE"), primary_key=True
    )
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    nav_end_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    inflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    outflow_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    investors_end: Mapped[int | None] = mapped_column(BigInteger)
    classes_reporting: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundHoldingsSummary(Base):
    __tablename__ = "fund_holdings_summary"

    class_cnpj: Mapped[str] = mapped_column(
        String(14),
        ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
        primary_key=True,
    )
    month: Mapped[date] = mapped_column(Date, primary_key=True)
    as_of_date: Mapped[date | None] = mapped_column(Date)
    nav_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    positions: Mapped[int] = mapped_column(Integer, nullable=False)
    derivative_positions: Mapped[int] = mapped_column(Integer, nullable=False)
    top10_share: Mapped[float | None] = mapped_column(Float(53))
    pct_public_bonds_repo: Mapped[float | None] = mapped_column(Float(53))
    pct_fund_quotas: Mapped[float | None] = mapped_column(Float(53))
    pct_equities: Mapped[float | None] = mapped_column(Float(53))
    pct_private_credit: Mapped[float | None] = mapped_column(Float(53))
    pct_derivatives: Mapped[float | None] = mapped_column(Float(53))
    pct_foreign: Mapped[float | None] = mapped_column(Float(53))
    pct_cash: Mapped[float | None] = mapped_column(Float(53))
    pct_other: Mapped[float | None] = mapped_column(Float(53))
    pct_confidential: Mapped[float | None] = mapped_column(Float(53))
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundProfileMonthly(Base):
    __tablename__ = "fund_profile_monthly"

    class_cnpj: Mapped[str] = mapped_column(
        String(14),
        ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
        primary_key=True,
    )
    as_of_date: Mapped[date] = mapped_column(Date, primary_key=True)
    pct_nav_retail: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_private_banking: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_institutional: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_funds: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_non_resident: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_distributors: Mapped[float | None] = mapped_column(Float(53))
    pct_nav_other: Mapped[float | None] = mapped_column(Float(53))
    investors: Mapped[int | None] = mapped_column(Integer)
    derivatives_notional_brl: Mapped[Decimal | None] = mapped_column(Numeric(22, 2))
    var_pct: Mapped[float | None] = mapped_column(Float(53))
    var_model: Mapped[str | None] = mapped_column(Text)
    stress_pct: Mapped[float | None] = mapped_column(Float(53))
    private_credit_pct: Mapped[float | None] = mapped_column(Float(53))
    largest_investor_pct: Mapped[float | None] = mapped_column(Float(53))
    days_to_liquidate_half: Mapped[float | None] = mapped_column(Float(53))
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundLamina(Base):
    __tablename__ = "fund_laminas"

    class_cnpj: Mapped[str] = mapped_column(
        String(14),
        ForeignKey("universe_fund_classes.class_cnpj", ondelete="CASCADE"),
        primary_key=True,
    )
    subclass_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    as_of_date: Mapped[date | None] = mapped_column(Date)
    trade_name: Mapped[str | None] = mapped_column(Text)
    max_foreign_pct: Mapped[str | None] = mapped_column(Text)
    max_private_credit_pct: Mapped[str | None] = mapped_column(Text)
    max_leverage_pct: Mapped[str | None] = mapped_column(Text)
    admin_fee_pct: Mapped[str | None] = mapped_column(Text)
    performance_fee: Mapped[str | None] = mapped_column(Text)
    min_initial_investment_brl: Mapped[str | None] = mapped_column(Text)
    risk_class: Mapped[str | None] = mapped_column(Text)
    benchmark: Mapped[str | None] = mapped_column(Text)
    redemption_payment_days: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class FundRegistryEvent(Base):
    __tablename__ = "fund_registry_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fund_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    manager_cnpj: Mapped[str] = mapped_column(
        String(14), ForeignKey("universe_entities.cnpj", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    counterparty_cnpj: Mapped[str | None] = mapped_column(String(14))
    counterparty_name: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class BankInstitution(Base):
    __tablename__ = "bank_institutions"

    cod_inst: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    is_conglomerate: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tcb: Mapped[str | None] = mapped_column(Text)
    td: Mapped[str | None] = mapped_column(Text)
    tc: Mapped[str | None] = mapped_column(Text)
    segment: Mapped[str | None] = mapped_column(Text)
    sr: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(2))
    city: Mapped[str | None] = mapped_column(String(120))
    financial_conglomerate: Mapped[str | None] = mapped_column(String(16))
    prudential_conglomerate: Mapped[str | None] = mapped_column(String(16))
    leader_cnpj_root: Mapped[str | None] = mapped_column(String(8))
    activity_start: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str] = mapped_column(String(6), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class BankFinancial(Base):
    __tablename__ = "bank_financials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cod_inst: Mapped[str] = mapped_column(
        String(16), ForeignKey("bank_institutions.cod_inst", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(6), nullable=False)
    report: Mapped[str] = mapped_column(String(4), nullable=False)
    report_name: Mapped[str] = mapped_column(Text, nullable=False)
    group_name: Mapped[str] = mapped_column(Text, nullable=False)
    account_code: Mapped[str] = mapped_column(String(16), nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(26, 2))
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class Benchmark(Base):
    __tablename__ = "benchmarks"

    series_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    value: Mapped[float] = mapped_column(Float(53), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    sgs_code: Mapped[int] = mapped_column(Integer, nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
    )


class Building(Base):
    __tablename__ = "buildings"

    building_key: Mapped[str] = mapped_column(Text, primary_key=True)
    tenants: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[Any | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    precision: Mapped[str] = mapped_column(String(16), nullable=False)
    is_exact: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    h3_r8: Mapped[str | None] = mapped_column(String(16))
    h3_r9: Mapped[str | None] = mapped_column(String(16))
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    attribution: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="RESTRICT"), nullable=True
    )


class CrmStatus(Base):
    """Commercial status imported from the CRM; empty until real data exists."""

    __tablename__ = "crm_status"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_key: Mapped[str | None] = mapped_column(String(64))
    cnpj: Mapped[str | None] = mapped_column(String(14))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    relationship: Mapped[str | None] = mapped_column(String(16))
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_note: Mapped[str] = mapped_column(Text, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
