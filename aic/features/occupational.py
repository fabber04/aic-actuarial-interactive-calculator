"""
Occupational actuarial concepts — table-driven hazard scores.

Algorithms stay separate from actuarial assumptions so tables can be revised
without changing business logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional


@dataclass(frozen=True)
class OccupationRiskTable:
    """
    Actuarial occupation hazard table (scores on [0, 1]).

    Keys are normalized lowercase occupation labels.
    """

    scores: Mapping[str, float] = field(
        default_factory=lambda: {
            "courier": 0.55,
            "driver": 0.60,
            "vendor": 0.35,
            "freelancer": 0.30,
            "agent": 0.40,
            "farmer": 0.45,
            "teacher": 0.25,
            "nurse": 0.40,
            "unknown": 0.50,
        }
    )
    default_score: float = 0.50
    version: str = "occupation_table_v1"

    def score(self, occupation: str | None) -> float:
        if not occupation:
            return self.default_score
        key = str(occupation).strip().lower()
        return float(self.scores.get(key, self.default_score))

    def with_overrides(self, overrides: Mapping[str, float]) -> "OccupationRiskTable":
        merged = {**dict(self.scores), **{k.lower(): float(v) for k, v in overrides.items()}}
        return OccupationRiskTable(
            scores=merged,
            default_score=self.default_score,
            version=self.version,
        )


DEFAULT_OCCUPATION_TABLE = OccupationRiskTable()


def occupation_risk_score(
    occupation: str | None,
    table: Optional[OccupationRiskTable] = None,
) -> float:
    """Look up occupation hazard from the actuarial table (not hard-coded logic)."""
    return (table or DEFAULT_OCCUPATION_TABLE).score(occupation)


def build_occupational_features(
    occupation: str | None,
    *,
    table: Optional[OccupationRiskTable] = None,
) -> Dict[str, float]:
    tbl = table or DEFAULT_OCCUPATION_TABLE
    risk = occupation_risk_score(occupation, tbl)
    return {
        "occupation_risk": round(risk, 4),
        # Inverse convenience for dashboards (higher = safer occupation)
        "occupation_safety": round(max(0.0, min(1.0, 1.0 - risk)), 4),
    }


def occupational_group_score(features: Dict[str, float]) -> float:
    """Composite 0–100 (higher = safer occupation profile)."""
    safety = features.get("occupation_safety", 1.0 - features.get("occupation_risk", 0.5))
    return round(max(0.0, min(100.0, safety * 100.0)), 1)
