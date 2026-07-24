"""Smoke tests for the CT Flex product slice of AIC."""

from __future__ import annotations

import unittest

from aic.ct_flex_product import (
    UnderwritingRequest,
    credibility_z,
    portfolio_metrics,
    trip_premium,
    underwrite,
)
from aic.engine_model import CredibilityParams


class TestCtFlexUsesEngine(unittest.TestCase):
    def test_credibility_matches_engine_params(self) -> None:
        z = credibility_z(8, k=50)
        expected = CredibilityParams(full_credibility_claims=1082, buhlmann_k=50.0).credibility(8.0)
        self.assertAlmostEqual(z, round(expected, 4), places=4)
        self.assertAlmostEqual(z, 8 / 58, places=4)

    def test_underwrite_income(self) -> None:
        result = underwrite(
            UnderwritingRequest(
                transaction_count=8,
                product="income",
                occupation="Courier",
                platform="Bolt",
                national_id="63-1234567-A12",
                full_name="Tafadzwa Moyo",
            )
        )
        self.assertTrue(result.approved)
        self.assertEqual(result.risk_rating, "Moderate")
        self.assertAlmostEqual(result.credibility_z, 0.14, places=2)
        self.assertGreater(result.premium_rate, result.class_rate)
        self.assertEqual(result.engine, "aic.engine_model.CredibilityParams")
        self.assertEqual(len(result.factors), 6)

    def test_consent_required(self) -> None:
        with self.assertRaises(ValueError):
            underwrite(UnderwritingRequest(transaction_count=8, ecocash_consent=False))

    def test_trip_paye(self) -> None:
        trip = trip_premium(8.0, 0.03)
        self.assertEqual(trip.premium_usd, 0.24)
        self.assertEqual(trip.net_usd, 7.76)

    def test_portfolio(self) -> None:
        p = portfolio_metrics(1247)
        self.assertEqual(p.risk_pool_size, 1247)
        self.assertGreater(p.solvency_buffer, 1.0)


if __name__ == "__main__":
    unittest.main()
