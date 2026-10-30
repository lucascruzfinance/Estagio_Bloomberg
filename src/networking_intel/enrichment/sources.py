from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

DataNature = Literal["real", "sandbox", "fictitious"]


class SandboxDataError(RuntimeError):
    """Raised when a non-production dataset is about to be used as real data."""


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    publisher: str
    title: str
    base_url: str
    data_nature: DataNature
    licence: str
    attribution: str
    max_age: timedelta
    rate_limit_seconds: float


SOURCES: dict[str, SourceSpec] = {
    spec.source_id: spec
    for spec in (
        SourceSpec(
            source_id="cvm_cad_adm_cart",
            publisher="CVM",
            title="Cadastro de Administradores de Carteira",
            base_url="https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip",
            data_nature="real",
            licence="Open Database License (ODbL) — Portal de Dados Abertos da CVM",
            attribution="Fonte: CVM — Dados Abertos",
            max_age=timedelta(days=7),
            rate_limit_seconds=1.0,
        ),
        SourceSpec(
            source_id="cvm_registro_fundo_classe",
            publisher="CVM",
            title="Registro de Fundos, Classes e Subclasses (RCVM 175)",
            base_url="https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip",
            data_nature="real",
            licence="Open Database License (ODbL) — Portal de Dados Abertos da CVM",
            attribution="Fonte: CVM — Dados Abertos",
            max_age=timedelta(days=7),
            rate_limit_seconds=1.0,
        ),
        SourceSpec(
            source_id="cvm_inf_diario",
            publisher="CVM",
            title="Informe Diário de Fundos de Investimento",
            base_url="https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/",
            data_nature="real",
            licence="Open Database License (ODbL) — Portal de Dados Abertos da CVM",
            attribution="Fonte: CVM — Dados Abertos",
            max_age=timedelta(days=7),
            rate_limit_seconds=1.0,
        ),
        SourceSpec(
            source_id="bcb_ifdata_cadastro",
            publisher="Banco Central do Brasil",
            title="IF.data — cadastro de instituições (Olinda)",
            base_url="https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/",
            data_nature="real",
            licence="Dados abertos do Banco Central do Brasil",
            attribution="Fonte: Banco Central do Brasil — IF.data",
            max_age=timedelta(days=200),
            rate_limit_seconds=1.0,
        ),
        SourceSpec(
            source_id="bcb_ifdata_valores",
            publisher="Banco Central do Brasil",
            title="IF.data — valores por relatório (Olinda)",
            base_url="https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/",
            data_nature="real",
            licence="Dados abertos do Banco Central do Brasil",
            attribution="Fonte: Banco Central do Brasil — IF.data",
            max_age=timedelta(days=200),
            rate_limit_seconds=1.0,
        ),
        SourceSpec(
            source_id="bcb_sgs",
            publisher="Banco Central do Brasil",
            title="SGS — Sistema Gerenciador de Séries Temporais",
            base_url="https://api.bcb.gov.br/dados/serie/",
            data_nature="real",
            licence="Dados abertos do Banco Central do Brasil",
            attribution="Fonte: Banco Central do Brasil — SGS",
            max_age=timedelta(days=3),
            rate_limit_seconds=1.0,
        ),
        *(
            SourceSpec(
                source_id=source_id,
                publisher="CVM",
                title=title,
                base_url=url,
                data_nature="real",
                licence="Open Database License (ODbL) — Portal de Dados Abertos da CVM",
                attribution="Fonte: CVM — Dados Abertos",
                max_age=timedelta(days=max_age_days),
                rate_limit_seconds=1.0,
            )
            for source_id, title, url, max_age_days in (
                (
                    "cvm_cad_intermed",
                    "Cadastro de Intermediários",
                    "https://dados.cvm.gov.br/dados/INTERMED/CAD/DADOS/cad_intermed.zip",
                    7,
                ),
                (
                    "cvm_cad_fi_hist",
                    "Cadastro de Fundos — histórico (pré-RCVM 175)",
                    "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi_hist.zip",
                    30,
                ),
                (
                    "cvm_cda",
                    "Composição e Diversificação das Aplicações (CDA)",
                    "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/",
                    30,
                ),
                (
                    "cvm_perfil_mensal",
                    "Perfil Mensal de Fundos",
                    "https://dados.cvm.gov.br/dados/FI/DOC/PERFIL_MENSAL/DADOS/",
                    30,
                ),
                (
                    "cvm_lamina",
                    "Lâmina de Informações Essenciais",
                    "https://dados.cvm.gov.br/dados/FI/DOC/LAMINA/DADOS/",
                    30,
                ),
            )
        ),
        SourceSpec(
            source_id="osm_nominatim",
            publisher="OpenStreetMap Foundation",
            title="Nominatim geocoding",
            base_url="https://nominatim.openstreetmap.org/search",
            data_nature="real",
            licence="ODbL 1.0 — dados © colaboradores do OpenStreetMap",
            attribution="© OpenStreetMap contributors",
            max_age=timedelta(days=365),
            # Nominatim usage policy: absolute maximum of 1 request per second.
            rate_limit_seconds=1.1,
        ),
        SourceSpec(
            source_id="anbima_sandbox",
            publisher="ANBIMA",
            title="ANBIMA Feed — sandbox",
            base_url="https://api-sandbox.anbima.com.br/",
            data_nature="sandbox",
            licence="Ambiente de testes; dados fictícios",
            attribution="ANBIMA sandbox (não usar como dado real)",
            max_age=timedelta(days=0),
            rate_limit_seconds=1.0,
        ),
    )
}


def get_source(source_id: str) -> SourceSpec:
    try:
        return SOURCES[source_id]
    except KeyError as error:
        raise KeyError(f"unknown source: {source_id}") from error


def require_real_source(source_id: str) -> SourceSpec:
    spec = get_source(source_id)
    if spec.data_nature != "real":
        raise SandboxDataError(
            f"{source_id} is {spec.data_nature} data and cannot feed real observations"
        )
    return spec
