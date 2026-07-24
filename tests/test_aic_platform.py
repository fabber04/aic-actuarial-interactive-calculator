"""Smoke tests for AIC v2 platform skeleton."""

from __future__ import annotations

import unittest

from aic.orchestrator import AICPlatform
from aic.products.ctflex import CTFlexAdapter


class TestAICPlatform(unittest.TestCase):
    def test_adapter_hides_platform(self) -> None:
        data = CTFlexAdapter().transform(
            {
                "occupation": "Driver",
                "platform": "Bolt",
                "transactions": [
                    {"date": "2026-07-01", "amount": 15},
                    {"date": "2026-07-02", "amount": 20},
                ],
            }
        )
        self.assertEqual(data.product, "ctflex_income")
        self.assertEqual(len(data.observations), 2)
        self.assertEqual(data.observations[0]["income"], 15.0)

    def test_quote_ctflex_end_to_end(self) -> None:
        out = AICPlatform().quote_ctflex(
            {
                "occupation": "Courier",
                "platform": "Bolt",
                "transaction_count": 8,
                "transactions": [10, 12, 8, 15, 14, 11, 9, 13],
            }
        )
        self.assertIn(out["decision"], ("Approved", "Refer", "Decline"))
        self.assertGreater(out["premium_rate"], 0)
        self.assertGreaterEqual(out["benefit"], 0)
        self.assertIn("explanation", out)
        self.assertIn("credibility_z", out)
        self.assertIn("expected_loss", out)
        self.assertEqual(out["credibility_class"], "Initial")
        self.assertTrue(out["credibility_drivers"])
        self.assertEqual(out["credibility_metadata"]["method"], "Bühlmann–Straub")

    def test_thin_history_can_refer(self) -> None:
        out = AICPlatform().quote_ctflex(
            {"occupation": "Courier", "transaction_count": 2, "transactions": [5, 6]}
        )
        self.assertIn(out["decision"], ("Approved", "Refer"))
        self.assertLess(out["credibility_z"], 0.5)

    def test_underwrite_api_shape(self) -> None:
        payload = AICPlatform().underwrite_ctflex_api(
            {"occupation": "Courier", "transaction_count": 8, "transactions": [10, 12, 8]}
        )
        self.assertEqual(payload["engine"], "aic.orchestrator.AICPlatform")
        self.assertIn("premiumRate", payload)

    def test_consent_required(self) -> None:
        with self.assertRaises(ValueError):
            AICPlatform().quote_ctflex(
                {"occupation": "Courier", "transaction_count": 8, "ecocash_consent": False}
            )


if __name__ == "__main__":
    unittest.main()
