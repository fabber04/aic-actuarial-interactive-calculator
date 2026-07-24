"""Actuarial Knowledge Layer unit tests."""

from __future__ import annotations

import unittest

from aic.contracts.data_objects import StandardizedData
from aic.features import build_feature_groups, build_feature_vector
from aic.features.financial import income_stability, income_volatility
from aic.features.occupational import OccupationRiskTable, occupation_risk_score
from aic.products.ctflex.features import generate_ctflex_features


class TestFinancialConcepts(unittest.TestCase):
    def test_stability_inverse_volatility(self) -> None:
        vals = [10.0, 12.0, 11.0, 10.5, 11.5]
        self.assertAlmostEqual(income_stability(vals) + income_volatility(vals), 1.0, places=4)

    def test_empty_series(self) -> None:
        self.assertEqual(income_stability([]), 0.4)


class TestOccupationTable(unittest.TestCase):
    def test_table_not_hardcoded_in_call(self) -> None:
        table = OccupationRiskTable(scores={"driver": 0.58}, default_score=0.5, version="test")
        self.assertAlmostEqual(occupation_risk_score("driver", table), 0.58)
        self.assertAlmostEqual(occupation_risk_score("courier", table), 0.5)

    def test_override_without_logic_change(self) -> None:
        base = OccupationRiskTable()
        revised = base.with_overrides({"driver": 0.58})
        self.assertAlmostEqual(revised.score("driver"), 0.58)
        self.assertAlmostEqual(base.score("driver"), 0.60)


class TestAggregator(unittest.TestCase):
    def test_groups_then_flatten(self) -> None:
        data = StandardizedData(
            product="ctflex_income",
            observations=[{"income": 10}, {"income": 12}, {"income": 8}, {"income": 15}],
            context={"occupation": "Courier", "platform": "Bolt", "transaction_count": 4},
        )
        groups = build_feature_groups(data)
        self.assertIn("financial", groups)
        self.assertIn("behavioural", groups)
        self.assertIn("occupational", groups)
        self.assertIn("environmental", groups)
        self.assertIn("income_stability", groups["financial"])
        self.assertIn("occupation_risk", groups["occupational"])

        fv = build_feature_vector(data)
        self.assertIn("income_stability", fv.features)
        self.assertIn("financial_index", fv.features)
        self.assertEqual(fv.metadata.get("feature_version"), "1.0.0")
        self.assertIn("generator", fv.metadata)
        self.assertIsNotNone(fv.feature_groups)
        self.assertIn("group_scores", fv.metadata)

    def test_no_pricing_keys_in_akl(self) -> None:
        data = StandardizedData(
            product="demo",
            observations=[{"income": 20}, {"income": 22}],
            context={"occupation": "Vendor"},
        )
        fv = build_feature_vector(data)
        for banned in ("premium", "premium_rate", "reserve", "glm", "ibnr"):
            self.assertTrue(all(banned not in k.lower() for k in fv.features))


class TestCtFlexUsesAkl(unittest.TestCase):
    def test_ctflex_adds_credibility_proxy_only(self) -> None:
        data = StandardizedData(
            product="ctflex_income",
            observations=[{"income": x} for x in [10, 12, 8, 15, 14, 11, 9, 13]],
            context={"occupation": "Courier", "transaction_count": 8, "platform": "Bolt"},
        )
        fv = generate_ctflex_features(data)
        self.assertIn("individual_rate_proxy", fv.features)
        self.assertIn("income_stability", fv.features)
        self.assertIn("activity_consistency", fv.features)
        self.assertEqual(fv.feature_groups["occupational"]["occupation_risk"], fv.features["occupation_risk"])


if __name__ == "__main__":
    unittest.main()
