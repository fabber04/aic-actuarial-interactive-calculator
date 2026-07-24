"""Decision Engine — product rules on top of priced risk (not actuarial loading)."""

from __future__ import annotations

from aic.contracts.decision_result import DecisionResult
from aic.contracts.feature_vector import FeatureVector
from aic.contracts.risk_result import RiskResult
from aic.core.pricing.base import PricingResult
from aic.products.ctflex.rules import CTFlexRules


class DecisionEngine:
    """
    Applies product / commercial packaging:

    - bind / refer / decline
    - benefits
    - payment method (e.g. PAYG % of fare)
    - maps indicated commercial premium → product premium presentation
    """

    def __init__(self, rules: CTFlexRules | None = None) -> None:
        self.rules = rules or CTFlexRules()

    def decide(
        self,
        features: FeatureVector,
        risk: RiskResult,
        pricing: PricingResult,
    ) -> DecisionResult:
        r = self.rules
        z = risk.credibility_z

        weekly_income = float(features.features.get("average_weekly_income", 100.0) or 100.0)
        monthly_income = max(weekly_income * 4.0, 1.0)
        benefit = min(r.benefit_weekly_cap, r.replacement_ratio * weekly_income)

        # Product commercial premium = indicated commercial from Pricing Engine
        premium = round(float(pricing.commercial_premium), 2)

        # PAYG: express indicated commercial as % of monthly earnings proxy, floored
        payg_rate = premium / monthly_income
        vol = float(features.features.get("income_volatility", 0.2) or 0.2)
        payg_rate = payg_rate * (1.0 + 0.05 * vol)
        payg_rate = max(r.min_premium_rate, round(payg_rate, 4))

        if z < r.z_refer_threshold:
            decision = "Refer"
            status = "REFER"
        else:
            decision = "Approved"
            status = "ACTIVE"

        return DecisionResult(
            decision=decision,
            premium=premium,
            benefit=round(benefit, 2),
            status=status,
            risk_class=risk.risk_class,
            payment_method="PAYG",
            premium_rate=payg_rate,
            extras={
                "grace_days": r.grace_days,
                "class_rate": r.class_rate,
                "expected_loss": risk.expected_loss,
                "pure_premium": pricing.pure_premium,
                "technical_premium": pricing.technical_premium,
                "commercial_premium": pricing.commercial_premium,
                "pricing_components": pricing.components,
                "model_version": risk.model_version,
            },
        )
