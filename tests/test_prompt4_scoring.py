from __future__ import annotations

import dataclasses
import json
import shutil
from datetime import date, timedelta
from pathlib import Path

import polars as pl
import pytest
import yaml
from pydantic import ValidationError

from networking_intel.scoring.calibration import (
    InsufficientOutcomesError,
    OutcomeRecord,
    require_calibration_data,
)
from networking_intel.scoring.config import ScoringConfig, load_config
from networking_intel.scoring.features import (
    CuratedInputs,
    ManualSignal,
    UnitFeatures,
    build_units,
    load_signals,
    strategy_family,
)
from networking_intel.scoring.model import aggregate, score_unit
from networking_intel.scoring.pipeline import run_scoring

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config/scoring/opportunity_v1.yaml"
CONFIG, _ = load_config(CONFIG_PATH)
REF = date(2026, 10, 27)


def unit(**overrides: object) -> UnitFeatures:
    base = UnitFeatures(
        unit_key="org-test",
        account_id="org-test",
        unit_name="Teste",
        canonical_name="Teste",
        institution_type="gestora independente",
        analysis_unit="organização",
        desk_key=None,
        evidence_mode="observed",
        reference_date=REF,
        active_classes=40,
        strategy_classes=20,
        strategy_basis="abertas não-FIC",
        families={"Multimercado": 10, "Ações": 6, "Renda fixa": 4},
        data_intensity=0.86,
        offshore_share=0.10,
        daily_share_classes=60,
        nav_non_fic=10e9,
        launches=3,
        launches_exclusive=1,
        net_flow_ratio=0.05,
        net_flow_brl=0.5e9,
        net_flow_coverage=0.9,
        new_entities=0,
        performance_excess=0.01,
        performance_coverage=0.8,
        identity_found=True,
        identity_found_active=True,
        identity_pending=True,
        open_conflicts=0,
        comparable_share=0.9,
        freshness_share=1.0,
    )
    return dataclasses.replace(base, **overrides)  # type: ignore[arg-type]


def config_dict() -> dict[str, object]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


# --- configuration -------------------------------------------------------------


def test_config_is_versioned_and_weights_are_valid() -> None:
    assert CONFIG.model_version.startswith("opportunity-v")
    assert sum(CONFIG.weights("fit").values()) == pytest.approx(1.0)
    assert sum(CONFIG.weights("timing").values()) == pytest.approx(1.0)
    assert CONFIG.weights("timing")["performance"] <= 0.10


def test_config_rejects_performance_above_cap_and_bad_sums() -> None:
    data = config_dict()
    timing = data["timing"]
    assert isinstance(timing, dict)
    timing["performance"]["weight"] = 0.20
    timing["product_launches"]["weight"] = 0.15
    with pytest.raises(ValidationError, match="performance weight"):
        ScoringConfig.model_validate(data)
    timing["performance"]["weight"] = 0.10
    with pytest.raises(ValidationError, match="sum to 1"):
        ScoringConfig.model_validate(data)


def test_desk_without_evidence_needs_complete_priors() -> None:
    data = config_dict()
    desks = data["bank_desks"]
    assert isinstance(desks, dict)
    desks["org-itau-bba"][0]["priors"].pop("international")
    with pytest.raises(ValidationError, match="priors for every fit factor"):
        ScoringConfig.model_validate(data)


# --- missingness and extremes ---------------------------------------------------


def test_missing_is_not_a_healthy_zero() -> None:
    complete = score_unit(CONFIG, unit())
    missing = score_unit(CONFIG, unit(net_flow_ratio=None, net_flow_coverage=None))

    flows = next(f for f in missing.factors if f.key == "net_flows")
    assert flows.value is None and flows.status == "missing"
    assert missing.timing.coverage < complete.timing.coverage
    assert missing.timing.lower <= (missing.timing.point or 0) <= missing.timing.upper
    zero_flow = score_unit(CONFIG, unit(net_flow_ratio=-0.20))
    assert missing.timing.point != zero_flow.timing.point
    assert any(r.code == "TIMING_NET_FLOWS_MISSING" for r in missing.reasons)


def test_low_flow_coverage_is_treated_as_missing() -> None:
    score = score_unit(CONFIG, unit(net_flow_coverage=0.2))
    assert next(f for f in score.factors if f.key == "net_flows").value is None


def test_extreme_values_are_clipped() -> None:
    huge = score_unit(CONFIG, unit(nav_non_fic=1e15, launches=10_000, net_flow_ratio=50.0))
    tiny = score_unit(CONFIG, unit(nav_non_fic=1.0, launches=0, net_flow_ratio=-5.0))
    for score in (huge, tiny):
        assert all(f.value is None or 0.0 <= f.value <= 1.0 for f in score.factors)
        assert 0.0 <= (score.fit.point or 0) <= 100.0
    assert next(f for f in huge.factors if f.key == "user_potential").value == 1.0
    assert next(f for f in tiny.factors if f.key == "net_flows").value == 0.0


