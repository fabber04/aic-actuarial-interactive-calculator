"""
Bühlmann–Straub strategy — first implementation of the AIC Credibility Framework.

Wraps ``engine_model.CredibilityParams`` for the classical Z = n/(n+k) form.
"""

from __future__ import annotations

from datetime import datetime, timezone

from aic.core.credibility.base import (
    CredibilityContext,
    CredibilityEngine,
    CredibilityResult,
    build_credibility_drivers,
    classify_credibility,
    credibility_confidence,
)
from aic.engine_model import CredibilityParams


class BuhlmannStraubEngine(CredibilityEngine):
    """Bühlmann–Straub partial credibility (volume / exposure based)."""

    method_name = "Bühlmann–Straub"
    method_version = "1.0.0"

    def __init__(self, k: float = 50.0) -> None:
        self.k = float(k)
        self._params = CredibilityParams(
            full_credibility_claims=max(self.k, 1.0),
            buhlmann_k=self.k,
        )

    def calculate(self, context: CredibilityContext) -> CredibilityResult:
        # Prefer exposure; fall back to observation count (transaction volume proxy)
        n = float(context.exposure) if context.exposure > 0 else float(context.observation_count)
        z = self._params.credibility(n)

        individual = float(context.individual_rate_proxy)
        if context.loss_history:
            individual = sum(context.loss_history) / max(len(context.loss_history), 1)

        collective = float(context.collective_rate)
        adjusted = z * individual + (1.0 - z) * collective
        cred_class = classify_credibility(z)
        drivers = build_credibility_drivers(
            z=z,
            exposure=float(context.exposure),
            observation_count=float(context.observation_count),
            group_scores=context.group_scores,
            k=self.k,
        )
        confidence = credibility_confidence(z, context.observation_count, k=self.k)

        return CredibilityResult(
            credibility_factor=round(z, 4),
            adjusted_risk=round(adjusted, 6),
            individual_rate=round(individual, 6),
            collective_rate=round(collective, 6),
            credibility_class=cred_class,
            observation_count=float(context.observation_count),
            exposure=float(context.exposure),
            confidence=confidence,
            drivers=drivers,
            metadata={
                "method": self.method_name,
                "version": self.method_version,
                "portfolio": context.portfolio,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "buhlmann_k": self.k,
                "inputs_used": [
                    "exposure" if context.exposure > 0 else "observation_count",
                    "individual_rate_proxy",
                    "collective_rate",
                    *(["loss_history"] if context.loss_history else []),
                ],
                "context_metadata": context.metadata,
            },
        )
