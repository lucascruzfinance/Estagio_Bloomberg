"""Response contracts (distinct from the SQLAlchemy persistence models).

Conventions documented once and repeated in field descriptions:
- money in BRL (reais), plain numbers, no scaling;
- returns, ratios and coverages are decimal fractions (0.05 = 5%);
- scores are 0-100; `point` is null when no evidence exists for that output;
- dates are ISO 8601 (YYYY-MM-DD), timestamps ISO 8601 with timezone;
- `null` always means "not observed", never zero.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

UNIT_KEY_PATTERN = r"^org-[a-z0-9-]+(:[a-z0-9-]+)?$"
ACCOUNT_ID_PATTERN = r"^org-[a-z0-9-]+$"
CNPJ_PATTERN = r"^\d{14}$"


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Problem(ApiModel):
    type: str = Field(description="URI que identifica o tipo do problema.")
    title: str
    status: int
    detail: str | None = None
    instance: str | None = Field(None, description="Caminho da requisição (sem query string).")
    request_id: str | None = Field(
        None, description="Correlation id também enviado em X-Request-ID."
    )
    errors: list[dict[str, Any]] | None = Field(
        None, description="Erros de validação (sem ecoar a entrada)."
    )


class PageMeta(ApiModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    total: int = Field(ge=0, description="Total de itens que atendem aos filtros.")
    sort: str | None = None
    order: Literal["asc", "desc"] | None = None


class Page(ApiModel, Generic[T]):
    data: list[T]
    meta: PageMeta


class ScoreBand(ApiModel):
    point: float | None = Field(
        None, description="Pontuação 0-100 só com fatores observados; null se não há evidência."
    )
    lower: float = Field(description="Mínimo 0-100 se todo fator ausente valesse 0.")
    upper: float = Field(description="Máximo 0-100 se todo fator ausente valesse 1.")
    coverage: float | None = Field(None, description="Fração 0-1 do peso com evidência.")


class SourceRef(ApiModel):
    source_type: str = Field(description="Identificador da fonte (ex.: cvm_cad_adm_cart).")
    url: str | None = None
    collected_at: datetime
    as_of_date: date | None = Field(None, description="Data de referência dos dados na fonte.")
    sha256: str | None = Field(None, description="Hash do arquivo bruto imutável no cache.")


class Location(ApiModel):
    address: str
    city: str | None = None
    state: str | None = None
    latitude: float | None = Field(
        None, description="WGS84 (EPSG:4326); null se não geocodificado."
    )
    longitude: float | None = None
    precision: str | None = Field(
        None, description="address | street | neighbourhood | city | unknown | none."
    )
    is_exact: bool = Field(description="True somente quando o número da porta foi conferido.")


class AccountSummary(ApiModel):
    account_id: str
    canonical_name: str
    legal_name: str | None = Field(None, description="Razão social da entidade principal (CVM).")
    cnpj: str | None = Field(None, description="CNPJ da entidade principal, 14 dígitos.")
    institution_type: str
    analysis_unit: str = Field(description="'organização' ou 'mesa/área' (bancos).")
    strategy_profile: str
    headquarters: Location | None = None
    best_unit_key: str | None = Field(None, description="Unidade com melhor posição no ranking.")
    best_rank: int | None = None
    tier: str | None = None
    priority: ScoreBand | None = None
    fit: ScoreBand | None = None
    timing: ScoreBand | None = None
    confidence: float | None = Field(
        None, description="Confiança dos dados 0-100 (não altera fit/timing)."
    )
    units_scored: int = 0
    nav_brl_non_fic: float | None = Field(
        None, description="PL somado das classes não-FIC, em BRL."
    )
    net_flow_12m_brl: float | None = Field(
        None, description="Captação líquida 12m em BRL (classes não-FIC, série completa)."
    )
    open_conflicts: int = 0


class LegalEntityOut(ApiModel):
    cnpj: str
    relation: str = Field(description="primary_manager | affiliate_manager | bank_entity.")
    approval_status: str
    relation_evidence: str
    legal_name: str
    trade_name: str | None = None
    cvm_status: str
    cvm_registration_date: date | None = None
    address_official: str | None = None
    phone_official: str | None = Field(
        None, description="Telefone institucional E.164 do cadastro CVM."
    )
    email_institutional: str | None = Field(
        None, description="Somente caixas institucionais; e-mails pessoais são suprimidos."
    )
    website_official: str | None = None
    business_unit_key: str | None = None
    source: SourceRef


class OfficeOut(ApiModel):
    office_key: str
    office_kind: str = Field(
        description="regulatory (endereço CVM) | workbook (planilha, não confirmado)."
    )
    legal_entity_cnpj: str | None = None
    location: Location
    geocode_status: str | None = None
    confidence: str


class PersonOut(ApiModel):
    full_name: str
    role_title: str | None = None
    basis: str = Field(description="Base da coleta (registro regulatório público).")
    as_of_date: date | None = None


class ProductOut(ApiModel):
    product_code: str
    product_name: str
    workflow: str
    rationale: str
    basis: str = Field(description="evidence_rule (dados observados) e/ou desk_config (premissa).")
    fit_status: str = Field(
        description="Sempre 'candidate': hipótese de workflow, não intenção de compra."
    )


class ScoreRow(ApiModel):
    rank: int
    unit_key: str
    unit_name: str
    account_id: str
    canonical_name: str
    institution_type: str
    analysis_unit: str
    evidence_mode: str = Field(description="observed | assumption (mesa pontuada por premissa).")
    tier: str
    priority: ScoreBand
    fit: ScoreBand
    fit_assumption_share: float = Field(description="Fração 0-1 do fit apoiada em premissas.")
    timing: ScoreBand
    confidence: float
    top_positive: list[str]
    top_negative: list[str]
    missing_factors: list[str]


class BusinessUnitOut(ApiModel):
    unit_key: str
    account_id: str
    name: str
    mapping_status: str = Field(description="source_stated | verified | pending.")
    score: ScoreRow | None = None


class FactorOut(ApiModel):
    key: str
    group: str = Field(description="fit | timing.")
    label: str
    weight: float | None = Field(None, description="Peso 0-1 dentro do grupo.")
    value: float | None = Field(None, description="Valor normalizado 0-1; null = sem evidência.")
    status: str = Field(description="observed | proxy | assumption | missing.")
    contribution_points: float | None = Field(
        None, description="Pontos 0-100 com que o fator contribui."
    )
    explanation: str
    evidence: list[str]
    raw: dict[str, Any]


class ReasonOut(ApiModel):
    code: str
    polarity: str = Field(description="'+' favorável, '-' desfavorável, '?' ausente, '~' premissa.")
    group: str
    factor: str
    text: str
    points: float | None = None


class ScoreExplanation(ApiModel):
    score: ScoreRow
    model_version: str
    as_of_date: date
    factors: list[FactorOut]
    reasons: list[ReasonOut]
    confidence_components: dict[str, float]
    products: list[ProductOut]
    limitations: list[str]
    sanity_checks: list[dict[str, Any]]


class FundMetricsOut(ApiModel):
    reference_date: date
    currency: Literal["BRL"] = "BRL"
    latest_nav_brl: float | None = None
    latest_investors: int | None = None
    return_1m: float | None = Field(
        None, description="Variação da cota (fração). Retorno do fundo, não lucro da gestora."
    )
    return_1m_status: str | None = None
    return_3m: float | None = None
    return_3m_status: str | None = None
    return_6m: float | None = None
    return_6m_status: str | None = None
    return_12m: float | None = None
    return_12m_status: str | None = None
    return_ytd: float | None = None
    return_ytd_status: str | None = None
    net_flow_12m_brl: float | None = None
    net_flow_status: str
    volatility_12m: float | None = Field(
        None, description="Desvio-padrão anualizado dos log-retornos diários."
    )
    max_drawdown_12m: float | None = Field(
        None, description="Maior queda pico-vale em 12m (fração negativa)."
    )


class FundRow(ApiModel):
    class_cnpj: str
    subclass_id: str = Field(description="'' para o nível da classe.")
    fund_cnpj: str | None = None
    name: str
    fund_name: str | None = None
    account_id: str
    manager_cnpj: str | None = None
    unit_key: str | None = None
    class_type: str | None = None
    classification: str | None = None
    anbima_classification: str | None = None
    benchmark: str | None = None
    is_active: bool
    is_exclusive: bool
    is_fund_of_funds: bool
    allows_full_offshore: bool | None = None
    constitution_date: date | None = None
    metrics: FundMetricsOut | None = None


class PerformancePoint(ApiModel):
    date: date
    quota: float | None = None
    quota_index: float | None = Field(
        None, description="Cota rebaseada para 100 no início do período."
    )
    nav_brl: float | None = None
    net_flow_brl: float | None = Field(None, description="Captação menos resgates do dia, em BRL.")
    investors: int | None = None


class FundPerformance(ApiModel):
    class_cnpj: str
    subclass_id: str
    name: str
    account_id: str
    currency: Literal["BRL"] = "BRL"
    start: date | None = None
    end: date | None = None
    points: list[PerformancePoint]
    metrics: FundMetricsOut | None = None
    sources: list[str] = Field(description="URLs dos arquivos mensais da CVM usados.")
    note: str


class SignalOut(ApiModel):
    account_id: str
    unit_key: str | None = None
    signal_type: str
    label: str | None = None
    observed_at: datetime
    expires_at: datetime | None = None
    value: float | None = Field(None, description="Intensidade normalizada 0-1.")
    status: str | None = None
    explanation: str | None = None
    evidence: list[str]
    source: SourceRef


class GeoPoint(ApiModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float] = Field(description="[longitude, latitude] WGS84.")


class OfficeFeatureProperties(ApiModel):
    office_key: str
    account_id: str
    canonical_name: str
    institution_type: str
    legal_name: str | None = None
    entity_cnpj: str | None = None
    relation: str | None = None
    address: str
    city: str | None = None
    state: str | None = None
    phone_official: str | None = None
    precision: str | None = None
    is_exact: bool
    tier: str | None = None
    priority_point: float | None = None
    fit_point: float | None = None
    timing_point: float | None = None
    confidence: float | None = None
    nav_brl_non_fic: float | None = None
    net_flow_12m_brl: float | None = None


class OfficeFeature(ApiModel):
    type: Literal["Feature"] = "Feature"
    geometry: GeoPoint
    properties: OfficeFeatureProperties


class MapMeta(ApiModel):
    count: int
    without_location: int = Field(
        description="Escritórios filtrados sem coordenada (não plotados)."
    )
    attribution: str
    precision_note: str


class OfficeFeatureCollection(ApiModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[OfficeFeature]
    meta: MapMeta


class DensityCell(ApiModel):
    longitude: float
    latitude: float
    offices: int
    accounts: list[str]


class DensityGrid(ApiModel):
    cell_m: int = Field(description="Lado da célula em metros (Web Mercator).")
    cells: list[DensityCell]
    attribution: str
    note: str


class ComparisonFactor(ApiModel):
    key: str
    group: str
    label: str
    values: dict[str, dict[str, Any]] = Field(description="Por unit_key: value, status, points.")


class Comparison(ApiModel):
    units: list[ScoreRow]
    factors: list[ComparisonFactor]
    warnings: list[str]


class FreshnessOut(ApiModel):
    source_id: str
    title: str
    status: str = Field(description="fresh | stale | unavailable | not_used.")
    data_as_of: date | None = None
    fetched_at: datetime | None = None
    age_days: int | None = None
    max_age_days: int
    detail: str | None = None


class AccountQuality(ApiModel):
    account_id: str
    canonical_name: str
    entities_found: int
    entities_registered: int
    official_address: bool
    geocode_precision: str | None = None
    active_classes: int
    classes_with_daily_report: int
    comparable_12m_share: float | None = None
    open_conflicts: int
    gaps: list[str]


class DataQuality(ApiModel):
    report_version: str
    run_at: datetime
    fund_reference_date: date | None = None
    freshness: list[FreshnessOut]
    accounts: list[AccountQuality]
    rules: list[str]
    conflicts_by_status: dict[str, int]
    database: dict[str, Any]


class ConflictOut(ApiModel):
    conflict_id: str
    account_id: str
    entity_cnpj: str
    field: str
    rule: str
    severity: str
    workbook_value: str
    source_value: str
    detected_at: datetime
    resolution_status: str
    resolution_note: str | None = None


class SearchHit(ApiModel):
    account_id: str
    canonical_name: str
    institution_type: str
    matched: str = Field(description="Texto que casou (alias, razão social ou CNPJ).")
    match_kind: Literal["cnpj", "exact", "prefix", "contains"]
    alias_kind: str | None = None


class AccountDetail(AccountSummary):
    website_url: str | None = None
    phone_public_workbook: str | None = Field(
        None, description="Telefone da planilha de networking (não verificado)."
    )
    legal_entities: list[LegalEntityOut]
    offices: list[OfficeOut]
    people: list[PersonOut]
    business_units: list[BusinessUnitOut]
    scores: list[ScoreRow]
    products: list[ProductOut]
    signals: list[SignalOut]
    quality: AccountQuality | None = None


class Meta(ApiModel):
    api_version: str
    data_mode: Literal["live", "demo"] = Field(
        description="demo = base congelada do repositório, sem atualização ao vivo."
    )
    data_note: str
    model_version: str | None = None
    score_as_of_date: date | None = None
    score_run_loaded_at: datetime | None = None
    fund_reference_date: date | None = None
    disclaimer: str
    limitations: list[str]
    conventions: dict[str, str]
    attributions: list[str]


class Health(ApiModel):
    status: Literal["ok"]


class Readiness(ApiModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, Any]


# --- Territory universe (Prompt 8) ---


class UniverseRow(ApiModel):
    cnpj: str = Field(pattern=CNPJ_PATTERN)
    legal_name: str
    trade_name: str | None = None
    group_key: str
    group_name: str
    kinds: list[str]
    primary_kind: str
    side: Literal["buy_side", "sell_side"]
    coverage_tier: Literal["curated", "radar", "universe"]
    curated_account_key: str | None = None
    centre: str | None = None
    city: str | None = None
    state: str | None = None
    registration_date: date | None = None
    active_classes: int
    selected_classes: int
    nav_brl: float | None = Field(None, description="PL não FIC no último Informe Diário (R$).")
    nav_month: date | None = None
    net_flow_12m_brl: float | None = Field(None, description="Captação líquida 12m, não FIC (R$).")
    funds_administered: int
    nav_administered_brl: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    geocode_precision: str
    building_key: str | None = None


class UniverseMonth(ApiModel):
    month: date
    nav_brl: float | None = None
    inflow_brl: float | None = None
    outflow_brl: float | None = None
    net_flow_brl: float | None = None
    investors: int | None = None
    classes_reporting: int


class UniverseFund(ApiModel):
    class_cnpj: str
    class_name: str
    classification: str | None = None
    anbima_classification: str | None = None
    nav_brl: float | None = None
    return_12m: float | None = Field(None, description="Variação da cota em 12 meses (mensal).")
    net_flow_12m_brl: float | None = None
    is_selected: bool


class UniverseDetail(UniverseRow):
    phone_official: str | None = None
    website_official: str | None = None
    street: str | None = None
    complement: str | None = None
    district: str | None = None
    group_members: int
    monthly: list[UniverseMonth]
    top_funds: list[UniverseFund]
    source: dict[str, Any]


class UniverseSummary(ApiModel):
    as_of: dict[str, Any]
    totals: dict[str, int]
    by_centre: list[dict[str, Any]]
    by_kind: list[dict[str, Any]]
    radar_recent: list[UniverseRow]
