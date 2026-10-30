from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from networking_intel.scoring.config import ScoringConfig
from networking_intel.scoring.model import UnitScore


def _n(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}"


def _range(lower: float, upper: float) -> str:
    return f"{lower:.0f}-{upper:.0f}"


def render_report(
    config: ScoringConfig,
    scores: Sequence[UnitScore],
    sensitivity: Sequence[dict[str, Any]],
    sensitivity_summary: dict[str, float],
    sanity: Sequence[dict[str, Any]],
    manifest: dict[str, Any],
    limitations: Sequence[str],
) -> str:
    sens = {row["unit_key"]: row for row in sensitivity}
    lines = [
        "# Prompt 4 — Modelo explicável de oportunidade comercial",
        "",
        f"Modelo `{config.model_version}` · dados até {manifest['as_of_date']} · "
        f"config SHA-256 `{manifest['config_sha256'][:12]}…`",
        "",
        "> Apoio à preparação de contas. Não é probabilidade de compra nem recomendação "
        "automática de abordagem. Fit, timing e confiança são saídas separadas; a confiança "
        "nunca altera fit ou timing.",
        "",
        "## Ranking do piloto",
        "",
        "Pontos de 0 a 100. `ponto` usa só fatores com evidência; `mín-máx` mostra o "
        "intervalo se cada fator ausente valesse 0 ou 1. `~` = pontuação por premissa.",
        "",
        "| # | Unidade | Faixa | Prioridade (mín-máx) | Fit (mín-máx) | Timing (mín-máx) | "
        "Cobertura timing | Confiança | Rank p05-p95 |",
        "|---:|---|---|---|---|---|---:|---:|---|",
    ]
    for position, score in enumerate(scores, start=1):
        row = sens.get(score.unit_key, {})
        rank_band = (
            f"{row.get('priority_rank_p05')}-{row.get('priority_rank_p95')}"
            if row.get("priority_rank_p05") is not None
            else f"fit {row.get('fit_rank_p05')}-{row.get('fit_rank_p95')}"
        )
        marker = " ~" if score.evidence_mode == "assumption" else ""
        lines.append(
            f"| {position} | {score.unit_name}{marker} | {score.tier} | "
            f"{_n(score.priority_point)} ({_range(score.priority_lower, score.priority_upper)}) | "
            f"{_n(score.fit.point)} ({_range(score.fit.lower, score.fit.upper)}) | "
            f"{_n(score.timing.point)} ({_range(score.timing.lower, score.timing.upper)}) | "
            f"{score.timing.coverage:.0%} | {score.confidence:.0f} | {rank_band} |"
        )
    lines += ["", "## Por que cada unidade está onde está", ""]
    for score in scores:
        lines.append(f"### {score.unit_name}")
        lines.append("")
        lines.append(
            f"Faixa **{score.tier}** · fit {_n(score.fit.point)} · timing {_n(score.timing.point)} "
            f"· confiança {score.confidence:.0f}"
        )
        lines.append("")
        lines.append("| Fator | Valor 0-1 | Pontos | Status | Explicação |")
        lines.append("|---|---:|---:|---|---|")
        for factor in score.factors:
            group_score = score.fit if factor.group == "fit" else score.timing
            points = group_score.contributions.get(factor.key)
            lines.append(
                f"| {factor.group}: {factor.label} | "
                f"{'—' if factor.value is None else f'{factor.value:.2f}'} | "
                f"{'—' if points is None else f'{points:.1f}'} | {factor.status} | "
                f"{factor.explanation} |"
            )
        if score.products:
            names = ", ".join(p["product_name"] for p in score.products)
            lines += ["", f"Workflows/produtos a explorar (hipótese): {names}."]
        lines.append("")
    lines += [
        "## Sensibilidade dos pesos",
        "",
        f"- {int(sensitivity_summary['draws'])} sorteios Dirichlet em torno dos pesos-base "
        f"(concentração 20): Spearman médio {sensitivity_summary['spearman_mean']:.2f}, "
        f"p05 {sensitivity_summary['spearman_p05']:.2f} contra o ranking-base de prioridade.",
        "- Variação de ±50% em cada peso isolado (renormalizado): maior deslocamento de "
        "posição por unidade na coluna `max_rank_shift_oat_50pct` de `data/scored/sensitivity.csv`.",
        "",
        "## Checagens contra rankings absurdos",
        "",
        "Falhas são investigadas e documentadas; pesos não são ajustados para forçar o "
        "resultado esperado.",
        "",
        "| Esperado maior | Esperado menor | Saída | Valores | Status | Racional | Fatores da falha |",
        "|---|---|---|---|---|---|---|",
    ]
    for check in sanity:
        hv, lv = check["higher_value"], check["lower_value"]
        values = f"{hv:.0f} vs {lv:.0f}" if isinstance(hv, float) and isinstance(lv, float) else "—"
        lines.append(
            f"| {check['higher']} | {check['lower']} | {check['output']} | {values} | "
            f"{check['status']} | {check['rationale']} | {check['fail_drivers'] or '—'} |"
        )
    lines += [
        "",
        "## Pesos (editáveis em `config/scoring/opportunity_v1.yaml`)",
        "",
        "| Grupo | Fator | Peso | Definição |",
        "|---|---|---:|---|",
    ]
    for group, specs in (("fit", config.fit), ("timing", config.timing)):
        for spec in specs.values():
            lines.append(f"| {group} | {spec.label} | {spec.weight:.0%} | {spec.description} |")
    lines += [
        "",
        f"Índice de prioridade = {config.priority_index['fit']:.0%} fit + "
        f"{config.priority_index['timing']:.0%} timing, calculado só quando a cobertura de "
        f"timing ≥ {config.tiers.min_timing_coverage:.0%}.",
        "",
        "## Limitações",
        "",
        *[f"- {item}" for item in limitations],
        "",
    ]
    return "\n".join(lines)
