from __future__ import annotations

from networking_intel.scoring.config import ScoringConfig
from networking_intel.scoring.features import UnitFeatures
from networking_intel.scoring.model import UnitScore

DESK_RATIONALE = "Workflow típico da mesa (premissa editável em config/scoring)."


def _rule_matches(when: dict[str, object], unit: UnitFeatures, score: UnitScore) -> bool:
    values = {f.key: f.value for f in score.factors}
    for condition, expected in when.items():
        if condition == "dominant_family" and unit.dominant_family != expected:
            return False
        if condition == "has_family" and not unit.families.get(str(expected)):
            return False
        if condition == "institution_type" and unit.institution_type != expected:
            return False
        if condition == "min_factor":
            assert isinstance(expected, dict)
            for key, threshold in expected.items():
                value = values.get(key)
                if value is None or value < threshold:
                    return False
    return True


def product_candidates(
    config: ScoringConfig, unit: UnitFeatures, score: UnitScore
) -> list[dict[str, str]]:
    """Workflow hypotheses for the sales conversation — never a purchase claim.

    Evidence rules apply wherever fund data was observed; desk catalogues from the
    config add the typical workflows of a bank area and are labelled as such.
    """
    found: dict[str, dict[str, list[str]]] = {}
    if unit.evidence_mode == "observed":
        for rule in config.product_rules:
            if _rule_matches(rule.when, unit, score):
                for code in rule.products:
                    found.setdefault(code, {}).setdefault("evidence_rule", []).append(
                        rule.rationale
                    )
    for code in unit.desk_products:
        found.setdefault(code, {}).setdefault("desk_config", []).append(DESK_RATIONALE)
    return [
        {
            "unit_key": unit.unit_key,
            "product_code": code,
            "product_name": config.products[code].name,
            "workflow": config.products[code].workflow,
            "rationale": " ".join(
                dict.fromkeys(text for texts in bases.values() for text in texts)
            ),
            "fit_status": "candidate",
            "basis": " + ".join(sorted(bases)),
        }
        for code, bases in found.items()
    ]
