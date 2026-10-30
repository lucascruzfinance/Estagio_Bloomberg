from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from unidecode import unidecode

from networking_intel.enrichment.cache import RawArtifact
from networking_intel.enrichment.http import Fetcher, SourceUnavailableError
from networking_intel.enrichment.sources import get_source

Precision = Literal["address", "street", "neighbourhood", "city", "unknown", "none"]
NOMINATIM_SOURCE = "osm_nominatim"

_ABBREVIATIONS = (
    (r"^AV\.?\s+", "AVENIDA "),
    (r"^R\.?\s+", "RUA "),
    (r"^P[CÇ]A?\.?\s+", "PRAÇA "),
    (r"\bBRIG\.?\s+", "BRIGADEIRO "),
    (r"\bBRG\.?\s+", "BRIGADEIRO "),
    (r"\bDR\.?\s+", "DOUTOR "),
)
_NUMBER = re.compile(
    r"^(?P<street>.*?[A-ZÀ-Ü.])\s*,?\s*(?:N\.?\s*[º°O]\.?\s*|N\.\s*)?"
    r"(?P<number>\d{1,3}(?:\.\d{3})+|\d{1,5})(?!\s*[º°ºª]|\s*AND)"
)


@dataclass(frozen=True)
class ParsedAddress:
    street: str
    number: str | None
    city: str | None
    state: str | None
    postal_code: str | None

    @property
    def key(self) -> str:
        parts = [self.street, self.number or "", self.city or "", self.state or ""]
        return unidecode("|".join(parts)).upper()


def parse_street(raw: str) -> tuple[str, str | None]:
    text = " ".join(raw.upper().split())
    text = text.split("/")[0].strip()
    for pattern, replacement in _ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    match = _NUMBER.match(text)
    if not match:
        return text.strip(" ,").title(), None
    street = match.group("street").strip(" ,.")
    number = match.group("number").replace(".", "")
    return street.title(), number


def parse_address(
    street_raw: str, city: str | None, state: str | None, postal_code: str | None
) -> ParsedAddress:
    street, number = parse_street(street_raw)
    return ParsedAddress(
        street=street,
        number=number,
        city=city.title() if city else None,
        state=state,
        postal_code=postal_code,
    )


@dataclass(frozen=True)
class GeocodeResult:
    address_key: str
    query: str
    provider: str
    attribution: str
    status: str
    fetched_at: str | None
    latitude: float | None
    longitude: float | None
    precision: Precision
    is_exact: bool
    display_name: str | None
    osm_type: str | None
    osm_id: int | None
    raw_sha256: str | None
    raw_path: str | None


_STREET_TYPES = frozenset({"RUA", "AVENIDA", "PRACA", "PRAIA", "ALAMEDA", "ESTRADA", "RODOVIA"})
_STREET_FILLERS = frozenset({"DE", "DA", "DO", "DAS", "DOS", "E", "JR", "JUNIOR"})


def _norm_tokens(value: str) -> set[str]:
    words = re.sub(r"[^A-Z0-9 ]", " ", unidecode(value).upper()).split()
    return {w for w in words if w not in _STREET_TYPES and w not in _STREET_FILLERS and len(w) > 1}


def locality_matches(result: dict[str, Any], address: ParsedAddress) -> bool:
    """Reject hits in another municipality or state (e.g. same number, wrong city)."""
    if not address.city:
        return True
    found = result.get("address") or {}
    candidates = [
        str(found.get(key, ""))
        for key in ("city", "town", "municipality", "village", "city_district")
    ]
    expected = unidecode(address.city).upper()
    return any(unidecode(value).upper() == expected for value in candidates if value)


def street_matches(result: dict[str, Any], address: ParsedAddress) -> bool:
    road = str((result.get("address") or {}).get("road", ""))
    wanted = _norm_tokens(address.street)
    if not road or not wanted:
        return False
    return len(wanted & _norm_tokens(road)) / len(wanted) >= 0.6


def classify_precision(result: dict[str, Any], address: ParsedAddress) -> Precision:
    found = result.get("address") or {}
    house_number = re.sub(r"\D", "", str(found.get("house_number", "")))
    on_street = street_matches(result, address)
    if address.number and house_number == address.number and on_street:
        return "address"
    kind = str(result.get("addresstype") or result.get("type") or "")
    if on_street or result.get("category") == "highway" or kind in {"road", "street"}:
        return "street"
    if kind in {"suburb", "neighbourhood", "quarter", "city_district"}:
        return "neighbourhood"
    if kind in {"city", "town", "municipality", "village"}:
        return "city"
    return "unknown"


def _queries(address: ParsedAddress) -> list[dict[str, str]]:
    base = {"format": "jsonv2", "addressdetails": "1", "limit": "1", "countrycodes": "br"}
    street = f"{address.number} {address.street}" if address.number else address.street
    structured = {**base, "street": street, "country": "Brasil"}
    if address.city:
        structured["city"] = address.city
    if address.state:
        structured["state"] = address.state
    free_text = ", ".join(
        part for part in (address.street, address.number, address.city, address.state) if part
    )
    queries = [structured, {**base, "q": f"{free_text}, Brasil"}]
    if address.postal_code:
        postal = f"{address.postal_code[:5]}-{address.postal_code[5:]}"
        queries.append({**structured, "postalcode": postal})
    return queries


def _result(
    address: ParsedAddress,
    query: dict[str, str],
    status: str,
    artifact: RawArtifact | None = None,
    hit: dict[str, Any] | None = None,
) -> GeocodeResult:
    spec = get_source(NOMINATIM_SOURCE)
    precision: Precision = classify_precision(hit, address) if hit else "none"
    return GeocodeResult(
        address_key=address.key,
        query=json.dumps(query, ensure_ascii=False, sort_keys=True),
        provider="Nominatim (OpenStreetMap)",
        attribution=spec.attribution,
        status=status,
        fetched_at=artifact.fetched_at if artifact else None,
        latitude=float(hit["lat"]) if hit else None,
        longitude=float(hit["lon"]) if hit else None,
        precision=precision,
        is_exact=precision == "address",
        display_name=hit.get("display_name") if hit else None,
        osm_type=hit.get("osm_type") if hit else None,
        osm_id=int(hit["osm_id"]) if hit and hit.get("osm_id") is not None else None,
        raw_sha256=artifact.sha256 if artifact else None,
        raw_path=artifact.path if artifact else None,
    )


def geocode(fetcher: Fetcher, address: ParsedAddress) -> GeocodeResult:
    spec = get_source(NOMINATIM_SOURCE)
    last_query: dict[str, str] = {}
    last_artifact: RawArtifact | None = None
    best: tuple[dict[str, str], RawArtifact, dict[str, Any]] | None = None
    rejected = False
    for query in _queries(address):
        last_query = query
        try:
            artifact = fetcher.fetch(NOMINATIM_SOURCE, spec.base_url, params=query, suffix=".json")
        except SourceUnavailableError:
            return _result(address, query, "source_unavailable")
        last_artifact = artifact
        hits = json.loads(fetcher.cache.read_bytes(artifact))
        if not hits:
            continue
        if not locality_matches(hits[0], address):
            rejected = True
            continue
        candidate = (query, artifact, hits[0])
        if classify_precision(hits[0], address) == "address":
            return _result(address, query, "matched", artifact, hits[0])
        best = best or candidate
    if best is not None:
        return _result(address, best[0], "matched_approximate", best[1], best[2])
    status = "rejected_wrong_locality" if rejected else "no_match"
    return _result(address, last_query, status, last_artifact)
