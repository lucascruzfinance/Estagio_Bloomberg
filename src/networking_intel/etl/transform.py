from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from unidecode import unidecode

from networking_intel.etl.schemas import PilotAccount

TRANSFORM_VERSION = "prompt2-v1"
TRANSFORMATION = (
    "prompt2-v1: null-normalization; deterministic aliases; multi-office split; "
    "source-stated bank-unit split"
)

BANK_UNITS: dict[str, tuple[str, ...]] = {
    "org-btg-pactual": ("Asset Management", "Investment Banking"),
    "org-itau-bba": ("Investment Banking e Mercados",),
}


def normalize_name(value: str) -> str:
    text = unidecode(value).lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AliasRecord:
    alias: str
    normalized_alias: str
    alias_kind: str


@dataclass(frozen=True)
class OfficeRecord:
    office_key: str
    address_raw: str
    city: str | None
    state: str | None


@dataclass(frozen=True)
class BusinessUnitRecord:
    unit_key: str
    name: str
    unit_type: str
    mapping_status: str


@dataclass(frozen=True)
class TransformedAccount:
    pilot: PilotAccount
    aliases: tuple[AliasRecord, ...]
    offices: tuple[OfficeRecord, ...]
    business_units: tuple[BusinessUnitRecord, ...]


def build_aliases(account: PilotAccount) -> tuple[AliasRecord, ...]:
    candidates: list[tuple[str, str]] = [
        (account.canonical_name, "canonical"),
        (account.group_name, "group"),
    ]
    candidates.extend((alias.strip(), "raw_name") for alias in account.raw_aliases.split(" | "))
    deduplicated: dict[tuple[str, str], AliasRecord] = {}
    for alias, alias_kind in candidates:
        normalized = normalize_name(alias)
        deduplicated[(normalized, alias_kind)] = AliasRecord(alias, normalized, alias_kind)
    return tuple(
        sorted(deduplicated.values(), key=lambda item: (item.alias_kind, item.normalized_alias))
    )


def build_offices(account: PilotAccount) -> tuple[OfficeRecord, ...]:
    if not account.address_raw:
        return ()
    addresses = [part.strip() for part in account.address_raw.split(" | ")]
    cities = [part.strip() for part in account.city.split(" | ")] if account.city else []
    states = [part.strip() for part in account.state.split(" | ")] if account.state else []
    offices: list[OfficeRecord] = []
    for index, address in enumerate(addresses):
        city = cities[index] if index < len(cities) else None
        state = states[index] if index < len(states) else None
        office_key = stable_hash(f"{account.account_id}|{normalize_name(address)}")
        offices.append(OfficeRecord(office_key, address, city, state))
    return tuple(offices)


def build_business_units(account: PilotAccount) -> tuple[BusinessUnitRecord, ...]:
    names = BANK_UNITS.get(account.account_id, ())
    return tuple(
        BusinessUnitRecord(
            unit_key=f"{account.account_id}:{normalize_name(name).replace(' ', '-')}",
            name=name,
            unit_type="mesa/área",
            mapping_status="source_stated",
        )
        for name in names
    )


def transform_accounts(accounts: list[PilotAccount]) -> list[TransformedAccount]:
    return [
        TransformedAccount(
            pilot=account,
            aliases=build_aliases(account),
            offices=build_offices(account),
            business_units=build_business_units(account),
        )
        for account in accounts
    ]
