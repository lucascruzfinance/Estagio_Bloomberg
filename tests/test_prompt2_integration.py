from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from networking_intel.db.models import BusinessUnit, Office, Organization
from networking_intel.etl.load import run_etl

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database_url() -> str:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    return DATABASE_URL


@pytest.fixture(scope="module")
def migrated_database(database_url: str) -> str:
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    os.environ["DATABASE_URL"] = database_url
    # Start from an empty schema so the module never depends on data loaded elsewhere;
    # this also exercises every downgrade path.
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return database_url


def test_etl_is_idempotent_and_reconciled(migrated_database: str) -> None:
    pilot_path = ROOT / "data/staging/pilot_accounts.csv"
    first = run_etl(pilot_path, migrated_database)
    second = run_etl(pilot_path, migrated_database)

    assert first["input_sha256"] == second["input_sha256"]
    engine = create_engine(migrated_database)
    with Session(engine) as session:
        pilot_ids = (
            select(func.count())
            .select_from(Organization)
            .where(Organization.account_id.like("org-%"))
        )
        assert session.scalar(pilot_ids) == 12
        assert session.scalar(select(func.count()).select_from(Office)) == 14
        assert session.scalar(select(func.count()).select_from(BusinessUnit)) == 3


def test_database_rejects_invalid_cnpj_and_orphan_reference(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    with Session(engine) as session:
        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "UPDATE organizations SET cnpj = '11111111111111' WHERE account_id = 'org-spx-capital'"
                )
            )
            session.commit()
        session.rollback()

        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE organizations SET as_of_date = '2026-02-30' "
                    "WHERE account_id = 'org-spx-capital'"
                )
            )
            session.commit()
        session.rollback()

        with pytest.raises(IntegrityError):
            session.execute(
                text(
                    "UPDATE organizations SET source_id = gen_random_uuid() "
                    "WHERE account_id = 'org-spx-capital'"
                )
            )
            session.commit()


def test_postgis_column_contract(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT type, srid FROM geometry_columns "
                "WHERE f_table_schema = current_schema() AND f_table_name = 'offices'"
            )
        ).one()
        assert row.type == "POINT"
        assert row.srid == 4326
