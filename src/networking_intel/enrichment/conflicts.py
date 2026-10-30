from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from urllib.parse import urlsplit

from unidecode import unidecode

from networking_intel.enrichment.cvm import ManagerRecord, normalize_phone
from networking_intel.enrichment.geocode import parse_street
from networking_intel.etl.schemas import PilotAccount
from networking_intel.etl.transform import stable_hash

RESOLUTION_STATUSES = (
    "pending_review",
    "accept_source",
    "keep_workbook",
    "both_valid",
    "dismissed",
    "no_longer_detected",
)
_ORD = r"(?:[º°ª]|O\.?)?"
_FLOOR = re.compile(
    r"(?<!\d)(\d{1,2})(?!\d)\s*"
    + _ORD
    + r"(?=(?:\s*(?:E|/|,)\s*\d{1,2}\s*"
    + _ORD
    + r")*\s*AND(?:AR|\.))"
)
_CITY_PREFIX = re.compile(r"^\s*[A-Za-zÀ-ú ]{2,30}:\s*")
_CEP = re.compile(r"\b(\d{5})-?(\d{3})\b")


@dataclass
class Conflict:
    conflict_id: str
    account_id: str
    entity_cnpj: str
    field: str
    rule: str
    severity: str
    workbook_value: str
    source_value: str
    source_id: str
    detected_at: str
    resolution_status: str = "pending_review"
    resolved_by: str = ""
    resolved_at: str = ""
    resolution_note: str = ""


def _conflict(
    account_id: str,
    entity_cnpj: str,
    field: str,
    rule: str,
    severity: str,
    workbook_value: str,
    source_value: str,
    detected_at: str,
) -> Conflict:
    key = stable_hash(
        "|".join((account_id, entity_cnpj, field, rule, workbook_value, source_value))
    )
    return Conflict(
        conflict_id=key[:16],
        account_id=account_id,
        entity_cnpj=entity_cnpj,
        field=field,
        rule=rule,
        severity=severity,
        workbook_value=workbook_value,
        source_value=source_value,
        source_id="cvm_cad_adm_cart",
        detected_at=detected_at,
    )


def _street_key(street: str) -> str:
    return unidecode(street).upper().replace(".", "")


def _floors(text: str | None) -> set[str]:
    return {str(int(number)) for number in _FLOOR.findall((text or "").upper())}


def _cep(text: str | None) -> str | None:
    match = _CEP.search(text or "")
    return f"{match.group(1)}{match.group(2)}" if match else None


def _domain(url: str | None) -> str | None:
    if not url:
        return None
    host = urlsplit(url if "//" in url else f"//{url}").netloc.lower()
    host = host.removeprefix("www.")
    return re.sub(r"\.br$", "", host) or None


def workbook_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("55") and len(digits) in {12, 13}:
        digits = digits[2:]
    return normalize_phone(digits[:2], digits[2:]) if len(digits) >= 10 else None


def detect_conflicts(
    pilot: PilotAccount,
    office_addresses: Sequence[str],
    entities: Sequence[ManagerRecord],
    detected_at: str,
) -> list[Conflict]:
    account = pilot.account_id
    primary = entities[0] if entities else None
    conflicts: list[Conflict] = []
    if primary is None:
        return conflicts

    phone = workbook_phone(pilot.phone_public)
    official_phones = {entity.phone for entity in entities if entity.phone}
    if phone and official_phones and phone not in official_phones:
        conflicts.append(
            _conflict(
                account,
                primary.cnpj,
                "phone_public",
                "phone_not_in_official_registry",
                "medium",
                pilot.phone_public or "",
                " | ".join(sorted(official_phones)),
                detected_at,
            )
        )
    for entity in entities:
        if entity.phone_raw and entity.phone is None:
            conflicts.append(
                _conflict(
                    account,
                    entity.cnpj,
                    "phone_public",
                    "official_phone_malformed",
                    "low",
                    pilot.phone_public or "",
                    entity.phone_raw,
                    detected_at,
                )
            )

    domain = _domain(pilot.website_url)
    official_domains = {d for d in (_domain(entity.website) for entity in entities) if d}
    if domain and official_domains and domain not in official_domains:
        conflicts.append(
            _conflict(
                account,
                primary.cnpj,
                "website_url",
                "website_domain_differs",
                "low",
                pilot.website_url or "",
                " | ".join(sorted(official_domains)),
                detected_at,
            )
        )

    for raw_office in office_addresses:
        office = _CITY_PREFIX.sub("", raw_office)
        street, number = parse_street(office)
        same_street = [
            entity
            for entity in entities
            if entity.street and _street_key(parse_street(entity.street)[0]) == _street_key(street)
        ]
        exact = [entity for entity in same_street if parse_street(entity.street or "")[1] == number]
        if not exact:
            official = " | ".join(
                sorted({entity.address_line or "" for entity in (same_street or [primary])})
            )
            rule = "street_number_differs" if same_street else "address_not_in_official_registry"
            conflicts.append(
                _conflict(
                    account,
                    (same_street or [primary])[0].cnpj,
                    "address_raw",
                    rule,
                    "medium",
                    raw_office,
                    official,
                    detected_at,
                )
            )
            continue
        match = exact[0]
        workbook_floors = _floors(office)
        official_floors = set().union(
            *(_floors(f"{entity.street} {entity.complement or ''}") for entity in exact)
        )
        if workbook_floors and official_floors and not workbook_floors & official_floors:
            conflicts.append(
                _conflict(
                    account,
                    match.cnpj,
                    "address_floor",
                    "floor_differs",
                    "low",
                    raw_office,
                    " | ".join(sorted({e.address_line or "" for e in exact})),
                    detected_at,
                )
            )
        workbook_cep = _cep(office)
        if workbook_cep and match.postal_code and workbook_cep != match.postal_code:
            conflicts.append(
                _conflict(
                    account,
                    match.cnpj,
                    "postal_code",
                    "postal_code_differs",
                    "low",
                    raw_office,
                    match.address_line or "",
                    detected_at,
                )
            )
    return conflicts


def merge_review_queue(path: Path, detected: Iterable[Conflict]) -> list[Conflict]:
    """Keep human decisions across runs; never drop a reviewed row."""
    existing: dict[str, Conflict] = {}
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                existing[row["conflict_id"]] = Conflict(**row)
    merged: dict[str, Conflict] = {}
    for conflict in detected:
        previous = existing.pop(conflict.conflict_id, None)
        if previous is not None and previous.resolution_status != "no_longer_detected":
            conflict.resolution_status = previous.resolution_status
            conflict.resolved_by = previous.resolved_by
            conflict.resolved_at = previous.resolved_at
            conflict.resolution_note = previous.resolution_note
            conflict.detected_at = previous.detected_at
        merged[conflict.conflict_id] = conflict
    for conflict_id, stale in existing.items():
        if stale.resolution_status == "pending_review":
            stale.resolution_status = "no_longer_detected"
        merged[conflict_id] = stale
    for conflict in merged.values():
        if conflict.resolution_status not in RESOLUTION_STATUSES:
            raise ValueError(
                f"invalid resolution_status in review queue: {conflict.resolution_status}"
            )
    rows = sorted(merged.values(), key=lambda c: (c.account_id, c.field, c.conflict_id))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[f.name for f in fields(Conflict)])
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)
    return rows
