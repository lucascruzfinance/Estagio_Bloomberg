"""Financial centres, building keys and H3 cells for São Paulo and Rio de Janeiro."""

from __future__ import annotations

import re

import h3  # type: ignore[import-untyped]
from unidecode import unidecode

from networking_intel.enrichment.geocode import parse_street

# Municipalities in scope. Osasco hosts the Bradesco headquarters (Cidade de Deus).
UNIVERSE_CITIES = frozenset({("SP", "SAO PAULO"), ("SP", "OSASCO"), ("RJ", "RIO DE JANEIRO")})

FARIA_LIMA = "Faria Lima"
JK = "JK / Vila Olímpia"
JARDINS = "Cidade Jardim / Jardins"
PAULISTA = "Paulista"
BERRINI = "Berrini / Chucri Zaidan"
CENTRO_SP = "Centro (SP)"
LEBLON = "Leblon / Ipanema (RJ)"
BOTAFOGO = "Botafogo (RJ)"
CENTRO_RJ = "Centro (RJ)"
BARRA = "Barra / São Conrado (RJ)"
OSASCO = "Osasco"
OTHER_SP = "Outros bairros (SP)"
OTHER_RJ = "Outros bairros (RJ)"

MAPPED_CENTRES = (
    FARIA_LIMA,
    JK,
    JARDINS,
    PAULISTA,
    BERRINI,
    CENTRO_SP,
    LEBLON,
    BOTAFOGO,
    CENTRO_RJ,
    BARRA,
    OSASCO,
)

# São Paulo: the avenue identifies the centre better than the neighbourhood
# (Faria Lima crosses Pinheiros and Itaim Bibi). Order matters: first match wins.
SP_STREETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (FARIA_LIMA, ("brigadeiro faria lima", "faria lima")),
    (
        JK,
        (
            "juscelino kubitschek",
            "presidente juscelino",
            "funchal",
            "gomes de carvalho",
            "elvira ferraz",
            "minas de prata",
            "leopoldo couto",
            "joaquim floriano",
            "jeronimo da veiga",
            "cardoso de melo",
            "olimpiadas",
            "iguatemi",
            "tabapua",
            "renato paes de barros",
            "pedroso alvarenga",
            "clodomiro amazonas",
            "amauri",
            "bandeira paulista",
        ),
    ),
    (
        JARDINS,
        (
            "cidade jardim",
            "sao gabriel",
            "europa",
            "nove de julho",
            "reboucas",
            "avenida brasil",
            "groenlandia",
            "horacio lafer",
        ),
    ),
    (PAULISTA, ("paulista", "alameda santos", "haddock lobo", "bela cintra")),
    (BERRINI, ("berrini", "chucri zaidan", "nacoes unidas", "roque petroni")),
    (CENTRO_SP, ("boa vista", "quinze de novembro", "xv de novembro", "antonio prado")),
)
SP_DISTRICTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (FARIA_LIMA, ("pinheiros", "jardim paulistano")),
    (JK, ("itaim bibi", "itaim", "vila olimpia", "vila nova conceicao")),
    (JARDINS, ("jardim europa", "jardim america", "jardim paulista", "cerqueira cesar")),
    (PAULISTA, ("bela vista", "consolacao")),
    (
        BERRINI,
        ("brooklin", "cidade moncoes", "vila cordeiro", "chacara santo antonio", "santo amaro"),
    ),
    (CENTRO_SP, ("centro", "se", "republica")),
)
RJ_DISTRICTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (LEBLON, ("leblon", "ipanema", "gavea", "jardim botanico", "lagoa", "humaita")),
    (BOTAFOGO, ("botafogo", "flamengo", "urca")),
    (CENTRO_RJ, ("centro", "saude")),
    (BARRA, ("barra da tijuca", "sao conrado")),
)


def norm(text: str | None) -> str:
    """ASCII, lower case, single spaces; punctuation becomes a space."""
    value = unidecode(text or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", value)).strip()


def in_universe(state: str | None, city: str | None) -> bool:
    return (norm(state).upper(), norm(city).upper()) in UNIVERSE_CITIES


def _match(
    value: str, table: tuple[tuple[str, tuple[str, ...]], ...], *, whole: bool
) -> str | None:
    for centre, needles in table:
        for needle in needles:
            if (value == needle or value.startswith(needle + " ")) if whole else needle in value:
                return centre
    return None


def centre_of(
    state: str | None, city: str | None, street: str | None, district: str | None
) -> tuple[str | None, str | None]:
    """(centre, basis). Basis is 'street' or 'district'; None outside the universe."""
    if not in_universe(state, city):
        return None, None
    if norm(city) == "osasco":
        return OSASCO, "city"
    district_n = norm(district)
    if norm(state) == "rj":
        found = _match(district_n, RJ_DISTRICTS, whole=True)
        return (found, "district") if found else (OTHER_RJ, "district")
    found = _match(norm(street), SP_STREETS, whole=False)
    if found:
        return found, "street"
    found = _match(district_n, SP_DISTRICTS, whole=True)
    return (found, "district") if found else (OTHER_SP, "district")


# Door number at the start of the complement ("4440, 15 ANDAR", "Nº 5.966"), never a
# floor ("6º andar", "14 E 15º ANDAR").
_COMPLEMENT_NUMBER = re.compile(
    r"^\s*(?:N[º°O]?\.?\s*)?(?P<number>\d{1,3}(?:\.\d{3})+|\d{1,5})"
    r"(?!\d|\s*(?:[º°ª]|O\b|ANDAR|AND\b|E\s+\d))"
)


def street_with_number(street_raw: str | None, complement: str | None) -> str | None:
    """The street line, completed with the door number found in the complement."""
    if not street_raw:
        return None
    _, number = parse_street(street_raw)
    if number or not complement:
        return street_raw
    match = _COMPLEMENT_NUMBER.match(complement.upper())
    return f"{street_raw}, {match.group('number')}" if match else street_raw


def building_key(
    street_raw: str | None, city: str | None, state: str | None, complement: str | None = None
) -> str | None:
    """Street + door number + city: tenants of one building share the key."""
    line = street_with_number(street_raw, complement)
    if not line:
        return None
    street, number = parse_street(line)
    if not number:
        return None
    return unidecode(f"{street}|{number}|{city or ''}|{state or ''}").upper()


def h3_cells(latitude: float | None, longitude: float | None) -> tuple[str | None, str | None]:
    """Resolution 8 (~0.7 km²) for density, 9 (~0.1 km²) for blocks."""
    if latitude is None or longitude is None:
        return None, None
    return h3.latlng_to_cell(latitude, longitude, 8), h3.latlng_to_cell(latitude, longitude, 9)
