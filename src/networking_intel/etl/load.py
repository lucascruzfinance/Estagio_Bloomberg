from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import Engine, FromClause, Table, func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, sessionmaker

from networking_intel.db.models import (
    BusinessUnit,
    FieldProvenance,
    IngestionRun,
    Office,
    Organization,
    OrganizationAlias,
    Source,
    StagingPilotAccount,
)
from networking_intel.db.session import create_database_engine, create_session_factory
from networking_intel.etl.schemas import PilotAccount, load_pilot_csv
from networking_intel.etl.transform import (
    TRANSFORM_VERSION,
    TRANSFORMATION,
    TransformedAccount,
    stable_hash,
    transform_accounts,
)

PIPELINE_NAME = "pilot_accounts_csv"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
    )
    return stable_hash(payload)


def pipe_list(value: str | None) -> list[str]:
    return [item.strip() for item in value.split(" | ") if item.strip()] if value else []


def upsert_returning_id(
    session: Session,
    table: FromClause,
    values: dict[str, Any],
    conflict_columns: list[str],
    update_columns: Iterable[str],
) -> uuid.UUID:
    typed_table = cast(Table, table)
    excluded = insert(typed_table).excluded
    update_values = {column: getattr(excluded, column) for column in update_columns}
    if "updated_at" in typed_table.c:
        update_values["updated_at"] = func.now()
    statement = (
        insert(typed_table)
        .values(**values)
        .on_conflict_do_update(
            index_elements=conflict_columns,
            set_=update_values,
        )
        .returning(typed_table.c.id)
    )
    return cast(uuid.UUID, session.execute(statement).scalar_one())


def source_values(account: PilotAccount, collected_at: datetime) -> dict[str, Any]:
    source_key = stable_hash(
        f"{account.source_workbook_sha256}|{account.source_locator}|{account.verification_locator or ''}"
    )
    return {
        "source_key": source_key,
        "source_type": "workbook",
        "source_locator": account.source_locator,
        "source_url": account.verification_source_url,
        "file_sha256": account.source_workbook_sha256,
        "collected_at": collected_at,
    }


def evidence_values(
    account: PilotAccount, source_id: uuid.UUID, collected_at: datetime
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "collected_at": collected_at,
        "as_of_date": account.as_of_date,
        "confidence": account.confidence,
        "verification_status": account.verification_status,
        "transformation": TRANSFORMATION,
    }


def organization_values(
    account: PilotAccount, source_id: uuid.UUID, collected_at: datetime
) -> dict[str, Any]:
    return {
        "account_id": account.account_id,
        "canonical_name": account.canonical_name,
        "legal_name": account.legal_name,
        "group_name": account.group_name,
        "institution_type": account.institution_type,
        "strategy_profile": account.strategy_profile,
        "analysis_unit": account.analysis_unit,
        "business_unit_required": account.business_unit_required,
        "pilot_wave": account.pilot_wave,
        "cnpj": account.cnpj,
        "evidence_class": account.evidence_class,
        "website_url": account.website_url,
        "linkedin_url": account.linkedin_url,
        "email_public": account.email_public,
        "phone_public": account.phone_public,
        "careers_channel": account.careers_channel,
        "human_approval_required": account.human_approval_required,
        "data_quality_flags": pipe_list(account.data_quality_flags),
        **evidence_values(account, source_id, collected_at),
    }


PROVENANCE_FIELDS = (
    "canonical_name",
    "legal_name",
    "group_name",
    "institution_type",
    "strategy_profile",
    "analysis_unit",
    "business_unit_required",
    "cnpj",
    "website_url",
    "linkedin_url",
    "email_public",
    "phone_public",
    "careers_channel",
)


def upsert_field_provenance(
    session: Session,
    account: PilotAccount,
    organization_id: uuid.UUID,
    source_id: uuid.UUID,
    collected_at: datetime,
) -> None:
    for field_name in PROVENANCE_FIELDS:
        value = getattr(account, field_name)
        values = {
            "entity_type": "organization",
            "entity_id": organization_id,
            "field_name": field_name,
            "source_id": source_id,
            "source_locator": account.source_locator,
            "collected_at": collected_at,
            "as_of_date": account.as_of_date,
            "confidence": account.confidence,
            "verification_status": account.verification_status,
            "transformation": TRANSFORMATION,
            "value_hash": json_hash(value),
        }
        provenance_table = cast(Table, FieldProvenance.__table__)
        statement = insert(provenance_table).values(**values)
        statement = statement.on_conflict_do_update(
            constraint="uq_field_provenance",
            set_={
                "source_locator": statement.excluded.source_locator,
                "collected_at": statement.excluded.collected_at,
                "as_of_date": statement.excluded.as_of_date,
                "confidence": statement.excluded.confidence,
                "verification_status": statement.excluded.verification_status,
                "transformation": statement.excluded.transformation,
                "value_hash": statement.excluded.value_hash,
            },
        )
        session.execute(statement)


