from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from networking_intel.etl.schemas import is_valid_cnpj
from networking_intel.etl.transform import normalize_name

Relation = Literal["primary_manager", "affiliate_manager", "bank_entity"]
ApprovalStatus = Literal["pending_human_review", "approved", "rejected"]

# Legal-form and filler tokens ignored when proposing review candidates.
_STOPWORDS = frozenset(
    [
        "ltda",
        "s",
        "a",
        "sa",
        "s/a",
        "de",
        "da",
        "do",
        "dos",
        "das",
        "e",
        "gestao",
        "gestora",
        "recursos",
        "investimentos",
        "asset",
        "management",
        "capital",
        "dtvm",
        "participacoes",
        "consultoria",
    ]
)


def digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def format_cnpj(value: str) -> str:
    d = digits(value)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


class RegistryEntity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cnpj: str
    relation: Relation
    relation_evidence: str
    approval_status: ApprovalStatus
    business_unit: str | None = None

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value: str) -> str:
        value = digits(value)
        if not is_valid_cnpj(value):
            raise ValueError(f"invalid CNPJ check digits: {value}")
        return value


class RegistryAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    primary_cnpj: str
    entities: tuple[RegistryEntity, ...]

    @model_validator(mode="after")
    def primary_is_listed(self) -> RegistryAccount:
        cnpjs = [entity.cnpj for entity in self.entities]
        if self.primary_cnpj not in cnpjs:
            raise ValueError(f"primary_cnpj {self.primary_cnpj} not among entities")
        if len(cnpjs) != len(set(cnpjs)):
            raise ValueError("duplicate CNPJ inside one account")
        return self

    def manager_cnpjs(self) -> tuple[str, ...]:
        return tuple(e.cnpj for e in self.entities if e.relation != "bank_entity")


class IdentityRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str
    as_of_date: str
    accounts: dict[str, RegistryAccount]

    @model_validator(mode="after")
    def cnpj_belongs_to_one_account(self) -> IdentityRegistry:
        owner: dict[str, str] = {}
        for account_id, account in self.accounts.items():
            for entity in account.entities:
                if entity.cnpj in owner:
                    raise ValueError(
                        f"CNPJ {entity.cnpj} mapped to {owner[entity.cnpj]} and {account_id}"
                    )
                owner[entity.cnpj] = account_id
        return self

    def account_for_cnpj(self) -> dict[str, str]:
        return {
            entity.cnpj: account_id
            for account_id, account in self.accounts.items()
            for entity in account.entities
        }

    def check_accounts(self, expected_account_ids: Iterable[str]) -> None:
        expected = set(expected_account_ids)
        actual = set(self.accounts)
        if expected != actual:
            raise ValueError(
                f"registry/pilot mismatch: missing={sorted(expected - actual)} "
                f"unexpected={sorted(actual - expected)}"
            )


def load_registry(path: Path) -> IdentityRegistry:
    with path.open(encoding="utf-8") as handle:
        return IdentityRegistry.model_validate(yaml.safe_load(handle))


def _tokens(value: str) -> set[str]:
    return {token for token in normalize_name(value).split() if token not in _STOPWORDS}


def propose_candidates(
    canonical_name: str, registered: Iterable[tuple[str, str, str]]
) -> list[tuple[str, str]]:
    """Review aid only: never applied automatically.

    Returns (cnpj, legal_name) rows whose distinctive tokens all appear in the
    registered legal or trade name. The output is written to the review queue.
    """
    wanted = _tokens(canonical_name)
    if not wanted:
        return []
    found: list[tuple[str, str]] = []
    for cnpj, legal_name, trade_name in registered:
        if wanted <= (_tokens(legal_name) | _tokens(trade_name)):
            found.append((cnpj, legal_name))
    return sorted(found)
