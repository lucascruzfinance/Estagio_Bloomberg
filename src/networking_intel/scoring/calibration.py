"""Interface for future calibration against real commercial outcomes.

There is no historical target variable (opportunities opened, demos, wins) yet,
so no supervised model is trained. When Bloomberg CRM outcomes exist, record
them in the schema below and implement a ``Calibrator``; the expert weights in
config/scoring stay the baseline to beat.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Literal, Protocol

Outcome = Literal["opportunity_opened", "won", "lost", "no_opportunity"]
MIN_OUTCOMES = 50
MIN_POSITIVES = 10


@dataclass(frozen=True)
class OutcomeRecord:
    unit_key: str
    model_version: str
    scored_at: date
    observed_at: date
    outcome: Outcome
    source: str  # CRM system / record id; never free text from an external page


class Calibrator(Protocol):
    def fit(
        self, features: Sequence[dict[str, float | None]], outcomes: Sequence[OutcomeRecord]
    ) -> None: ...

    def suggested_weights(self) -> dict[str, dict[str, float]]: ...


class InsufficientOutcomesError(RuntimeError):
    pass


def require_calibration_data(outcomes: Sequence[OutcomeRecord]) -> None:
    """Guard: refuse to fit on too few or one-sided outcomes."""
    positives = sum(o.outcome in {"opportunity_opened", "won"} for o in outcomes)
    if len(outcomes) < MIN_OUTCOMES or positives < MIN_POSITIVES:
        raise InsufficientOutcomesError(
            f"need >= {MIN_OUTCOMES} outcomes with >= {MIN_POSITIVES} positives; "
            f"got {len(outcomes)} / {positives}"
        )
    if any(o.observed_at < o.scored_at for o in outcomes):
        raise InsufficientOutcomesError("outcome observed before the score existed (leakage)")
