"""Standard AIC Pricing Engine — expected loss → technical → indicated commercial."""

from __future__ import annotations

from datetime import datetime, timezone

from aic.contracts.risk_result import RiskResult
from aic.core.pricing.base import PricingAssumptions, PricingEngine, PricingResult
from aic.core.pricing.commercial_rate import commercial_premium
from aic.core.pricing.pure_premium import pure_premium_from_expected_loss
from aic.core.pricing.technical_rate import decompose_technical, technical_premium


class StandardPricingEngine(PricingEngine):
    method_name = "standard_loaded_premium"
    method_version = "1.0.0"

    def price(
        self,
        risk: RiskResult,
        assumptions: PricingAssumptions,
    ) -> PricingResult:
        pure = pure_premium_from_expected_loss(risk.expected_loss)
        tech = technical_premium(pure, assumptions)
        parts = decompose_technical(pure, tech, assumptions)
        commercial, disc = commercial_premium(tech, assumptions)

        return PricingResult(
            expected_loss=round(float(risk.expected_loss), 6),
            pure_premium=parts["pure_premium"],
            expense_loading=parts["expense_loading"],
            profit_loading=parts["profit_loading"],
            risk_margin_amount=parts["risk_margin"],
            taxes_fees=parts["taxes_fees"],
            technical_premium=parts["technical_premium"],
            discount_amount=round(disc, 6),
            commercial_premium=round(commercial, 6),
            components={
                **parts,
                "discount_amount": round(disc, 6),
                "commercial_premium": round(commercial, 6),
                "fixed_expense": parts["fixed_expense"],
            },
            metadata={
                "method": self.method_name,
                "version": self.method_version,
                "portfolio": assumptions.portfolio,
                "currency": assumptions.currency,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "assumptions": {
                    "expense_ratio": assumptions.expense_ratio,
                    "fixed_expense": assumptions.fixed_expense,
                    "profit_load": assumptions.profit_load,
                    "risk_margin": assumptions.risk_margin,
                    "tax_fee_ratio": assumptions.tax_fee_ratio,
                    "discount_ratio": assumptions.discount_ratio,
                    "min_premium": assumptions.min_premium,
                },
                "risk_model": risk.model_name,
                "risk_model_version": risk.model_version,
            },
        )
