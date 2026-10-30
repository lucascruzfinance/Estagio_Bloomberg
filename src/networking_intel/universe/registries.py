"""CVM registries for the universe: intermediaries, fund classes and administrators."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from networking_intel.enrichment.cvm import (
    _clean,
    _float,
    _parse_date,
    normalize_phone,
    normalize_postal_code,
    zip_csv_rows,
)
from networking_intel.enrichment.identity import digits

# The registry carries a few unit errors (three funds at R$ 16.7 trillion each in 10/2026);
# the largest real Brazilian funds are around R$ 200 bi.
MAX_PLAUSIBLE_FUND_NAV = 3e11

INTERMEDIARY_KINDS = {
    "BANCOS MÚLTIPLOS COM CARTEIRA DE INVESTIMENTO": "banco_multiplo",
    "BANCOS DE INVESTIMENTOS": "banco_investimento",
    "CAIXAS ECONÔMICAS": "caixa_economica",
    "CORRETORAS": "corretora",
    "DISTRIBUIDORAS": "distribuidora",
    "CUSTODIANTES DE VALORES MOBILIÁRIOS": "custodiante",
    "ESCRITURADORES DE VALORES MOBILIÁRIOS": "escriturador",
    "ENTIDADES ADMINISTRADORAS DE MERCADO ORGANIZADO": "infraestrutura_mercado",
    "DEPOSITÁRIOS CENTRAIS DE VALORES MOBILIÁRIOS": "infraestrutura_mercado",
}


@dataclass
class IntermediaryRecord:
    cnpj: str
    legal_name: str
    trade_name: str | None
    kinds: set[str]
    registration_date: date | None
    street: str | None
    complement: str | None
    district: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    phone: str | None
    website: str | None
    control: str | None


def parse_intermediaries(content: bytes) -> dict[str, IntermediaryRecord]:
    """Active intermediaries; one CVM row per (entity, participation type) is merged."""
    records: dict[str, IntermediaryRecord] = {}
    for row in zip_csv_rows(content, "cad_intermed.csv"):
        if "FUNCIONAMENTO NORMAL" not in (row["SIT"] or "").upper():
            continue
        cnpj = digits(row["CNPJ"])
        kind = INTERMEDIARY_KINDS.get((row["TP_PARTIC"] or "").strip().upper(), "outro")
        registered = _parse_date(row["DT_REG"])
        record = records.get(cnpj)
        if record is None:
            records[cnpj] = IntermediaryRecord(
                cnpj=cnpj,
                legal_name=" ".join(row["DENOM_SOCIAL"].split()),
                trade_name=_clean(row["DENOM_COMERC"]),
                kinds={kind},
                registration_date=registered,
                street=_clean(row["LOGRADOURO"]),
                complement=_clean(row["COMPL"]),
                district=_clean(row["BAIRRO"]),
                city=_clean(row["MUN"]),
                state=_clean(row["UF"]),
                postal_code=normalize_postal_code(row["CEP"]),
                phone=normalize_phone(row["DDD_TEL"], row["TEL"]),
                website=_clean(row["SITE_WEB"]),
                control=_clean(row["CONTROLE_ACIONARIO"]),
            )
            continue
        record.kinds.add(kind)
        if registered and (
            record.registration_date is None or registered < record.registration_date
        ):
            record.registration_date = registered
    return records


@dataclass(frozen=True)
class UniverseClass:
    class_cnpj: str
    fund_cnpj: str
    manager_cnpj: str
    administrator_cnpj: str | None
    custodian_cnpj: str | None
    class_name: str
    fund_type: str | None
    class_type: str | None
    classification: str | None
    anbima_classification: str | None
    benchmark: str | None
    condominium: str | None
    is_exclusive: bool | None
    is_fic: bool | None
    target_investor: str | None
    status: str
    registry_nav_brl: float | None
    registry_nav_date: date | None
    constitution_date: date | None
    class_start_date: date | None
    cancel_date: date | None
    allows_full_offshore: bool | None
    nav_anomaly: bool = False

    @property
    def is_active(self) -> bool:
        return self.status.lower() == "em funcionamento normal"

    @property
    def is_selected(self) -> bool:
        """Open, non-exclusive, non-FIC classes: public vehicles holding their own portfolio.

        Unknown flags count as not selected (conservative): the class still feeds the
        manager-level aggregates.
        """
        return (
            self.is_active
            and self.condominium == "Aberto"
            and self.is_exclusive is False
            and self.is_fic is False
        )


def _flag(value: str | None) -> bool | None:
    value = _clean(value)
    return None if value is None else value.upper() == "S"


def parse_universe_classes(
    content: bytes, manager_cnpjs: Iterable[str], *, cancelled_since: date
) -> list[UniverseClass]:
    """Classes of the given managers: active ones plus those cancelled since a date."""
    wanted = set(manager_cnpjs)
    funds = {
        row["ID_Registro_Fundo"]: row
        for row in zip_csv_rows(content, "registro_fundo.csv")
        if digits(row["CPF_CNPJ_Gestor"] or "") in wanted
    }
    records: list[UniverseClass] = []
    for cls in zip_csv_rows(content, "registro_classe.csv"):
        fund = funds.get(cls["ID_Registro_Fundo"])
        if fund is None:
            continue
        cancel = _parse_date(fund["Data_Cancelamento"])
        status = (cls["Situacao"] or fund["Situacao"]).strip()
        if status.lower() != "em funcionamento normal" and (
            cancel is None or cancel < cancelled_since
        ):
            continue
        nav = _float(cls["Patrimonio_Liquido"])
        anomaly = nav is not None and nav > MAX_PLAUSIBLE_FUND_NAV
        records.append(
            UniverseClass(
                class_cnpj=digits(cls["CNPJ_Classe"] or fund["CNPJ_Fundo"]),
                fund_cnpj=digits(fund["CNPJ_Fundo"]),
                manager_cnpj=digits(fund["CPF_CNPJ_Gestor"]),
                administrator_cnpj=digits(fund["CNPJ_Administrador"] or "") or None,
                custodian_cnpj=digits(cls["CNPJ_Custodiante"] or "") or None,
                class_name=" ".join(
                    (cls["Denominacao_Social"] or fund["Denominacao_Social"]).split()
                ),
                fund_type=_clean(fund["Tipo_Fundo"]),
                class_type=_clean(cls["Tipo_Classe"]),
                classification=_clean(cls["Classificacao"]),
                anbima_classification=_clean(cls["Classificacao_Anbima"]),
                benchmark=_clean(cls["Indicador_Desempenho"]),
                condominium=_clean(cls["Forma_Condominio"]),
                is_exclusive=_flag(cls["Exclusivo"]),
                is_fic=_flag(cls["Classe_Cotas"]),
                target_investor=_clean(cls["Publico_Alvo"]),
                status=status,
                registry_nav_brl=None if anomaly else nav,
                registry_nav_date=_parse_date(cls["Data_Patrimonio_Liquido"]),
                constitution_date=_parse_date(fund["Data_Constituicao"]),
                class_start_date=_parse_date(cls["Data_Inicio"]),
                cancel_date=cancel,
                allows_full_offshore=_flag(cls["Permitido_Aplicacao_CemPorCento_Exterior"]),
                nav_anomaly=anomaly,
            )
        )
    unique = {record.class_cnpj: record for record in sorted(records, key=_class_sort_key)}
    return sorted(unique.values(), key=lambda r: (r.manager_cnpj, r.class_cnpj))


def _class_sort_key(record: UniverseClass) -> tuple[bool, str]:
    # Active rows sort last so they win the de-duplication by class CNPJ.
    return (record.is_active, record.class_cnpj)


@dataclass
class AdministratorStats:
    cnpj: str
    name: str
    active_funds: int = 0
    nav_brl: float = 0.0
    managers: set[str] = field(default_factory=set)


def administrator_stats(
    content: bytes,
) -> tuple[dict[str, AdministratorStats], list[dict[str, object]]]:
    """Active funds and registry NAV per fiduciary administrator (fund level).

    Returns the stats and the anomalies excluded by the plausibility guard.
    """
    stats: dict[str, AdministratorStats] = {}
    anomalies: list[dict[str, object]] = []
    for row in zip_csv_rows(content, "registro_fundo.csv"):
        if "funcionamento" not in (row["Situacao"] or "").lower():
            continue
        cnpj = digits(row["CNPJ_Administrador"] or "")
        if not cnpj:
            continue
        entry = stats.setdefault(
            cnpj, AdministratorStats(cnpj, " ".join((row["Administrador"] or "").split()))
        )
        entry.active_funds += 1
        entry.managers.add(digits(row["CPF_CNPJ_Gestor"] or ""))
        nav = _float(row["Patrimonio_Liquido"]) or 0.0
        if nav > MAX_PLAUSIBLE_FUND_NAV:
            anomalies.append(
                {
                    "fund_cnpj": digits(row["CNPJ_Fundo"]),
                    "fund_name": " ".join(row["Denominacao_Social"].split()),
                    "nav_brl": nav,
                    "nav_date": row["Data_Patrimonio_Liquido"],
                }
            )
            continue
        entry.nav_brl += nav
    return stats, anomalies


def manager_fund_counts(classes: Iterable[UniverseClass]) -> dict[str, dict[str, float]]:
    """Active classes, open non-exclusive classes and non-FIC registry NAV per manager."""
    out: dict[str, dict[str, float]] = defaultdict(
        lambda: {"active_classes": 0, "selected_classes": 0, "nav_registry_non_fic_brl": 0.0}
    )
    for record in classes:
        if not record.is_active:
            continue
        entry = out[record.manager_cnpj]
        entry["active_classes"] += 1
        entry["selected_classes"] += record.is_selected
        if record.is_fic is not True and record.registry_nav_brl:
            entry["nav_registry_non_fic_brl"] += record.registry_nav_brl
    return dict(out)