def test_all_max_beats_all_min_and_contributions_add_up() -> None:
    best = score_unit(
        CONFIG,
        unit(
            data_intensity=1.0,
            families={f"F{i}": 1 for i in range(8)},
            offshore_share=0.5,
            daily_share_classes=5000,
            nav_non_fic=1e12,
            launches=50,
            net_flow_ratio=0.5,
            new_entities=3,
            performance_excess=0.2,
        ),
    )
    worst = score_unit(
        CONFIG,
        unit(
            data_intensity=0.3,
            families={"Outros": 1},
            offshore_share=0.0,
            daily_share_classes=1,
            nav_non_fic=1e6,
            launches=0,
            net_flow_ratio=-0.5,
            new_entities=0,
            performance_excess=-0.2,
        ),
    )
    assert best.fit.point == pytest.approx(100.0)
    assert worst.fit.point == pytest.approx(0.0)
    assert (best.priority_point or 0) > (worst.priority_point or 0)
    for score in (best, worst):
        total = sum(v for v in score.fit.contributions.values() if v is not None)
        assert total == pytest.approx(score.fit.point)


# --- monotonicity and separation of outputs ------------------------------------


@pytest.mark.parametrize(
    ("field", "low", "high", "group"),
    [
        ("net_flow_ratio", -0.10, 0.10, "timing"),
        ("launches", 1, 10, "timing"),
        ("new_entities", 0, 2, "timing"),
        ("nav_non_fic", 2e9, 50e9, "fit"),
        ("offshore_share", 0.0, 0.25, "fit"),
        ("data_intensity", 0.5, 0.9, "fit"),
    ],
)
def test_scores_move_in_the_right_direction(
    field: str, low: float, high: float, group: str
) -> None:
    lo = score_unit(CONFIG, unit(**{field: low}))
    hi = score_unit(CONFIG, unit(**{field: high}))
    lo_group, hi_group = (lo.fit, hi.fit) if group == "fit" else (lo.timing, hi.timing)
    assert (hi_group.point or 0) > (lo_group.point or 0)
    assert (hi.priority_point or 0) > (lo.priority_point or 0)


def test_confidence_never_changes_fit_or_timing() -> None:
    clean = score_unit(CONFIG, unit())
    conflicted = score_unit(
        CONFIG, unit(open_conflicts=5, freshness_share=0.0, identity_found_active=False)
    )
    assert conflicted.confidence < clean.confidence
    assert conflicted.fit == clean.fit
    assert conflicted.timing == clean.timing
    assert conflicted.priority_point == clean.priority_point


def test_curated_signal_raises_timing_and_coverage() -> None:
    signal = ManualSignal(
        "s1",
        "org-test",
        "",
        "hiring",
        REF - timedelta(days=10),
        "Contratou head de quant",
        2,
        "https://example.com/noticia",
        "Valor Econômico",
    )
    without = score_unit(CONFIG, unit())
    with_signal = score_unit(CONFIG, unit(manual_signals={"hiring": [signal]}))
    hiring = next(f for f in with_signal.factors if f.key == "hiring")
    assert hiring.value == pytest.approx(1.0) and hiring.evidence
    assert with_signal.timing.coverage > without.timing.coverage
    assert (with_signal.timing.point or 0) > (without.timing.point or 0)


def test_signals_require_source_url(tmp_path: Path) -> None:
    path = tmp_path / "signals.csv"
    path.write_text(
        "signal_id,account_id,unit_key,signal_type,observed_at,description,strength,"
        "source_url,source_publisher,collected_at,verified_by\n"
        "s1,org-x,,hiring,2026-10-01,Contratação,1,,Fonte,2026-10-02,analista\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no source URL"):
        load_signals(path)


def test_assumption_desk_is_flagged_and_less_confident() -> None:
    priors = {
        "workflow_complexity": 0.9,
        "asset_breadth": 0.9,
        "international": 0.8,
        "data_api_need": 0.9,
        "user_potential": 0.9,
    }
    desk = unit(
        unit_key="org-bank:trading",
        desk_key="trading",
        evidence_mode="assumption",
        priors=priors,
        launches=None,
        net_flow_ratio=None,
        new_entities=None,
        performance_excess=None,
        comparable_share=None,
    )
    score = score_unit(CONFIG, desk)
    observed = score_unit(CONFIG, unit())

    assert all(f.status == "assumption" for f in score.factors if f.group == "fit")
    assert score.fit.assumption_share == pytest.approx(1.0)
    assert score.timing.point is None and score.priority_point is None
    assert score.tier.endswith("timing desconhecido")
    assert score.confidence < observed.confidence
    assert all(r.polarity in {"~", "?"} for r in score.reasons)


