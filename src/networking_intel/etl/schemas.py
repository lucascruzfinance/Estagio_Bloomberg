from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

NULLABLE_TEXT_FIELDS = (
    "legal_name",
    "cnpj",
    "linkedin_url",
    "email_public",
    "phone_public",
    "website_url",
    "careers_channel",
    "address_raw",
    "city",
    "state",
    "verification_status",
    "as_of_date",
    "verification_locator",
    "verification_source_url",
    "missing_fields",
    "data_quality_flags",
)


def is_valid_cnpj(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False

    def calculate_digit(partial: str, weights: list[int]) -> int:
        remainder = (
            sum(int(digit) * weight for digit, weight in zip(partial, weights, strict=True)) % 11
        )
        return 0 if remainder < 2 else 11 - remainder

    first = calculate_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = calculate_digit(digits[:12] + str(first), [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digits[-2:] == f"{first}{second}"


class PilotAccount(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    account_id: str = Field(pattern=r"^org-[a-z0-9-]+$")
    canonical_name: str = Field(min_length=1)
    legal_name: str | None = None
    group_name: str = Field(min_length=1)
    institution_type: str = Field(min_length=1)
    strategy_profile: str = Field(min_length=1)
    analysis_unit: Literal["organização", "mesa/área"]
    business_unit_required: bool
    pilot_wave: int = Field(ge=1)
    cnpj: str | None = None
    linkedin_url: str | None = None
    email_public: str | None = None
    phone_public: str | None = None
    website_url: str | None = None
    careers_channel: str | None = None
    address_raw: str | None = None
    city: str | None = None
    state: str | None = None
    verification_status: str | None = None
    evidence_class: Literal["source_stated", "verified_fact", "inference", "gap"]
    confidence: Literal["high", "medium", "low", "blocked"]
    as_of_date: date | None = None
    source_sheet: str = Field(min_length=1)
    source_row: int = Field(ge=2)
    source_locator: str = Field(min_length=1)
    verification_locator: str | None = None
    verification_source_url: str | None = None
    raw_aliases: str = Field(min_length=1)
    missing_fields: str | None = None
    data_quality_flags: str | None = None
    human_approval_required: bool
    source_workbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator(*NULLABLE_TEXT_FIELDS, mode="before")
    @classmethod
    def empty_string_to_none(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value: str | None) -> str | None:
        if value is None:
            return None
        digits = re.sub(r"\D", "", value)
        if not is_valid_cnpj(digits):
            raise ValueError("invalid CNPJ check digits")
        return digits


def load_pilot_csv(path: Path) -> list[PilotAccount]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [PilotAccount.model_validate(row) for row in reader]
    if len(rows) != 12:
        raise ValueError(f"pilot must contain exactly 12 accounts, got {len(rows)}")
    if len({row.account_id for row in rows}) != len(rows):
        raise ValueError("pilot account_id values must be unique")
    return rows
