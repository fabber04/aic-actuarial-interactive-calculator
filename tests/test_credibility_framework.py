"""Tests for the AIC Credibility Framework."""

from __future__ import annotations

import unittest

from aic.contracts.data_objects import StandardizedData
from aic.core.credibility import (
    BuhlmannStraubEngine,
    CredibilityContext,
    classify_credibility,
)
from aic.features import build_feature_vector
from aic.products.ctflex.features import generate_ctflex_features
from aic.products.ctflex.rules import CLASS_RATE_INCOME


class TestCredibilityClasses(unittest.TestCase):
    def test_bands(self) -> None:
        self.assertEqual(classify_credibility(0.10), "Initial")
        self.assertEqual(classify_credibility(0.30), "Emerging")
        self.assertEqual(classify_credibility(0.60), "Established")
        self.assertEqual(classify_credibility(0.90), "Mature")


class TestCredibilityContext(unittest.TestCase):
    def test_omits_occupation_and_pricing(self) -> None:
        data = StandardizedData(
            product="ctflex_income",
            observations=[{"income": x} for x in [10, 12, 8, 15, 14, 11, 9, 13]],
            context={"occupation": "Courier", "transaction_count": 8, "platform": "Bolt"},
        )
        fv = generate_ctflex_features(data)
        self.assertIn("occupation_risk", fv.features)
        ctx = CredibilityContext.from_feature_vector(fv, CLASS_RATE_INCOME, portfolio="ctflex_income")
        # Context must not carry occupation into the credibility math surface
        self.assertFalse(hasattr(ctx, "occupation_risk"))
        self.assertIn("financial_index", ctx.group_scores)
        self.assertNotIn("occupational_index", ctx.group_scores)
        self.assertGreater(ctx.individual_rate_proxy, 0)


class TestBuhlmannStraubFramework(unittest.TestCase):
    def test_result_has_class_drivers_metadata(self) -> None:
        engine = BuhlmannStraubEngine(k=50.0)
        ctx = CredibilityContext(
            exposure=8.0,
            observation_count=8.0,
            individual_rate_proxy=0.025,
            collective_rate=0.0263,
            group_scores={"financial_index": 75.0, "behavioural_index": 70.0},
            portfolio="ctflex_income",
        )
        result = engine.calculate(ctx)
        self.assertAlmostEqual(result.z, 8 / 58, places=4)
        self.assertEqual(result.credibility_class, "Initial")
        self.assertTrue(result.drivers)
        self.assertEqual(result.metadata["method"], "Bühlmann–Straub")
        self.assertIn("exposure", result.metadata["inputs_used"])
        self.assertAlmostEqual(result.adjusted_rate, result.adjusted_risk)

    def test_from_features_convenience(self) -> None:
        data = StandardizedData(
            product="ctflex_income",
            observations=[{"income": 15} for _ in range(60)],
            context={"occupation": "Driver", "transaction_count": 60},
        )
        fv = build_feature_vector(data)
        result = BuhlmannStraubEngine(k=50.0).calculate_from_features(fv, 0.0263)
        self.assertIn(result.credibility_class, ("Established", "Mature"))
        self.assertGreater(result.confidence, 0.5)

    def test_no_product_decision_fields(self) -> None:
        result = BuhlmannStraubEngine().calculate(
            CredibilityContext(
                exposure=10,
                observation_count=10,
                individual_rate_proxy=0.03,
                collective_rate=0.0263,
            )
        )
        for banned in ("premium", "approved", "benefit", "status"):
            self.assertNotIn(banned, result.metadata)


if __name__ == "__main__":
    unittest.main()
