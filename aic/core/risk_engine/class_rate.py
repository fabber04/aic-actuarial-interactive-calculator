"""
Phase-1 CT Flex risk estimate from credibility-adjusted class rate.

Full Gamma GLM (fremtpl_glm) plugs in here later as another RiskEngine impl.
"""

from __future__ import annotations

from aic.contracts.feature_vector import FeatureVector
from aic.contracts.risk_result import RiskResult
from aic.core.credibility.base import CredibilityResult
from aic.core.risk_engine.base import RiskEngine

MODEL_NAME = "ctflex_class_rate_v1"
MODEL_VERSION = "2.0.0-skeleton"


class ClassRateRiskEngine(RiskEngine):
    """E(loss) ≈ credibility-adjusted rate × reference income scale."""

    def predict(
        self,
        features: FeatureVector,
        credibility: CredibilityResult,
    ) -> RiskResult:
        ref_income = features.features.get("average_weekly_income", 100.0)
        # Expected monthly benefit cost proxy for income product
        expected_loss = credibility.adjusted_risk * max(ref_income, 1.0) * 4.0
        z = credibility.credibility_factor
        confidence = round(0.55 + z * 0.40, 4)
        if z < 0.25:
            risk_class = "Elevated"
        elif z < 0.5:
            risk_class = "Moderate"
        else:
            risk_class = "Low"
        return RiskResult(
            expected_loss=round(expected_loss, 4),
            confidence=confidence,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            credibility_z=z,
            risk_class=risk_class,
        )
