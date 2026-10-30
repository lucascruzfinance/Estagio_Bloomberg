"""Weight sensitivity: one-at-a-time (±50%) and Dirichlet perturbations.

Factor values do not depend on weights, so only the aggregation is recomputed.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from networking_intel.scoring.config import ScoringConfig
from networking_intel.scoring.model import FactorResult, aggregate, combine

SEED = 20261030


@dataclass(frozen=True)
class UnitFactors:
    unit_key: str
    fit: list[FactorResult]
    timing: list[FactorResult]


def _scores(
    config: ScoringConfig,
    units: Sequence[UnitFactors],
    fit_w: dict[str, float],
    timing_w: dict[str, float],
) -> dict[str, tuple[float | None, float | None]]:
    out: dict[str, tuple[float | None, float | None]] = {}
    for unit in units:
        fit = aggregate(unit.fit, fit_w)
        timing = aggregate(unit.timing, timing_w)
        priority, _, _ = combine(config, fit, timing)
        out[unit.unit_key] = (fit.point, priority)
    return out


def _ranks(values: dict[str, float | None]) -> dict[str, int]:
    present = sorted((k for k, v in values.items() if v is not None), key=lambda k: (-values[k], k))  # type: ignore[operator]
    return {key: position + 1 for position, key in enumerate(present)}


def run_sensitivity(
    config: ScoringConfig, units: Sequence[UnitFactors], draws: int = 1000
) -> tuple[list[dict[str, object]], dict[str, float]]:
    base_fit_w, base_timing_w = config.weights("fit"), config.weights("timing")
    base = _scores(config, units, base_fit_w, base_timing_w)
    base_fit_rank = _ranks({k: v[0] for k, v in base.items()})
    base_pri_rank = _ranks({k: v[1] for k, v in base.items()})

    oat_shift: dict[str, int] = {u.unit_key: 0 for u in units}
    for group, weights in (("fit", base_fit_w), ("timing", base_timing_w)):
        for factor in weights:
            for multiplier in (0.5, 1.5):
                changed = {k: w * (multiplier if k == factor else 1.0) for k, w in weights.items()}
                total = sum(changed.values())
                changed = {k: w / total for k, w in changed.items()}
                fit_w = changed if group == "fit" else base_fit_w
                timing_w = changed if group == "timing" else base_timing_w
                scores = _scores(config, units, fit_w, timing_w)
                ranks = _ranks({k: v[1] for k, v in scores.items()})
                fit_ranks = _ranks({k: v[0] for k, v in scores.items()})
                for key in oat_shift:
                    shifts = [
                        abs(ranks[key] - base_pri_rank[key])
                        if key in ranks and key in base_pri_rank
                        else 0,
                        abs(fit_ranks[key] - base_fit_rank[key])
                        if key in fit_ranks and key in base_fit_rank
                        else 0,
                    ]
                    oat_shift[key] = max(oat_shift[key], *shifts)

    rng = np.random.default_rng(SEED)
    fit_keys, timing_keys = list(base_fit_w), list(base_timing_w)
    fit_alpha = np.array([base_fit_w[k] for k in fit_keys]) * 20
    timing_alpha = np.array([base_timing_w[k] for k in timing_keys]) * 20
    pri_ranks: dict[str, list[int]] = {k: [] for k in base_pri_rank}
    fit_ranks_all: dict[str, list[int]] = {k: [] for k in base_fit_rank}
    rhos: list[float] = []
    ordered = sorted(base_pri_rank)
    for _ in range(draws):
        fw = dict(zip(fit_keys, rng.dirichlet(fit_alpha), strict=True))
        tw = dict(zip(timing_keys, rng.dirichlet(timing_alpha), strict=True))
        scores = _scores(config, units, fw, tw)
        ranks = _ranks({k: v[1] for k, v in scores.items()})
        f_ranks = _ranks({k: v[0] for k, v in scores.items()})
        # Timing coverage depends on the weights, so a unit can drop out of the
        # priority ranking in a draw; those draws are excluded for that unit.
        for key in pri_ranks:
            if key in ranks:
                pri_ranks[key].append(ranks[key])
        for key in fit_ranks_all:
            fit_ranks_all[key].append(f_ranks[key])
        common = [k for k in ordered if k in ranks]
        if len(common) > 2:
            # Inputs are already ranks without ties, so Pearson on them is Spearman.
            rho = np.corrcoef([base_pri_rank[k] for k in common], [ranks[k] for k in common])[0, 1]
            rhos.append(float(rho))

    rows: list[dict[str, object]] = []
    for unit in units:
        key = unit.unit_key
        pr = np.array(pri_ranks.get(key, []))
        fr = np.array(fit_ranks_all.get(key, []))
        rows.append(
            {
                "unit_key": key,
                "base_priority_rank": base_pri_rank.get(key),
                "priority_rank_p05": int(np.percentile(pr, 5)) if pr.size else None,
                "priority_rank_p95": int(np.percentile(pr, 95)) if pr.size else None,
                "p_top3_priority": float((pr <= 3).mean()) if pr.size else None,
                "base_fit_rank": base_fit_rank.get(key),
                "fit_rank_p05": int(np.percentile(fr, 5)) if fr.size else None,
                "fit_rank_p95": int(np.percentile(fr, 95)) if fr.size else None,
                "max_rank_shift_oat_50pct": oat_shift[key],
            }
        )
    summary = {
        "draws": float(draws),
        "spearman_mean": float(np.mean(rhos)) if rhos else float("nan"),
        "spearman_p05": float(np.percentile(rhos, 5)) if rhos else float("nan"),
    }
    return rows, summary
