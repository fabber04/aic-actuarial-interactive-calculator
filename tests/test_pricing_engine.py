"""Tests for AIC Pricing Engine."""

from __future__ import annotations

import unittest

from aic.contracts.risk_result import RiskResult
from aic.core.pricing import PricingAssumptions, StandardPricingEngine
from aic.core.pricing.technical_rate import technical_premium
from aic.orchestrator import AICPlatform


class TestTechnicalPremiumFormula(unittest.TestCase):
    def test_permissive_loading(self) -> None:
        assumptions = PricingAssumptions(
            expense_ratio=0.12,
            fixed_expense=0.0,
            profit_load=0.05,
            risk_margin=0.03,
            tax_fee_ratio=0.0,
        )
        # (100) / (1 - 0.12 - 0.05 - 0.03) = 100 / 0.80 = 125
        self.assertAlmostEqual(technical_premium(100.0, assumptions), 125.0, places=6)


class TestStandardPricingEngine(unittest.TestCase):
    def test_pipeline_components(self) -> None:
        risk = RiskResult(
            expected_loss=120.0,
            confidence=0.8,
            model_name="test",
            model_version="1",
            credibility_z=0.5,
        )
        result = StandardPricingEngine().price(
            risk,
            PricingAssumptions(
                expense_ratio=0.12,
                profit_load=0.05,
                risk_margin=0.03,
                portfolio="demo",
            ),
        )
        self.assertAlmostEqual(result.pure_premium, 120.0)
        self.assertAlmostEqual(result.technical_premium, 150.0)  # 120/0.8
        self.assertAlmostEqual(result.commercial_premium, 150.0)
        self.assertEqual(result.metadata["method"], "standard_loaded_premium")
        self.assertIn("expense_loading", result.components)

    def test_discount_and_floor(self) -> None:
        risk = RiskResult(
            expected_loss=100.0,
            confidence=0.7,
            model_name="test",
            model_version="1",
            credibility_z=0.4,
        )
        result = StandardPricingEngine().price(
            risk,
            PricingAssumptions(
                expense_ratio=0.10,
                profit_load=0.05,
                risk_margin=0.05,
                discount_ratio=0.10,
                min_premium=50.0,
            ),
        )
        # denom = 0.80 → tech = 125; discount 10% → 112.5
        self.assertAlmostEqual(result.technical_premium, 125.0, places=4)
        self.assertAlmostEqual(result.commercial_premium, 112.5, places=4)


class TestOrchestratorUsesPricing(unittest.TestCase):
    def test_quote_exposes_pricing_layer(self) -> None:
        out = AICPlatform().quote_ctflex(
            {
                "occupation": "Courier",
                "transaction_count": 8,
                "transactions": [10, 12, 8, 15, 14, 11, 9, 13],
            }
        )
        self.assertIn("technical_premium", out)
        self.assertIn("commercial_premium", out)
        self.assertIn("pricing_components", out)
        self.assertGreater(out["technical_premium"], out["expected_loss"])
        self.assertEqual(out["payment_method"], "PAYG")
        self.assertGreater(out["premium_rate"], 0)


if __name__ == "__main__":
    unittest.main()
