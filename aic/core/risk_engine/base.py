from __future__ import annotations

from abc import ABC, abstractmethod

from aic.contracts.feature_vector import FeatureVector
from aic.contracts.risk_result import RiskResult
from aic.core.credibility.base import CredibilityResult


class RiskEngine(ABC):
    """Estimate E(Loss | X) — not commercial premium."""

    @abstractmethod
    def predict(
        self,
        features: FeatureVector,
        credibility: CredibilityResult,
    ) -> RiskResult:
        ...