# --- duplicates and real-data pipeline -----------------------------------------


def _inputs_with_duplicates() -> tuple[CuratedInputs, CuratedInputs]:
    from networking_intel.scoring.features import load_inputs

    real = load_inputs(ROOT)
    duplicated = dataclasses.replace(
        real,
        classes=pl.concat([real.classes, real.classes.head(200)]),
        metrics=pl.concat([real.metrics, real.metrics.head(200)]),
    )
    return real, duplicated


def test_duplicate_rows_do_not_change_features() -> None:
    real, duplicated = _inputs_with_duplicates()
    base = {u.unit_key: u for u in build_units(real, CONFIG)}
    dup = {u.unit_key: u for u in build_units(duplicated, CONFIG)}
    for key, features in base.items():
        assert dup[key].active_classes == features.active_classes
        assert dup[key].nav_non_fic == features.nav_non_fic
        assert dup[key].launches == features.launches


def test_banks_are_scored_by_desk_never_as_conglomerate() -> None:
    from networking_intel.scoring.features import load_inputs

    keys = {u.unit_key for u in build_units(load_inputs(ROOT), CONFIG)}
    assert "org-btg-pactual" not in keys and "org-itau-bba" not in keys
    assert {"org-btg-pactual:asset-management", "org-itau-bba:sales-trading-treasury"} <= keys
    assert len([k for k in keys if ":" not in k]) == 10


def test_strategy_family_mapping() -> None:
    assert strategy_family("Classes de Cotas de Fundos FIDC", None, None).startswith("Crédito")
    assert (
        strategy_family("Classes de Cotas de Fundos FIF", "Multimercado", "Multimercados Macro")
        == "Multimercado"
    )
    assert strategy_family("FIF", "Renda Fixa", "Previdência RF Duração Livre") == "Previdência"


def _copy_inputs(target: Path) -> None:
    for relative in (
        "data/staging/pilot_accounts.csv",
        "data/enriched/fund_classes.csv",
        "data/enriched/fund_metrics.csv",
        "data/enriched/legal_entities.csv",
        "data/enriched/quality_report.json",
        "data/reference/commercial_signals.csv",
        "config/scoring/opportunity_v1.yaml",
    ):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, destination)
    (target / "docs").mkdir()


def test_pipeline_is_reproducible_and_explainable(tmp_path: Path) -> None:
    _copy_inputs(tmp_path)
    config = tmp_path / "config/scoring/opportunity_v1.yaml"
    first = run_scoring(tmp_path, config, draws=50)
    second = run_scoring(tmp_path, config, draws=50)
    assert first["outputs_sha256"] == second["outputs_sha256"]

    explanations = json.loads(
        (tmp_path / "data/scored/score_explanations.json").read_text(encoding="utf-8")
    )
    assert explanations["limitations"]
    for unit_score in explanations["units"]:
        for group in ("fit", "timing"):
            score = unit_score[group]
            if score["point"] is not None:
                total = sum(v for v in score["contributions"].values() if v is not None)
                assert total == pytest.approx(score["point"])
        for factor in unit_score["factors"]:
            if factor["value"] is not None:
                assert factor["evidence"], factor["key"]
    report = (tmp_path / "docs/opportunity_model_report.md").read_text(encoding="utf-8")
    assert "Não é probabilidade de compra" in report


def test_calibration_refuses_small_or_leaky_samples() -> None:
    record = OutcomeRecord("org-x", "opportunity-v1.0.0", REF, REF, "won", "crm:1")
    with pytest.raises(InsufficientOutcomesError, match="need"):
        require_calibration_data([record] * 5)
    leaky = dataclasses.replace(record, observed_at=REF - timedelta(days=1))
    with pytest.raises(InsufficientOutcomesError, match="leakage"):
        require_calibration_data([leaky] * 60)


def test_aggregate_without_evidence_has_no_point() -> None:
    timing = score_unit(
        CONFIG,
        unit(
            evidence_mode="assumption",
            priors={
                "workflow_complexity": 0.5,
                "asset_breadth": 0.5,
                "international": 0.5,
                "data_api_need": 0.5,
                "user_potential": 0.5,
            },
            launches=None,
            net_flow_ratio=None,
            new_entities=None,
            performance_excess=None,
        ),
    ).timing
    assert timing.point is None and timing.lower == 0.0 and timing.upper == 100.0
    assert aggregate([], {}).point is None
