from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from networking_intel.etl.load_universe import expected_counts, run_universe_load

ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def database_url() -> str:
    if not DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = DATABASE_URL
    command.upgrade(config, "head")
    return DATABASE_URL


def test_universe_load_is_idempotent_and_reconciled(database_url: str) -> None:
    first = run_universe_load(ROOT, database_url)
    second = run_universe_load(ROOT, database_url)
    expected = expected_counts(ROOT)
    for table, count in expected.items():
        assert first[table] == second[table] == count, table
    engine = create_engine(database_url)
    with engine.connect() as connection:
        tables = connection.execute(
            text(
                "SELECT (SELECT count(*) FROM universe_entities),"
                " (SELECT count(*) FROM fund_daily),"
                " (SELECT count(*) FROM curated_accounts WHERE approval_status = 'pending_human_review'),"
                " (SELECT count(*) FROM group_memberships WHERE basis <> 'curated_registry'"
                "   AND approval_status <> 'source_exact'),"
                " (SELECT count(*) FROM universe_entities WHERE geocode_is_exact"
                "   AND geocode_precision <> 'address'),"
                " (SELECT count(*) FROM crm_status)"
            )
        ).one()
    engine.dispose()
    assert tables[0] == expected["universe_entities"]
    assert tables[1] == expected["fund_daily"]
    assert tables[2] == 36  # every curated link still awaits human review
    assert tables[3] == 0  # name similarity never creates an approved link
    assert tables[4] == 0
    assert tables[5] == 0  # no invented commercial status
