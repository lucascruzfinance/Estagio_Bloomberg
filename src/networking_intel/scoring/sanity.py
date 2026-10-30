from __future__ import annotations

from collections.abc import Sequence

from networking_intel.scoring.config import ScoringConfig
from networking_intel.scoring.model import UnitScore


def _value(score: UnitScore, output: str) -> float | None:
    if output == "fit":
        return score.fit.point
    if output == "timing":
        return score.timing.point
    return score.priority_point


def _drivers(higher: UnitScore, lower: UnitScore, output: str) -> str:
    """Factors that explain why `lower` beat `higher` (largest contribution gaps)."""
    groups = ("fit", "timing") if output == "priority" else (output,)
    gaps: list[tuple[float, str]] = []
    for group in groups:
        h = (higher.fit if group == "fit" else higher.timing).contributions
        lo = (lower.fit if group == "fit" else lower.timing).contributions
        labels = {f.key: f.label for f in higher.factors if f.group == group}
        for key, label in labels.items():
            if h.get(key) is not None and lo.get(key) is not None:
                gaps.append(((lo[key] or 0.0) - (h[key] or 0.0), label))
    top = sorted(gaps, reverse=True)[:2]
    return "; ".join(
        f"{label} (+{gap:.1f} pts para o esperado menor)" for gap, label in top if gap > 0
    )


def check_expectations(
    config: ScoringConfig, scores: Sequence[UnitScore]
) -> list[dict[str, object]]:
    by_key = {score.unit_key: score for score in scores}
    results: list[dict[str, object]] = []
    for expectation in config.sanity_expectations:
        higher, lower = by_key.get(expectation.higher), by_key.get(expectation.lower)
        hv = _value(higher, expectation.output) if higher else None
        lv = _value(lower, expectation.output) if lower else None
        status = "not_evaluable" if hv is None or lv is None else "pass" if hv > lv else "fail"
        drivers = (
            _drivers(higher, lower, expectation.output)
            if status == "fail" and higher and lower
            else ""
        )
        results.append(
            {
                "higher": expectation.higher,
                "lower": expectation.lower,
                "output": expectation.output,
                "higher_value": hv,
                "lower_value": lv,
                "status": status,
                "rationale": expectation.rationale,
                "fail_drivers": drivers,
            }
        )
    return results
