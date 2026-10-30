from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from networking_intel.scoring.config import ScoringConfig, load_config
from networking_intel.scoring.features import build_units, load_inputs
from networking_intel.scoring.model import (
    UnitScore,
    fit_factors,
    rank_key,
    score_unit,
    timing_factors,
)
from networking_intel.scoring.products import product_candidates
from networking_intel.scoring.report import render_report
from networking_intel.scoring.sanity import check_expectations
from networking_intel.scoring.sensitivity import UnitFactors, run_sensitivity

LIMITATIONS = (
    "Não é probabilidade de compra: não existe variável-alvo histórica de oportunidades ou "
    "conversões; pesos são premissas especialistas editáveis e versionadas.",
    "Fit usa proxies regulatórios (classes, estratégias, PL); headcount, sistemas atuais e "
    "contratos vigentes com Bloomberg ou concorrentes não foram observados.",
    "30% do peso de timing (contratações, M&A, mudanças operacionais) depende de sinais "
    "curados com fonte em data/reference/commercial_signals.csv, hoje vazio; o intervalo "
    "[mín, máx] mostra o efeito dessa lacuna.",
    "Mesas de bancos sem entidade CVM própria são pontuadas por premissa (marcadas '~'); "
    "servem para estruturar a conversa por área, não para comparar com gestoras observadas.",
    "Performance é retorno de fundos para o cotista, relativo aos pares da mesma "
    "classificação CVM dentro do piloto, com peso máximo de 10%; não é lucro da gestora.",
    "A CVM só enxerga veículos domiciliados no Brasil: fundos offshore (ex.: veículos "
    "globais de gestoras macro) não entram em amplitude, atuação internacional nem escala, o "
    "que subestima o fit de gestoras com operação global relevante fora do país.",
    "Em plataformas de wealth/family office, veículos de famílias não exclusivos ainda contam "
    "como estratégias; ali o fit mede escala da plataforma, não sofisticação de gestão.",
    "Ranking é um apoio à preparação de contas; a decisão de abordagem é do vendedor.",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _round(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def _flat_row(rank: int, score: UnitScore) -> dict[str, Any]:
    positives = [r.text for r in score.reasons if r.polarity == "+"]
    negatives = [r.text for r in score.reasons if r.polarity == "-"]
    missing = [r.factor for r in score.reasons if r.polarity == "?"]
    return {
        "rank": rank,
        "unit_key": score.unit_key,
        "account_id": score.account_id,
        "unit_name": score.unit_name,
        "analysis_unit": score.analysis_unit,
        "evidence_mode": score.evidence_mode,
        "tier": score.tier,
        "priority_point": _round(score.priority_point),
        "priority_lower": _round(score.priority_lower),
        "priority_upper": _round(score.priority_upper),
        "fit_point": _round(score.fit.point),
        "fit_lower": _round(score.fit.lower),
        "fit_upper": _round(score.fit.upper),
        "fit_coverage": _round(score.fit.coverage, 3),
        "fit_assumption_share": _round(score.fit.assumption_share, 3),
        "timing_point": _round(score.timing.point),
        "timing_lower": _round(score.timing.lower),
        "timing_upper": _round(score.timing.upper),
        "timing_coverage": _round(score.timing.coverage, 3),
        "confidence": _round(score.confidence),
        "positive_reasons": " | ".join(positives),
        "negative_reasons": " | ".join(negatives),
        "missing_factors": " | ".join(missing),
        "model_version": score.model_version,
        "as_of_date": score.as_of_date,
    }


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def score_all(root: Path, config: ScoringConfig) -> tuple[list[UnitScore], list[UnitFactors], Any]:
    inputs = load_inputs(root)
    units = build_units(inputs, config)
    scores: list[UnitScore] = []
    factors: list[UnitFactors] = []
    for unit in units:
        fit_list, timing_list = fit_factors(config, unit), timing_factors(config, unit)
        score = score_unit(config, unit, (fit_list, timing_list))
        score.products = product_candidates(config, unit, score)
        scores.append(score)
        factors.append(UnitFactors(unit.unit_key, fit_list, timing_list))
    scores.sort(key=rank_key)
    return scores, factors, inputs


def run_scoring(root: Path, config_path: Path, draws: int = 1000) -> dict[str, Any]:
    config, config_sha = load_config(config_path)
    scores, factors, inputs = score_all(root, config)
    sensitivity, sensitivity_summary = run_sensitivity(config, factors, draws=draws)
    sanity = check_expectations(config, scores)

    out = root / "data/scored"
    rows = [_flat_row(position + 1, score) for position, score in enumerate(scores)]
    _write_csv(out / "unit_scores.csv", rows)
    _write_csv(out / "product_fit.csv", [p for score in scores for p in score.products])
    _write_csv(out / "sensitivity.csv", sensitivity)
    _write_csv(out / "sanity_checks.csv", sanity)
    explanations = {
        "model_version": config.model_version,
        "config_sha256": config_sha,
        "limitations": list(LIMITATIONS),
        "units": [score.as_dict() for score in scores],
    }
    (out / "score_explanations.json").write_text(
        json.dumps(explanations, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    manifest = {
        "model_version": config.model_version,
        "config_path": config_path.as_posix(),
        "config_sha256": config_sha,
        "as_of_date": scores[0].as_of_date if scores else None,
        "inputs_sha256": {
            path.relative_to(root).as_posix(): _sha256(path)
            for path in inputs.paths
            if path.exists()
        },
        "units_scored": len(scores),
        "sensitivity": sensitivity_summary,
        "sanity": {
            s: sum(r["status"] == s for r in sanity) for s in ("pass", "fail", "not_evaluable")
        },
        "outputs_sha256": {
            name: _sha256(out / name)
            for name in ("unit_scores.csv", "product_fit.csv", "score_explanations.json")
        },
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report = render_report(
        config, scores, sensitivity, sensitivity_summary, sanity, manifest, LIMITATIONS
    )
    (root / "docs/opportunity_model_report.md").write_text(report, encoding="utf-8")
    return manifest
