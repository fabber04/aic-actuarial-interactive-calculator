"""Benchmark tests — actuarial systems comparison, not language comparison."""

from __future__ import annotations

import unittest

from aic.benchmark.personas import build_personas
from aic.benchmark.runner import run_benchmark


class TestPrototypeVsAicBenchmark(unittest.TestCase):
    def test_four_personas(self) -> None:
        result = run_benchmark()
        self.assertEqual(len(result["personas"]), 4)
        self.assertIn("income_reliability_finding", result)

    def test_new_worker_aic_refers(self) -> None:
        row = next(r for r in run_benchmark()["personas"] if r["persona"]["id"] == "new_worker")
        self.assertEqual(row["aic"]["decision"], "Refer")
        self.assertLess(row["aic"]["credibility_z"], 0.2)

    def test_established_approved(self) -> None:
        row = next(
            r for r in run_benchmark()["personas"] if r["persona"]["id"] == "established_driver"
        )
        self.assertEqual(row["aic"]["decision"], "Approved")
        self.assertGreater(row["aic"]["credibility_z"], 0.5)

    def test_income_reliability_contribution(self) -> None:
        finding = run_benchmark()["income_reliability_finding"]
        self.assertTrue(finding["same_transaction_count"])
        self.assertTrue(finding["prototype_premium_rate_identical"])
        self.assertTrue(finding["aic_distinguishes_reliability"])

    def test_aic_has_pricing_layers(self) -> None:
        row = next(
            r for r in run_benchmark()["personas"] if r["persona"]["id"] == "established_driver"
        )
        self.assertIsNotNone(row["aic"]["expected_loss"])
        self.assertIsNotNone(row["aic"]["technical_premium"])
        self.assertTrue(row["aic"]["governance_metadata"])
        self.assertGreater(row["explainability_coverage"]["aic"], row["explainability_coverage"]["prototype"])

    def test_persona_catalog(self) -> None:
        ids = {p.id for p in build_personas()}
        self.assertEqual(
            ids,
            {"new_worker", "established_driver", "volatile_income", "high_income_stable"},
        )


if __name__ == "__main__":
    unittest.main()
