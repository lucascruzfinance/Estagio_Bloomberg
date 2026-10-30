"""Factor computation and transparent aggregation.

Missing data never counts as a healthy zero. Each group score is reported as
  - ``point``: weighted mean over the factors that have evidence;
  - ``lower``/``upper``: the range spanned if every missing factor were 0 or 1;
  - ``coverage``: share of the group weight that has evidence.
Confidence is computed separately and never feeds fit, timing or priority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from networking_intel.scoring.config import FIT_FACTORS, ScoringConfig
from networking_intel.scoring.features import UnitFeatures

Status = Literal["observed", "proxy", "assumption", "missing"]
Group = Literal["fit", "timing"]


@dataclass(frozen=True)
class FactorResult:
    key: str
    group: Group
    label: str
    value: float | None
    status: Status
    raw: dict[str, Any]
    evidence: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class GroupScore:
    point: float | None
    lower: float
    upper: float
    coverage: float
    assumption_share: float
    contributions: dict[str, float | None]


@dataclass(frozen=True)
class ReasonCode:
    code: str
    polarity: Literal["+", "-", "?", "~"]
    group: str
    factor: str
    text: str
    points: float | None


@dataclass
class UnitScore:
    unit_key: str
    account_id: str
    unit_name: str
    analysis_unit: str
    evidence_mode: str
    model_version: str
    as_of_date: str
    fit: GroupScore
    timing: GroupScore
    priority_point: float | None
    priority_lower: float
    priority_upper: float
    confidence: float
    confidence_components: dict[str, float]
    tier: str
    factors: list[FactorResult]
    reasons: list[ReasonCode] = field(default_factory=list)
    products: list[dict[str, str]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _pct(value: float) -> str:
    """Brazilian percent: 28,6% / -15,7% (explanations are read by the sales team)."""
    text = f"{value:+.1%}" if value < 0 else f"{value:.1%}"
    return text.replace(".", ",")


def _dec(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _brl_bn(value: float) -> str:
    return f"R$ {value / 1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")


CVM_FUNDS = "CVM — Registro de Fundos/Classes"
CVM_DAILY = "CVM — Informe Diário"
CVM_MANAGERS = "CVM — Cadastro de Administradores de Carteira"


def _factor(
    config: ScoringConfig,
    group: Group,
    key: str,
    raw_value: float | None,
    status: Status,
    raw: dict[str, Any],
    evidence: tuple[str, ...],
    explanation: str,
    scale_key: str | None = None,
) -> FactorResult:
    spec = (config.fit if group == "fit" else config.timing)[key]
    if raw_value is None:
        value, status = None, "missing"
    elif status == "assumption":
        value = raw_value
    else:
        value = config.scales[scale_key or key].transform(raw_value)
    return FactorResult(key, group, spec.label, value, status, raw, evidence, explanation)


def _assumed(config: ScoringConfig, unit: UnitFeatures, key: str) -> FactorResult:
    prior = unit.priors[key]
    return _factor(
        config,
        "fit",
        key,
        prior,
        "assumption",
        {"prior": prior},
        ("config/scoring/opportunity_v1.yaml — premissa especialista",),
        f"Premissa editável para a mesa ({_dec(prior)}); sem evidência pública coletada.",
    )


def fit_factors(config: ScoringConfig, unit: UnitFeatures) -> list[FactorResult]:
    if unit.evidence_mode == "assumption":
        return [_assumed(config, unit, key) for key in FIT_FACTORS]
    has_classes = unit.active_classes > 0
    families = ", ".join(f"{k}: {v}" for k, v in sorted(unit.families.items()))
    evidence = (
        f"{CVM_FUNDS}; {unit.strategy_classes} estratégias próprias ({unit.strategy_basis}) "
        f"de {unit.active_classes} classes ativas ({families})",
    )
    results = [
        _factor(
            config,
            "fit",
            "workflow_complexity",
            unit.data_intensity if has_classes else None,
            "observed",
            {"data_intensity": unit.data_intensity, "basis": unit.strategy_basis},
            evidence,
            f"Intensidade média de dados {_dec(unit.data_intensity or 0)} em "
            f"{unit.strategy_classes} estratégias próprias ({unit.strategy_basis}).",
        ),
        _factor(
            config,
            "fit",
            "asset_breadth",
            float(len(unit.families)) if has_classes else None,
            "observed",
            {"families": unit.families},
            evidence,
            f"{len(unit.families)} famílias de estratégia: {families or '—'}.",
        ),
        _factor(
            config,
            "fit",
            "international",
            unit.offshore_share if has_classes else None,
            "observed",
            {"offshore_share": unit.offshore_share},
            evidence,
            f"{_pct(unit.offshore_share or 0)} das estratégias próprias com mandato 100% "
            "exterior ou classificação exterior.",
        ),
        _factor(
            config,
            "fit",
            "data_api_need",
            float(unit.daily_share_classes) if unit.daily_share_classes else None,
            "proxy",
            {"daily_share_classes": unit.daily_share_classes},
            (f"{CVM_DAILY}; séries com cota diária atualizada",),
            f"{unit.daily_share_classes or 0} classes/subclasses não-FIC com cota diária "
            "(proxy de volume de dados operacionais).",
        ),
        _factor(
            config,
            "fit",
            "user_potential",
            unit.nav_non_fic if unit.nav_non_fic else None,
            "proxy",
            {"nav_non_fic_brl": unit.nav_non_fic},
            (f"{CVM_DAILY}; PL das classes não-FIC",),
            f"PL não-FIC de {_brl_bn(unit.nav_non_fic or 0)} como proxy de equipe "
            "(headcount não coletado).",
        ),
    ]
    return results


def _manual_factor(config: ScoringConfig, unit: UnitFeatures, key: str) -> FactorResult:
    signals = unit.manual_signals.get(key, [])
    if not signals:
        return _factor(
            config,
            "timing",
            key,
            None,
            "missing",
            {},
            (),
            "Sem sinal curado com fonte; ausência de registro não é evidência de ausência.",
        )
    strength = float(sum(s.strength for s in signals))
    evidence = tuple(
        f"{s.source_publisher} ({s.observed_at.isoformat()}): {s.source_url}" for s in signals
    )
    text = "; ".join(s.description for s in signals)
    return _factor(
        config,
        "timing",
        key,
        strength,
        "observed",
        {"signals": [s.signal_id for s in signals], "strength": strength},
        evidence,
        text,
        scale_key="manual_signal",
    )


def timing_factors(config: ScoringConfig, unit: UnitFeatures) -> list[FactorResult]:
    rules = config.evidence_rules
    observed = unit.evidence_mode == "observed"
    flows_ok = (
        unit.net_flow_coverage is not None
        and unit.net_flow_coverage >= rules.min_net_flow_nav_coverage
        and unit.net_flow_ratio is not None
    )
    perf_ok = (
        unit.performance_coverage is not None
        and unit.performance_coverage >= rules.min_performance_nav_coverage
        and unit.performance_excess is not None
    )
    launches = unit.launches if observed and unit.active_classes else None
    examples = "; ".join(unit.launch_examples[:3])
    return [
        _factor(
            config,
            "timing",
            "product_launches",
            float(launches) if launches is not None else None,
            "observed",
            {"launches": launches, "exclusive": unit.launches_exclusive},
            (f"{CVM_FUNDS}; data de constituição dos fundos",),
            (
                f"{launches} fundos abertos constituídos em 12 meses (mais "
                f"{unit.launches_exclusive or 0} exclusivos, não pontuados). Ex.: {examples or '—'}."
                if launches is not None
                else "Sem fundos mapeados a esta unidade; lançamentos não observáveis."
            ),
        ),
        _factor(
            config,
            "timing",
            "net_flows",
            unit.net_flow_ratio if flows_ok else None,
            "observed",
            {
                "ratio": unit.net_flow_ratio,
                "net_flow_brl": unit.net_flow_brl,
                "nav_coverage": unit.net_flow_coverage,
            },
            (f"{CVM_DAILY}; CAPTC_DIA - RESG_DIA em 12 meses",),
            (
                f"Captação líquida de {_brl_bn(unit.net_flow_brl or 0)} "
                f"({_pct(unit.net_flow_ratio or 0)} do PL inicial; cobertura "
                f"{_pct(unit.net_flow_coverage or 0)} do PL)."
                if flows_ok
                else "Cobertura de séries completas insuficiente para medir fluxos."
            ),
        ),
        _factor(
            config,
            "timing",
            "expansion",
            float(unit.new_entities) if observed and unit.new_entities is not None else None,
            "observed",
            {"new_entities": unit.new_entity_names},
            (f"{CVM_MANAGERS}; data de registro das entidades",),
            (
                f"{unit.new_entities} nova(s) entidade(s) CVM em 24 meses: "
                f"{', '.join(unit.new_entity_names)}."
                if unit.new_entities
                else "Nenhuma nova entidade regulada pela CVM em 24 meses."
            ),
        ),
        _manual_factor(config, unit, "hiring"),
        _manual_factor(config, unit, "m_and_a"),
        _manual_factor(config, unit, "operational_change"),
        _factor(
            config,
            "timing",
            "performance",
            unit.performance_excess if perf_ok else None,
            "observed",
            {"excess_12m": unit.performance_excess, "nav_coverage": unit.performance_coverage},
            (f"{CVM_DAILY}; retorno 12m vs mediana da mesma classificação CVM",),
            (
                f"Excesso de retorno 12m ponderado por PL de {_pct(unit.performance_excess or 0)} "
                "vs pares (peso limitado; retorno do fundo, não lucro da gestora)."
                if perf_ok
                else "Retornos comparáveis cobrem pouco do PL; performance não avaliada."
            ),
        ),
    ]


def aggregate(factors: list[FactorResult], weights: dict[str, float]) -> GroupScore:
    total = sum(weights.values())
    if not total:
        return GroupScore(None, 0.0, 100.0, 0.0, 0.0, {})
    available = [f for f in factors if f.value is not None]
    have = sum(weights[f.key] for f in available)
    weighted = sum(weights[f.key] * (f.value or 0.0) for f in available)
    missing = total - have
    point = 100 * weighted / have if have else None
    contributions: dict[str, float | None] = {
        f.key: (
            100 * weights[f.key] * (f.value or 0.0) / have if have and f.value is not None else None
        )
        for f in factors
    }
    assumed = sum(weights[f.key] for f in available if f.status == "assumption")
    return GroupScore(
        point=point,
        lower=100 * weighted / total,
        upper=100 * (weighted + missing) / total,
        coverage=have / total,
        assumption_share=assumed / total,
        contributions=contributions,
    )


def reasons_for(
    config: ScoringConfig, factors: list[FactorResult], group: GroupScore
) -> list[ReasonCode]:
    thresholds = config.reason_thresholds
    reasons: list[ReasonCode] = []
    for factor in factors:
        prefix = f"{factor.group.upper()}_{factor.key.upper()}"
        points = group.contributions.get(factor.key)
        if factor.value is None:
            reasons.append(
                ReasonCode(
                    f"{prefix}_MISSING",
                    "?",
                    factor.group,
                    factor.key,
                    f"{factor.label}: {factor.explanation}",
                    None,
                )
            )
        elif factor.status == "assumption":
            reasons.append(
                ReasonCode(
                    f"{prefix}_ASSUMED",
                    "~",
                    factor.group,
                    factor.key,
                    f"{factor.label}: {factor.explanation}",
                    points,
                )
            )
        elif factor.value >= thresholds.positive:
            reasons.append(
                ReasonCode(
                    f"{prefix}_HIGH",
                    "+",
                    factor.group,
                    factor.key,
                    f"{factor.label}: {factor.explanation}",
                    points,
                )
            )
        elif factor.value <= thresholds.negative:
            reasons.append(
                ReasonCode(
                    f"{prefix}_LOW",
                    "-",
                    factor.group,
                    factor.key,
                    f"{factor.label}: {factor.explanation}",
                    points,
                )
            )
    return reasons


def confidence_for(
    config: ScoringConfig, unit: UnitFeatures, fit: GroupScore, timing: GroupScore
) -> tuple[float, dict[str, float]]:
    cfg = config.confidence
    evidence = (
        (fit.coverage - fit.assumption_share) + (timing.coverage - timing.assumption_share)
    ) / 2
    identity = 1.0 if unit.identity_found_active else 0.5 if unit.identity_found else 0.0
    if unit.identity_pending:
        identity *= cfg.pending_identity_factor
    if unit.evidence_mode == "assumption":
        identity *= 0.5  # desk itself not identified in any public registry
    components = {
        "evidence_coverage": evidence,
        "identity": identity,
        "freshness": unit.freshness_share,
        "conflicts": 1.0 - min(1.0, unit.open_conflicts / cfg.conflicts_for_zero),
        "comparability": unit.comparable_share or 0.0,
    }
    weights = cfg.component_weights()
    return 100 * sum(weights[k] * v for k, v in components.items()), components


def tier_for(config: ScoringConfig, fit: GroupScore, timing: GroupScore) -> str:
    tiers = config.tiers
    if fit.point is None or fit.coverage < tiers.min_fit_coverage:
        return "Evidência insuficiente"
    fit_high = fit.point >= tiers.fit_high
    if timing.point is None or timing.coverage < tiers.min_timing_coverage:
        return "Fit alto — timing desconhecido" if fit_high else "Fit baixo — timing desconhecido"
    timing_high = timing.point >= tiers.timing_high
    if fit_high and timing_high:
        return "Prioridade agora"
    if fit_high:
        return "Desenvolver relacionamento"
    if timing_high:
        return "Oportunidade tática"
    return "Monitorar"


def combine(
    config: ScoringConfig, fit: GroupScore, timing: GroupScore
) -> tuple[float | None, float, float]:
    wf, wt = config.priority_index["fit"], config.priority_index["timing"]
    point = (
        wf * fit.point + wt * timing.point
        if fit.point is not None
        and timing.point is not None
        and timing.coverage >= config.tiers.min_timing_coverage
        else None
    )
    return point, wf * fit.lower + wt * timing.lower, wf * fit.upper + wt * timing.upper


def score_unit(
    config: ScoringConfig,
    unit: UnitFeatures,
    factors: tuple[list[FactorResult], list[FactorResult]] | None = None,
) -> UnitScore:
    fit_list, timing_list = factors or (fit_factors(config, unit), timing_factors(config, unit))
    fit = aggregate(fit_list, config.weights("fit"))
    timing = aggregate(timing_list, config.weights("timing"))
    priority, lower, upper = combine(config, fit, timing)
    confidence, components = confidence_for(config, unit, fit, timing)
    return UnitScore(
        unit_key=unit.unit_key,
        account_id=unit.account_id,
        unit_name=unit.unit_name,
        analysis_unit=unit.analysis_unit,
        evidence_mode=unit.evidence_mode,
        model_version=config.model_version,
        as_of_date=unit.reference_date.isoformat(),
        fit=fit,
        timing=timing,
        priority_point=priority,
        priority_lower=lower,
        priority_upper=upper,
        confidence=confidence,
        confidence_components=components,
        tier=tier_for(config, fit, timing),
        factors=[*fit_list, *timing_list],
        reasons=reasons_for(config, fit_list, fit) + reasons_for(config, timing_list, timing),
    )


def rank_key(score: UnitScore) -> tuple[int, float, float, str]:
    """Units with a priority point first (desc), then fit-only units by fit (desc)."""
    has_point = score.priority_point is not None
    primary = score.priority_point if has_point else (score.fit.point or 0.0)
    return (0 if has_point else 1, -(primary or 0.0), -(score.fit.point or 0.0), score.unit_key)
