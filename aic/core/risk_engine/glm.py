"""
Gamma GLM risk engine — platform RiskEngine adapter over fremtpl_glm.

Does not reimplement GLM math. Expected loss comes from the live Gamma
(log-link) price model, optionally credibility-blended toward the collective.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from aic.contracts.feature_vector import FeatureVector
from aic.contracts.risk_result import RiskResult
from aic.core.credibility.base import CredibilityResult
from aic.core.risk_engine.base import RiskEngine
from aic.core.risk_engine.predictor import GlmPredictor
from aic.fremtpl_glm import LivePricingEngine, PricingProfile

MODEL_NAME = "gamma_glm_price_v1"


class GammaGLMRiskEngine(RiskEngine):
    """
    E(Loss | X) ≈ Gamma GLM mean (charged-premium / price proxy).

    ``FeatureVector.features`` should carry the same keys the pricing profile
    expects (numeric + categorical encoded as present in the training schema).
    For full motor rows with mixed types, prefer ``predict_record``.
    """

    def __init__(
        self,
        predictor: Optional[GlmPredictor] = None,
        *,
        engine: Optional[LivePricingEngine] = None,
        store_path: Union[str, Path, None] = None,
        model_dir: Union[str, Path, None] = None,
        profile: Optional[PricingProfile] = None,
    ) -> None:
        if predictor is not None:
            self.predictor = predictor
        else:
            kwargs: Dict[str, Any] = {}
            if engine is not None:
                kwargs["engine"] = engine
            if store_path is not None:
                kwargs["store_path"] = store_path
            if model_dir is not None:
                kwargs["model_dir"] = model_dir
            if profile is not None:
                kwargs["profile"] = profile
            self.predictor = GlmPredictor(**kwargs)

    def predict_record(
        self,
        record: Dict[str, Any],
        credibility: CredibilityResult,
        *,
        product: str = "motor",
    ) -> RiskResult:
        """Score a raw policy/feature dict (preferred for motor schemas)."""
        mu = float(self.predictor.predict_records(record)[0])
        return self._to_result(mu, credibility, product=product)

    def predict(
        self,
        features: FeatureVector,
        credibility: CredibilityResult,
    ) -> RiskResult:
        if not features.features:
            raise ValueError("FeatureVector.features is empty — nothing to score")
        mu = float(self.predictor.predict_records(dict(features.features))[0])
        return self._to_result(mu, credibility, product=features.product)

    def _to_result(
        self,
        mu: float,
        credibility: CredibilityResult,
        *,
        product: str,
    ) -> RiskResult:
        z = float(credibility.credibility_factor)
        # Blend model mean with credibility-adjusted collective indication
        collective = float(credibility.adjusted_risk)
        if collective > 0 and abs(collective - mu) / max(mu, 1e-9) > 0.01:
            # If collective looks like a rate (<< mu), scale by mu as exposure proxy
            if collective < 1.0 and mu > 1.0:
                collective_loss = collective * mu
            else:
                collective_loss = collective
            expected = z * mu + (1.0 - z) * collective_loss
        else:
            expected = mu

        confidence = round(0.55 + z * 0.40, 4)
        if z < 0.25:
            risk_class = "Elevated"
        elif z < 0.5:
            risk_class = "Moderate"
        else:
            risk_class = "Low"

        version = self.predictor.version_id or "unversioned"
        return RiskResult(
            expected_loss=round(float(expected), 4),
            confidence=confidence,
            model_name=MODEL_NAME,
            model_version=version,
            credibility_z=z,
            risk_class=risk_class,
        )
