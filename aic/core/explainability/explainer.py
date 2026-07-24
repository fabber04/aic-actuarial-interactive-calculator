from __future__ import annotations

from typing import Optional

from aic.contracts.decision_result import DecisionResult
from aic.contracts.explanation import Explanation, ExplanationFactor
from aic.contracts.feature_vector import FeatureVector
from aic.contracts.risk_result import RiskResult
from aic.core.credibility.base import CredibilityResult
from aic.core.pricing.base import PricingResult


class ExplainabilityEngine:
    def explain(
        self,
        features: FeatureVector,
        risk: RiskResult,
        decision: DecisionResult,
        *,
        credibility: Optional[CredibilityResult] = None,
        pricing: Optional[PricingResult] = None,
    ) -> Explanation:
        factors: list[ExplanationFactor] = []

        if credibility is not None:
            factors.append(
                ExplanationFactor(
                    name="Credibility",
                    impact=credibility.credibility_class,
                    detail=f"Z={credibility.z:.2f}; " + "; ".join(credibility.drivers[:3]),
                )
            )
            for driver in credibility.drivers:
                factors.append(
                    ExplanationFactor(
                        name="Credibility driver",
                        impact="informational",
                        detail=driver,
                    )
                )

        if pricing is not None:
            factors.append(
                ExplanationFactor(
                    name="Pure Premium",
                    impact="informational",
                    detail=f"value={pricing.pure_premium:.4f}",
                )
            )
            factors.append(
                ExplanationFactor(
                    name="Technical Premium",
                    impact="informational",
                    detail=(
                        f"value={pricing.technical_premium:.4f} "
                        f"(expense={pricing.expense_loading:.4f}, "
                        f"profit={pricing.profit_loading:.4f}, "
                        f"risk_margin={pricing.risk_margin_amount:.4f})"
                    ),
                )
            )
            factors.append(
                ExplanationFactor(
                    name="Indicated Commercial Premium",
                    impact="informational",
                    detail=f"value={pricing.commercial_premium:.4f}",
                )
            )

        for key in (
            "financial_index",
            "behavioural_index",
            "occupational_index",
            "environmental_index",
        ):
            if key in features.features:
                value = features.features[key]
                factors.append(
                    ExplanationFactor(
                        name=key.replace("_", " ").title(),
                        impact="positive" if value >= 70 else ("watch" if value >= 45 else "higher risk"),
                        detail=f"score={value:.1f}/100",
                    )
                )

        for name, value in features.features.items():
            if name.endswith("_index"):
                continue
            if name.endswith("_risk") or "volatility" in name or "gap" in name:
                impact = "higher risk" if value > 0.5 else "neutral"
            elif "stability" in name or "consistency" in name or "diversity" in name:
                impact = "positive" if value >= 0.6 else "watch"
            else:
                impact = "informational"
            factors.append(
                ExplanationFactor(
                    name=name.replace("_", " ").title(),
                    impact=impact,
                    detail=f"value={value:.3f}",
                )
            )

        cred_bit = ""
        if credibility is not None:
            cred_bit = f" credibility={credibility.credibility_class} (Z={credibility.z:.2f})"
        price_bit = ""
        if pricing is not None:
            price_bit = (
                f" technical={pricing.technical_premium:.2f}"
                f" commercial={pricing.commercial_premium:.2f}"
            )
        summary = (
            f"{decision.decision}: premium={decision.premium:.4f}, "
            f"benefit={decision.benefit:.2f}, risk_class={risk.risk_class} "
            f"(Z={risk.credibility_z:.2f}).{cred_bit}{price_bit}"
        )
        return Explanation(summary=summary, factors=factors, confidence=risk.confidence)
