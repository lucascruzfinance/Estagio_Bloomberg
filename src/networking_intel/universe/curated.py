"""Curated accounts: the 12 pilot accounts plus wave 2, all with exact CNPJ lists."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from networking_intel.enrichment.identity import RegistryEntity, load_registry

Side = Literal["buy_side", "sell_side"]


class Wave2Account(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    display_name: str
    side: Side
    segment: str
    rationale: str
    primary_cnpj: str
    entities: tuple[RegistryEntity, ...]

    @model_validator(mode="after")
    def primary_is_listed(self) -> Wave2Account:
        cnpjs = [entity.cnpj for entity in self.entities]
        if self.primary_cnpj not in cnpjs:
            raise ValueError(f"primary_cnpj {self.primary_cnpj} not among entities")
        if len(cnpjs) != len(set(cnpjs)):
            raise ValueError("duplicate CNPJ inside one account")
        return self


class Wave2File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    as_of_date: str
    accounts: dict[str, Wave2Account]


class CuratedAccount(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_key: str
    display_name: str
    wave: Literal["pilot", "wave2"]
    side: Side
    segment: str
    rationale: str
    primary_cnpj: str
    entities: tuple[RegistryEntity, ...]


def load_curated(pilot_csv: Path, registry_path: Path, wave2_path: Path) -> list[CuratedAccount]:
    """Pilot first, then wave 2. A CNPJ may belong to one curated account only."""
    with pilot_csv.open(encoding="utf-8-sig", newline="") as handle:
        pilots = {row["account_id"]: row for row in csv.DictReader(handle)}
    registry = load_registry(registry_path)
    accounts = [
        CuratedAccount(
            account_key=account_id,
            display_name=pilots[account_id]["canonical_name"],
            wave="pilot",
            side="sell_side" if pilots[account_id]["institution_type"] == "banco" else "buy_side",
            segment=pilots[account_id]["institution_type"],
            rationale="Conta do piloto (Prompts 1 a 7).",
            primary_cnpj=account.primary_cnpj,
            entities=account.entities,
        )
        for account_id, account in registry.accounts.items()
    ]
    with wave2_path.open(encoding="utf-8") as handle:
        wave2 = Wave2File.model_validate(yaml.safe_load(handle))
    accounts += [
        CuratedAccount(
            account_key=key,
            display_name=account.display_name,
            wave="wave2",
            side=account.side,
            segment=account.segment,
            rationale=account.rationale,
            primary_cnpj=account.primary_cnpj,
            entities=account.entities,
        )
        for key, account in wave2.accounts.items()
    ]
    owner: dict[str, str] = {}
    for account in accounts:
        for entity in account.entities:
            if entity.cnpj in owner:
                raise ValueError(
                    f"CNPJ {entity.cnpj} in {owner[entity.cnpj]} and {account.account_key}"
                )
            owner[entity.cnpj] = account.account_key
    return accounts
