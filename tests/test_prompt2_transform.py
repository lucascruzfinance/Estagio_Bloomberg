from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from networking_intel.etl.schemas import PilotAccount, is_valid_cnpj, load_pilot_csv
from networking_intel.etl.transform import transform_accounts

ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = ROOT / "data/staging/pilot_accounts.csv"


def test_pilot_transforms_to_expected_curated_counts() -> None:
    accounts = load_pilot_csv(PILOT_PATH)
    transformed = transform_accounts(accounts)

    assert len(transformed) == 12
    assert sum(len(account.offices) for account in transformed) == 14
    assert sum(len(account.business_units) for account in transformed) == 3
    assert len({account.pilot.account_id for account in transformed}) == 12


def test_bank_units_are_explicit_and_source_stated() -> None:
    transformed = transform_accounts(load_pilot_csv(PILOT_PATH))
    by_id = {account.pilot.account_id: account for account in transformed}

    assert {unit.name for unit in by_id["org-btg-pactual"].business_units} == {
        "Asset Management",
        "Investment Banking",
    }
    assert {unit.name for unit in by_id["org-itau-bba"].business_units} == {
        "Investment Banking e Mercados"
    }
    assert all(
        unit.mapping_status == "source_stated"
        for account_id in ("org-btg-pactual", "org-itau-bba")
        for unit in by_id[account_id].business_units
    )


def test_multi_office_fields_are_split_without_coordinates() -> None:
    transformed = transform_accounts(load_pilot_csv(PILOT_PATH))
    by_id = {account.pilot.account_id: account for account in transformed}

    for account_id in ("org-spx-capital", "org-vinci-compass"):
        offices = by_id[account_id].offices
        assert len(offices) == 2
        assert {office.state for office in offices} == {"SP", "RJ"}


def test_aliases_are_deterministic_and_unique_within_kind() -> None:
    for account in transform_accounts(load_pilot_csv(PILOT_PATH)):
        keys = {(alias.normalized_alias, alias.alias_kind) for alias in account.aliases}
        assert len(keys) == len(account.aliases)
        assert all(alias.normalized_alias for alias in account.aliases)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.461.756/0001-17", True),
        ("11.111.111/1111-11", False),
        ("12.461.756/0001-18", False),
        ("123", False),
    ],
)
def test_cnpj_check_digits(value: str, expected: bool) -> None:
    assert is_valid_cnpj(value) is expected


def test_invalid_cnpj_is_rejected_before_database() -> None:
    original = load_pilot_csv(PILOT_PATH)[0].model_dump(mode="json")
    original["cnpj"] = "11111111111111"
    with pytest.raises(ValidationError, match="invalid CNPJ"):
        PilotAccount.model_validate(original)


def test_compose_contract_uses_postgresql_16_postgis_and_migrations() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    services = compose["services"]
    assert services["db"]["image"] == "postgis/postgis:16-3.6"
    assert services["migrate"]["command"] == ["alembic", "upgrade", "head"]
    assert services["migrate"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert "profiles" not in services["migrate"]
