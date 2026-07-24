"""
AIC orchestrator — Adapter → AKL → Credibility → Risk → Pricing → Decision → Explain.

Products never call actuarial engines directly.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from aic.contracts.decision_result import DecisionResult
from aic.contracts.explanation import Explanation
from aic.contracts.risk_result import RiskResult
from aic.core.credibility import BuhlmannStraubEngine, CredibilityContext
from aic.core.explainability import ExplainabilityEngine
from aic.core.pricing import PricingAssumptions, PricingResult, StandardPricingEngine
from aic.core.risk_engine import ClassRateRiskEngine
from aic.decision import DecisionEngine
from aic.products.ctflex import CTFlexAdapter, CTFlexRules, generate_ctflex_features
from aic.products.ctflex.rules import CLASS_RATE_INCOME

PLATFORM_MODEL_VERSION = "aic-platform-1.0.0"
MORTALITY_BASIS = "SA85-90 (illustrative) · ASSA2008 · Zimbabwe calibration"


def assumptions_from_ctflex_rules(rules: CTFlexRules) -> PricingAssumptions:
    """Map CT Flex product loads into reusable pricing assumptions."""
    return PricingAssumptions(
        expense_ratio=rules.expense_load,
        fixed_expense=0.0,
        profit_load=rules.profit_load,
        risk_margin=0.03,
        tax_fee_ratio=0.0,
        discount_ratio=0.0,
        min_premium=0.0,
        portfolio="ctflex_income",
    )


class AICPlatform:
    def __init__(self) -> None:
        self.adapter = CTFlexAdapter()
        self.credibility = BuhlmannStraubEngine(k=50.0)
        self.risk = ClassRateRiskEngine()
        self.pricing = StandardPricingEngine()
        self.rules = CTFlexRules()
        self.decision = DecisionEngine(self.rules)
        self.explainer = ExplainabilityEngine()

    def quote_ctflex(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        if raw_input.get("ecocash_consent", True) is False:
            raise ValueError("Alternative underwriting requires EcoCash / platform data consent")

        data = self.adapter.transform(raw_input)
        features = generate_ctflex_features(data)
        cred_ctx = CredibilityContext.from_feature_vector(
            features,
            CLASS_RATE_INCOME,
            portfolio="ctflex_income",
        )
        cred = self.credibility.calculate(cred_ctx)
        risk: RiskResult = self.risk.predict(features, cred)
        pricing: PricingResult = self.pricing.price(
            risk, assumptions_from_ctflex_rules(self.rules)
        )
        decision: DecisionResult = self.decision.decide(features, risk, pricing)
        explanation: Explanation = self.explainer.explain(
            features, risk, decision, credibility=cred, pricing=pricing
        )

        return {
            "decision": decision.decision,
            "premium": decision.premium,
            "premium_rate": decision.premium_rate,
            "benefit": decision.benefit,
            "status": decision.status,
            "risk_class": decision.risk_class,
            "payment_method": decision.payment_method,
            "expected_loss": risk.expected_loss,
            "pure_premium": pricing.pure_premium,
            "technical_premium": pricing.technical_premium,
            "commercial_premium": pricing.commercial_premium,
            "pricing_components": pricing.components,
            "pricing_metadata": pricing.metadata,
            "confidence": risk.confidence,
            "credibility_z": risk.credibility_z,
            "credibility_class": cred.credibility_class,
            "credibility_drivers": cred.drivers,
            "credibility_confidence": cred.confidence,
            "credibility_metadata": cred.metadata,
            "model": risk.model_name,
            "model_version": risk.model_version,
            "features": features.features,
            "feature_groups": features.feature_groups,
            "feature_metadata": features.metadata,
            "explanation": {
                "summary": explanation.summary,
                "confidence": explanation.confidence,
                "factors": [asdict(f) for f in explanation.factors],
            },
            "extras": decision.extras,
            "context": data.context,
        }

    def underwrite_ctflex_api(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        CT Flex MVP camelCase payload (compatible with legacy underwrite_to_dict),
        produced by the v2 orchestrator path.
        """
        quote = self.quote_ctflex(raw_input)
        return quote_to_ctflex_underwrite(quote)


def quote_to_ctflex_underwrite(quote: Dict[str, Any]) -> Dict[str, Any]:
    """Map orchestrator quote → CT Flex TypeScript UnderwritingResult shape."""
    features = quote.get("features") or {}
    extras = quote.get("extras") or {}
    context = quote.get("context") or {}
    explanation = quote.get("explanation") or {}

    decision = str(quote.get("decision", "Refer"))
    risk_rating = str(quote.get("risk_class", "Moderate"))
    if decision == "Refer":
        risk_rating = "Elevated"
    approved = decision != "Decline"

    weekly = float(features.get("average_weekly_income", 0) or 0)
    income_estimate = int(round(weekly * 4.0)) if weekly else 0
    benefit = float(quote.get("benefit", 0) or 0)
    coverage = int(round(benefit * 4.0)) if benefit else int(round(income_estimate * 0.6))

    txn = int(context.get("transaction_count", features.get("transaction_frequency", 0) or 0))
    class_rate = float(extras.get("class_rate", CLASS_RATE_INCOME))
    z = float(quote.get("credibility_z", 0) or 0)
    confidence = float(quote.get("confidence", 0) or 0)

    factors = []
    for f in explanation.get("factors") or []:
        name = str(f.get("name", "factor"))
        slug = name.lower().replace(" ", "_")
        factors.append(
            {
                "id": slug,
                "label": name,
                "bps": 0,
                "explanation": f"{f.get('impact', '')}: {f.get('detail', '')}".strip(": "),
            }
        )

    return {
        "approved": approved,
        "riskRating": risk_rating,
        "incomeEstimateUsd": income_estimate,
        "premiumRate": float(quote.get("premium_rate") or class_rate),
        "coverageUsd": coverage,
        "confidenceScore": int(round(confidence * 100)),
        "credibilityZ": round(z, 2),
        "transactionCount": txn,
        "classRate": class_rate,
        "factors": factors,
        "mortalityBasis": MORTALITY_BASIS,
        "modelVersion": PLATFORM_MODEL_VERSION,
        "engine": "aic.orchestrator.AICPlatform",
        "decision": decision,
        "status": quote.get("status"),
        "paymentMethod": quote.get("payment_method"),
        "expectedLoss": quote.get("expected_loss"),
        "technicalPremium": quote.get("technical_premium"),
        "commercialPremium": quote.get("commercial_premium"),
        "explanation": explanation,
    }
