"""
AIC Credibility Framework — contracts.

Answers one question: how much weight on individual vs collective experience?

Does not set premiums, benefits, approvals, or pricing rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from aic.contracts.feature_vector import FeatureVector

# Z-band → credibility class (dashboard / explainability)
CREDIBILITY_CLASSES = (
    (0.20, "Initial"),  # [0, 0.20)
    (0.50, "Emerging"),  # [0.20, 0.50)
    (0.80, "Established"),  # [0.50, 0.80)
    (1.01, "Mature"),  # [0.80, 1.00]
)


def classify_credibility(z: float) -> str:
    z = max(0.0, min(1.0, float(z)))
    for upper, label in CREDIBILITY_CLASSES:
        if z < upper:
            return label
    return "Mature"


@dataclass
class CredibilityContext:
    """
    Dedicated inputs for the Credibility Layer.

    Built from a FeatureVector but intentionally omits occupation risk, premiums,
    and expected loss — those belong to risk / decision layers.
    """

    exposure: float
    observation_count: float
    individual_rate_proxy: float
    collective_rate: float
    loss_history: List[float] = field(default_factory=list)
    # Optional diagnostics only (e.g. financial_index, behavioural_index) — not occupation
    group_scores: Dict[str, float] = field(default_factory=dict)
    portfolio: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_feature_vector(
        cls,
        features: FeatureVector,
        collective_rate: float,
        *,
        portfolio: str = "",
    ) -> "CredibilityContext":
        feats = features.features or {}
        exposure = float(features.exposure) if features.exposure > 0 else float(
            feats.get("transaction_frequency", 0.0) or 0.0
        )
        observation_count = float(
            feats.get("transaction_frequency", len(features.loss_history) or exposure)
        )
        individual = float(feats.get("individual_rate_proxy", collective_rate))
        # Diagnostics: only stability-style group scores from AKL metadata
        raw_scores = (features.metadata or {}).get("group_scores") or {}
        allowed = ("financial_index", "behavioural_index")
        group_scores = {k: float(raw_scores[k]) for k in allowed if k in raw_scores}

        return cls(
            exposure=exposure,
            observation_count=observation_count,
            individual_rate_proxy=individual,
            collective_rate=float(collective_rate),
            loss_history=list(features.loss_history or []),
            group_scores=group_scores,
            portfolio=portfolio or features.product,
            metadata={
                "feature_version": (features.metadata or {}).get("feature_version"),
                "source_generator": (features.metadata or {}).get("generator"),
            },
        )


@dataclass
class CredibilityResult:
    """
    Mathematical credibility output — not a product decision.

    ``credibility_factor`` is Z; ``adjusted_risk`` is the credibility-weighted rate.
    """

    credibility_factor: float
    adjusted_risk: float
    individual_rate: float
    collective_rate: float
    credibility_class: str = "Initial"
    observation_count: float = 0.0
    exposure: float = 0.0
    confidence: float = 0.0
    drivers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def z(self) -> float:
        return self.credibility_factor

    @property
    def adjusted_rate(self) -> float:
        return self.adjusted_risk


def build_credibility_drivers(
    *,
    z: float,
    exposure: float,
    observation_count: float,
    group_scores: Optional[Dict[str, float]] = None,
    k: float = 50.0,
) -> List[str]:
    """Human-readable reasons credibility is high or low (explainability feed)."""
    drivers: List[str] = []
    scores = group_scores or {}

    if observation_count >= k:
        drivers.append("Long observation history")
    elif observation_count >= k * 0.4:
        drivers.append("Moderate observation history")
    else:
        drivers.append("Limited observation history")

    if exposure >= k:
        drivers.append("Sufficient exposure")
    elif exposure >= k * 0.4:
        drivers.append("Partial exposure relative to full credibility standard")
    else:
        drivers.append("Thin exposure relative to full credibility standard")

    fin = scores.get("financial_index")
    if fin is not None:
        if fin >= 70:
            drivers.append("Stable transaction pattern")
        elif fin < 45:
            drivers.append("Volatile financial pattern reduces individual weight")

    beh = scores.get("behavioural_index")
    if beh is not None:
        if beh >= 70:
            drivers.append("Consistent behavioural engagement")
        elif beh < 45:
            drivers.append("Irregular activity pattern")

    if z >= 0.8:
        drivers.append("High credibility factor (mature experience)")
    elif z < 0.2:
        drivers.append("Low credibility factor — leaning on collective experience")

    # De-dupe while preserving order
    seen = set()
    unique: List[str] = []
    for d in drivers:
        if d not in seen:
            seen.add(d)
            unique.append(d)
    return unique


def credibility_confidence(z: float, observation_count: float, *, k: float = 50.0) -> float:
    """Governance-style confidence in the Z estimate itself (not product UW confidence)."""
    vol_term = min(1.0, observation_count / max(k, 1.0))
    return round(max(0.0, min(1.0, 0.45 * float(z) + 0.55 * vol_term)), 4)


class CredibilityEngine(ABC):
    """
    AIC Credibility Framework strategy interface.

    Implementations: Bühlmann–Straub (current), Bühlmann–Jewell / Bayesian (future).
    """

    method_name: str = "credibility"
    method_version: str = "1.0"

    @abstractmethod
    def calculate(self, context: CredibilityContext) -> CredibilityResult:
        """Return CredibilityResult only — never premiums or approval decisions."""
        ...

    def calculate_from_features(
        self,
        features: FeatureVector,
        collective_rate: float,
        *,
        portfolio: str = "",
    ) -> CredibilityResult:
        """Convenience: build CredibilityContext from an AKL FeatureVector."""
        ctx = CredibilityContext.from_feature_vector(
            features, collective_rate, portfolio=portfolio
        )
        return self.calculate(ctx)
