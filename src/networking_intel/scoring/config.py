from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

FIT_FACTORS = (
    "workflow_complexity",
    "asset_breadth",
    "international",
    "data_api_need",
    "user_potential",
)
TIMING_FACTORS = (
    "product_launches",
    "net_flows",
    "expansion",
    "hiring",
    "m_and_a",
    "operational_change",
    "performance",
)


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactorSpec(_Frozen):
    weight: float = Field(ge=0)
    label: str
    description: str


class Scale(_Frozen):
    kind: Literal["linear", "log", "log1p"]
    low: float
    high: float

    def transform(self, value: float) -> float:
        if self.kind == "linear":
            x, low, high = value, self.low, self.high
        elif self.kind == "log":
            x, low, high = math.log(max(value, 1e-12)), math.log(self.low), math.log(self.high)
        else:
            x, low, high = math.log1p(max(value, 0.0)), math.log1p(self.low), math.log1p(self.high)
        return min(1.0, max(0.0, (x - low) / (high - low)))


class EvidenceRules(_Frozen):
    min_net_flow_nav_coverage: float
    min_performance_nav_coverage: float
    launch_window_days: int
    expansion_window_days: int
    manual_signal_validity_days: int


class Tiers(_Frozen):
    fit_high: float
    timing_high: float
    min_fit_coverage: float
    min_timing_coverage: float


class ConfidenceWeights(_Frozen):
    evidence_coverage: float
    identity: float
    freshness: float
    conflicts: float
    comparability: float
    pending_identity_factor: float
    conflicts_for_zero: int

    def component_weights(self) -> dict[str, float]:
        return {
            "evidence_coverage": self.evidence_coverage,
            "identity": self.identity,
            "freshness": self.freshness,
            "conflicts": self.conflicts,
            "comparability": self.comparability,
        }


class ReasonThresholds(_Frozen):
    positive: float
    negative: float


class DeskSpec(_Frozen):
    key: str
    name: str
    entity_cnpjs: tuple[str, ...] = ()
    priors: dict[str, float] = Field(default_factory=dict)
    products: tuple[str, ...]

    @model_validator(mode="after")
    def evidence_or_priors(self) -> DeskSpec:
        if not self.entity_cnpjs and set(self.priors) != set(FIT_FACTORS):
            raise ValueError(f"desk {self.key} needs entity_cnpjs or priors for every fit factor")
        if any(not 0 <= value <= 1 for value in self.priors.values()):
            raise ValueError(f"desk {self.key} priors must be within [0, 1]")
        return self


class ProductSpec(_Frozen):
    name: str
    workflow: str


class ProductRule(_Frozen):
    when: dict[str, Any]
    products: tuple[str, ...]
    rationale: str


class SanityExpectation(_Frozen):
    higher: str
    lower: str
    output: Literal["fit", "timing", "priority"]
    rationale: str


class ScoringConfig(_Frozen):
    model_version: str
    description: str
    fit: dict[str, FactorSpec]
    timing: dict[str, FactorSpec]
    limits: dict[str, float]
    scales: dict[str, Scale]
    evidence_rules: EvidenceRules
    priority_index: dict[str, float]
    tiers: Tiers
    confidence: ConfidenceWeights
    reason_thresholds: ReasonThresholds
    family_data_intensity: dict[str, float]
    bank_desks: dict[str, tuple[DeskSpec, ...]]
    products: dict[str, ProductSpec]
    product_rules: tuple[ProductRule, ...]
    sanity_expectations: tuple[SanityExpectation, ...]

    @model_validator(mode="after")
    def validate_model(self) -> ScoringConfig:
        if tuple(self.fit) != FIT_FACTORS or tuple(self.timing) != TIMING_FACTORS:
            raise ValueError("fit/timing factors must match the documented factor set")
        for group, specs in (("fit", self.fit), ("timing", self.timing)):
            total = sum(spec.weight for spec in specs.values())
            if not math.isclose(total, 1.0, abs_tol=1e-9):
                raise ValueError(f"{group} weights must sum to 1, got {total}")
        if self.timing["performance"].weight > self.limits["max_performance_weight"]:
            raise ValueError("performance weight exceeds the configured limit")
        if not math.isclose(sum(self.priority_index.values()), 1.0, abs_tol=1e-9):
            raise ValueError("priority_index weights must sum to 1")
        if not math.isclose(sum(self.confidence.component_weights().values()), 1.0):
            raise ValueError("confidence component weights must sum to 1")
        known = set(self.products)
        for desks in self.bank_desks.values():
            for desk in desks:
                if missing := set(desk.products) - known:
                    raise ValueError(f"unknown products {missing} in desk {desk.key}")
        for rule in self.product_rules:
            if missing := set(rule.products) - known:
                raise ValueError(f"unknown products {missing} in product rule")
        return self

    def weights(self, group: Literal["fit", "timing"]) -> dict[str, float]:
        specs = self.fit if group == "fit" else self.timing
        return {key: spec.weight for key, spec in specs.items()}

    def with_weights(
        self, fit: dict[str, float] | None = None, timing: dict[str, float] | None = None
    ) -> ScoringConfig:
        """Copy with replaced (renormalised) weights — used by sensitivity analysis."""

        def apply(specs: dict[str, FactorSpec], new: dict[str, float] | None) -> dict[str, Any]:
            if new is None:
                return {k: v.model_dump() for k, v in specs.items()}
            total = sum(new.values())
            return {k: {**v.model_dump(), "weight": new[k] / total} for k, v in specs.items()}

        data = self.model_dump()
        data["fit"] = apply(self.fit, fit)
        data["timing"] = apply(self.timing, timing)
        data["limits"] = {**self.limits, "max_performance_weight": 1.0}
        return ScoringConfig.model_validate(data)


def load_config(path: Path) -> tuple[ScoringConfig, str]:
    raw = path.read_bytes()
    config = ScoringConfig.model_validate(yaml.safe_load(raw.decode("utf-8")))
    return config, hashlib.sha256(raw).hexdigest()
