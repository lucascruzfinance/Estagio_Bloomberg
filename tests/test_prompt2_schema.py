from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from geoalchemy2 import Geometry

from networking_intel.db import models  # noqa: F401
from networking_intel.db.base import Base

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_TABLES = {
    "organizations",
    "business_units",
    "offices",
    "people",
    "funds",
    "fund_observations",
    "commercial_signals",
    "product_fit",
    "sources",
    "opportunity_scores",
    "score_runs",
    "legal_entities",
    "fund_metrics",
    "data_conflicts",
    "quality_reports",
    "organization_aliases",
    "field_provenance",
    "ingestion_runs",
    "staging_pilot_accounts",
}


def test_required_tables_are_modeled() -> None:
    assert set(Base.metadata.tables) >= REQUIRED_TABLES


def test_office_location_is_postgis_point_4326() -> None:
    location = Base.metadata.tables["offices"].c.location
    assert isinstance(location.type, Geometry)
    assert location.type.geometry_type == "POINT"
    assert location.type.srid == 4326


def test_foreign_keys_protect_core_references() -> None:
    for table_name, column_name in (
        ("business_units", "organization_id"),
        ("offices", "organization_id"),
        ("people", "organization_id"),
        ("funds", "organization_id"),
        ("fund_observations", "fund_id"),
        ("opportunity_scores", "organization_id"),
        ("legal_entities", "organization_id"),
        ("fund_metrics", "fund_id"),
    ):
        foreign_keys = Base.metadata.tables[table_name].c[column_name].foreign_keys
        assert len(foreign_keys) == 1


def test_initial_migration_compiles_offline() -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = (
        "postgresql+psycopg://networking:local-development-only-change-me@localhost:5432/networking"
    )
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    sql = result.stdout
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql
    assert "CREATE TABLE organizations" in sql
    assert "CREATE TABLE field_provenance" in sql
    assert "geometry(POINT,4326)" in sql
    assert "is_valid_cnpj" in sql
