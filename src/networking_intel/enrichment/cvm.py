from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

import polars as pl

from networking_intel.enrichment.identity import digits

CVM_ENCODING = "latin-1"
ACTIVE_MANAGER_STATUS = "EM FUNCIONAMENTO NORMAL"
INF_DIARIO_URL = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_{period}.zip"


def zip_csv_rows(content: bytes, member: str) -> list[dict[str, str]]:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        text = archive.read(member).decode(CVM_ENCODING)
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return None if value in {"", "-", "--", "-----"} else value


def _parse_date(value: str | None) -> date | None:
    value = _clean(value)
    return date.fromisoformat(value) if value else None


@dataclass(frozen=True)
class ManagerRecord:
    cnpj: str
    legal_name: str
    trade_name: str | None
    status: str
    status_since: date | None
    registration_date: date | None
    registration_category: str | None
    street: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    phone: str | None
    phone_raw: str | None
    email: str | None
    website: str | None

    @property
    def is_active(self) -> bool:
        return self.status.upper() == ACTIVE_MANAGER_STATUS

    @property
    def address_line(self) -> str | None:
        parts = [self.street, self.complement, self.district]
        locality = "/".join(part for part in (self.city, self.state) if part)
        text = ", ".join(part for part in parts if part)
        if not text:
            return None
        suffix = f", {locality}" if locality else ""
        cep = f", CEP {self.postal_code[:5]}-{self.postal_code[5:]}" if self.postal_code else ""
        return f"{text}{suffix}{cep}"


def normalize_postal_code(value: str | None) -> str | None:
    value = digits(value or "")
    if not value or len(value) > 8:
        return None
    return value.zfill(8)


def normalize_phone(ddd: str | None, number: str | None) -> str | None:
    ddd_digits = digits(ddd or "")
    number_digits = digits(number or "")
    if not number_digits:
        return None
    if ddd_digits == "55" and len(number_digits) == 10:
        # Some records store country code as DDD and area code inside the number.
        ddd_digits, number_digits = number_digits[:2], number_digits[2:]
    if len(ddd_digits) != 2 or len(number_digits) not in {8, 9}:
        return None
    if len(number_digits) == 9 and not number_digits.startswith("9"):
        return None  # nine-digit Brazilian numbers are mobiles starting with 9
    return f"+55{ddd_digits}{number_digits}"


def parse_managers(content: bytes) -> dict[str, ManagerRecord]:
    managers: dict[str, ManagerRecord] = {}
    for row in zip_csv_rows(content, "cad_adm_cart_pj.csv"):
        cnpj = digits(row["CNPJ"])
        managers[cnpj] = ManagerRecord(
            cnpj=cnpj,
            legal_name=" ".join(row["DENOM_SOCIAL"].split()),
            trade_name=_clean(row["DENOM_COMERC"]),
            status=row["SIT"].strip(),
            status_since=_parse_date(row["DT_INI_SIT"]),
            registration_date=_parse_date(row["DT_REG"]),
            registration_category=_clean(row["CATEG_REG"]),
            street=_clean(row["LOGRADOURO"]),
            complement=_clean(row["COMPL"]),
            district=_clean(row["BAIRRO"]),
            city=_clean(row["MUN"]),
            state=_clean(row["UF"]),
            postal_code=normalize_postal_code(row["CEP"]),
            phone=normalize_phone(row["DDD"], row["TEL"]),
            phone_raw=_clean(f"{row['DDD']} {row['TEL']}".strip()),
            email=_clean(row["EMAIL"]),
            website=_clean(row["SITE_ADMIN"]),
        )
    return managers


def parse_portfolio_directors(content: bytes, cnpjs: Iterable[str]) -> dict[str, list[str]]:
    """Directors responsible for portfolio management (Res. CVM 21) only.

    Compliance, risk and AML officers are deliberately not collected: they are
    not needed for account planning (LGPD data minimisation).
    """
    wanted = set(cnpjs)
    directors: dict[str, list[str]] = defaultdict(list)
    for row in zip_csv_rows(content, "cad_adm_cart_diretor.csv"):
        cnpj = digits(row["CNPJ"])
        name = _clean(row["DIRETOR"])
        if cnpj in wanted and name and name.title() not in directors[cnpj]:
            directors[cnpj].append(name.title())
    return dict(directors)


FUND_OF_FUNDS_TOKENS = (" FIC ", " FIC-", " CIC ", " FICFI", "COTAS DE FUNDOS", " EM COTAS ")


@dataclass(frozen=True)
class FundClass:
    manager_cnpj: str
    fund_cnpj: str
    class_cnpj: str
    fund_name: str
    class_name: str
    fund_type: str | None
    class_type: str | None
    classification: str | None
    anbima_classification: str | None
    benchmark: str | None
    status: str
    is_exclusive: bool
    target_investor: str | None
    condominium: str | None
    administrator_name: str | None
    registry_nav_brl: float | None
    registry_nav_date: date | None
    # Fund-level constitution date: class registration dates mostly reflect the
    # RCVM 175 adaptation (2024-2025) and must not be read as product launches.
    fund_constitution_date: date | None = None
    allows_full_offshore: bool | None = None

    @property
    def is_active(self) -> bool:
        return self.status.lower() == "em funcionamento normal"

    @property
    def is_fund_of_funds(self) -> bool:
        name = f" {self.class_name.upper()} "
        return any(token in name for token in FUND_OF_FUNDS_TOKENS)