def load_curated_account(
    session: Session,
    transformed: TransformedAccount,
    run_id: uuid.UUID,
    collected_at: datetime,
) -> None:
    account = transformed.pilot
    source_data = source_values(account, collected_at)
    source_id = upsert_returning_id(
        session,
        Source.__table__,
        source_data,
        ["source_key"],
        ("source_type", "source_locator", "source_url", "file_sha256", "collected_at"),
    )

    raw_payload = account.model_dump(mode="json")
    staging_values = {
        "run_id": run_id,
        "source_key": source_data["source_key"],
        "account_id": account.account_id,
        "record_hash": json_hash(raw_payload),
        "raw_payload": raw_payload,
        "loaded_at": collected_at,
    }
    upsert_returning_id(
        session,
        StagingPilotAccount.__table__,
        staging_values,
        ["run_id", "account_id"],
        ("source_key", "record_hash", "raw_payload", "loaded_at"),
    )

    org_data = organization_values(account, source_id, collected_at)
    organization_id = upsert_returning_id(
        session,
        Organization.__table__,
        org_data,
        ["account_id"],
        tuple(key for key in org_data if key != "account_id"),
    )

    evidence = evidence_values(account, source_id, collected_at)
    for alias in transformed.aliases:
        alias_values = {
            "organization_id": organization_id,
            "alias": alias.alias,
            "normalized_alias": alias.normalized_alias,
            "alias_kind": alias.alias_kind,
            **evidence,
        }
        upsert_returning_id(
            session,
            OrganizationAlias.__table__,
            alias_values,
            ["organization_id", "normalized_alias", "alias_kind"],
            (
                "alias",
                "collected_at",
                "as_of_date",
                "confidence",
                "verification_status",
                "transformation",
            ),
        )

    for unit in transformed.business_units:
        unit_values = {
            "organization_id": organization_id,
            "unit_key": unit.unit_key,
            "name": unit.name,
            "unit_type": unit.unit_type,
            "mapping_status": unit.mapping_status,
            **evidence,
        }
        upsert_returning_id(
            session,
            BusinessUnit.__table__,
            unit_values,
            ["organization_id", "unit_key"],
            (
                "name",
                "unit_type",
                "mapping_status",
                "collected_at",
                "as_of_date",
                "confidence",
                "verification_status",
                "transformation",
            ),
        )

    for office in transformed.offices:
        office_values = {
            "organization_id": organization_id,
            "office_key": office.office_key,
            "address_raw": office.address_raw,
            "city": office.city,
            "state": office.state,
            "country_code": "BR",
            "location": None,
            **evidence,
        }
        upsert_returning_id(
            session,
            Office.__table__,
            office_values,
            ["office_key"],
            (
                "organization_id",
                "address_raw",
                "city",
                "state",
                "collected_at",
                "as_of_date",
                "confidence",
                "verification_status",
                "transformation",
            ),
        )

    upsert_field_provenance(session, account, organization_id, source_id, collected_at)


def start_run(
    session: Session, input_sha256: str, row_count: int, started_at: datetime
) -> uuid.UUID:
    values = {
        "pipeline_name": PIPELINE_NAME,
        "input_sha256": input_sha256,
        "transform_version": TRANSFORM_VERSION,
        "status": "running",
        "started_at": started_at,
        "completed_at": None,
        "source_row_count": row_count,
        "staged_row_count": 0,
        "curated_row_count": 0,
        "error_message": None,
    }
    return upsert_returning_id(
        session,
        IngestionRun.__table__,
        values,
        ["pipeline_name", "input_sha256", "transform_version"],
        tuple(
            key
            for key in values
            if key not in {"pipeline_name", "input_sha256", "transform_version"}
        ),
    )


def run_etl(path: Path, database_url: str, *, engine: Engine | None = None) -> dict[str, Any]:
    accounts = load_pilot_csv(path)
    transformed = transform_accounts(accounts)
    input_hash = file_sha256(path)
    started_at = datetime.now(UTC)
    database_engine = engine or create_database_engine(database_url)
    session_factory: sessionmaker[Session] = create_session_factory(database_engine)

    with session_factory.begin() as session:
        run_id = start_run(session, input_hash, len(accounts), started_at)

    try:
        with session_factory.begin() as session:
            for account in transformed:
                load_curated_account(session, account, run_id, started_at)
            session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="complete",
                    completed_at=datetime.now(UTC),
                    staged_row_count=len(accounts),
                    curated_row_count=len(accounts),
                    error_message=None,
                )
            )
    except Exception as exc:
        with session_factory.begin() as session:
            session.execute(
                update(IngestionRun)
                .where(IngestionRun.id == run_id)
                .values(
                    status="failed", completed_at=datetime.now(UTC), error_message=str(exc)[:2000]
                )
            )
        raise

    return {
        "run_id": str(run_id),
        "input_sha256": input_hash,
        "source_rows": len(accounts),
        "staged_rows": len(accounts),
        "curated_organizations": len(accounts),
        "offices": sum(len(account.offices) for account in transformed),
        "business_units": sum(len(account.business_units) for account in transformed),
    }