def _yes_no(value: str | None) -> bool | None:
    value = _clean(value)
    return None if value is None else value.upper() == "S"


def _float(value: str | None) -> float | None:
    value = _clean(value)
    return float(value) if value else None


def parse_fund_classes(content: bytes, manager_cnpjs: Iterable[str]) -> list[FundClass]:
    """Exact join: registro_fundo.CPF_CNPJ_Gestor in the curated CNPJ set."""
    wanted = set(manager_cnpjs)
    funds = {
        row["ID_Registro_Fundo"]: row
        for row in zip_csv_rows(content, "registro_fundo.csv")
        if digits(row["CPF_CNPJ_Gestor"]) in wanted
    }
    classes_by_fund: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in zip_csv_rows(content, "registro_classe.csv"):
        if row["ID_Registro_Fundo"] in funds:
            classes_by_fund[row["ID_Registro_Fundo"]].append(row)

    records: list[FundClass] = []
    for fund_id, fund in funds.items():
        class_rows = classes_by_fund.get(fund_id) or [{}]
        for cls in class_rows:
            records.append(
                FundClass(
                    manager_cnpj=digits(fund["CPF_CNPJ_Gestor"]),
                    fund_cnpj=digits(fund["CNPJ_Fundo"]),
                    class_cnpj=digits(cls.get("CNPJ_Classe") or fund["CNPJ_Fundo"]),
                    fund_name=" ".join(fund["Denominacao_Social"].split()),
                    class_name=" ".join(
                        (cls.get("Denominacao_Social") or fund["Denominacao_Social"]).split()
                    ),
                    fund_type=_clean(fund["Tipo_Fundo"]),
                    class_type=_clean(cls.get("Tipo_Classe")),
                    classification=_clean(cls.get("Classificacao")),
                    anbima_classification=_clean(cls.get("Classificacao_Anbima")),
                    benchmark=_clean(cls.get("Indicador_Desempenho")),
                    status=(cls.get("Situacao") or fund["Situacao"]).strip(),
                    is_exclusive=(cls.get("Exclusivo") or "N").strip().upper() == "S",
                    target_investor=_clean(cls.get("Publico_Alvo")),
                    condominium=_clean(cls.get("Forma_Condominio")),
                    administrator_name=_clean(fund["Administrador"]),
                    registry_nav_brl=_float(
                        cls.get("Patrimonio_Liquido") or fund["Patrimonio_Liquido"]
                    ),
                    registry_nav_date=_parse_date(
                        cls.get("Data_Patrimonio_Liquido") or fund["Data_Patrimonio_Liquido"]
                    ),
                    fund_constitution_date=_parse_date(fund["Data_Constituicao"]),
                    allows_full_offshore=_yes_no(
                        cls.get("Permitido_Aplicacao_CemPorCento_Exterior")
                    ),
                )
            )
    return sorted(records, key=lambda record: (record.manager_cnpj, record.class_cnpj))


INF_DIARIO_SCHEMA = {
    "TP_FUNDO_CLASSE": pl.Utf8,
    "CNPJ_FUNDO_CLASSE": pl.Utf8,
    "ID_SUBCLASSE": pl.Utf8,
    "DT_COMPTC": pl.Utf8,
    "VL_TOTAL": pl.Float64,
    "VL_QUOTA": pl.Float64,
    "VL_PATRIM_LIQ": pl.Float64,
    "CAPTC_DIA": pl.Float64,
    "RESG_DIA": pl.Float64,
    "NR_COTST": pl.Int64,
}


def parse_daily_report(content: bytes, class_cnpjs: Iterable[str]) -> pl.DataFrame:
    """Rows of one monthly Informe Diário zip restricted to the mapped classes."""
    wanted = list(set(class_cnpjs))
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        member = next(name for name in archive.namelist() if name.endswith(".csv"))
        raw = archive.read(member)
    frame = pl.read_csv(
        raw,
        separator=";",
        encoding="utf8-lossy",
        schema_overrides=INF_DIARIO_SCHEMA,
    )
    return (
        frame.with_columns(
            pl.col("CNPJ_FUNDO_CLASSE").str.replace_all(r"\D", "").alias("class_cnpj"),
            pl.col("ID_SUBCLASSE").fill_null("").alias("subclass_id"),
            pl.col("DT_COMPTC").str.to_date("%Y-%m-%d").alias("date"),
        )
        .filter(pl.col("class_cnpj").is_in(wanted))
        .select(
            "class_cnpj",
            "subclass_id",
            pl.col("TP_FUNDO_CLASSE").alias("report_type"),
            "date",
            pl.col("VL_QUOTA").alias("quota"),
            pl.col("VL_PATRIM_LIQ").alias("nav_brl"),
            pl.col("CAPTC_DIA").alias("inflow_brl"),
            pl.col("RESG_DIA").alias("outflow_brl"),
            pl.col("NR_COTST").alias("investors"),
        )
    )
