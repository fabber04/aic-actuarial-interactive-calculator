"""API dual-run: Platform v2 underwrite + legacy v1."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from aic.api.ct_flex import create_app
from aic.orchestrator import PLATFORM_MODEL_VERSION, AICPlatform, quote_to_ctflex_underwrite


class TestCtFlexApiV2(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(create_app())

    def test_health_reports_platform(self) -> None:
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["modelVersion"], PLATFORM_MODEL_VERSION)
        self.assertEqual(body["underwriteEngine"], "aic.orchestrator.AICPlatform")

    def test_underwrite_income_uses_orchestrator(self) -> None:
        r = self.client.post(
            "/ct-flex/underwrite",
            json={
                "transactionCount": 8,
                "product": "income",
                "occupation": "Courier",
                "platform": "Bolt",
                "transactions": [10, 12, 8, 15, 14, 11, 9, 13],
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["engine"], "aic.orchestrator.AICPlatform")
        self.assertEqual(body["modelVersion"], PLATFORM_MODEL_VERSION)
        self.assertIn(body["decision"], ("Approved", "Refer", "Decline"))
        self.assertGreater(body["premiumRate"], 0)
        self.assertIn("explanation", body)

    def test_underwrite_dual_attaches_legacy(self) -> None:
        r = self.client.post(
            "/ct-flex/underwrite?dual=1",
            json={"transactionCount": 8, "product": "income", "occupation": "Courier"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("legacyCompare", body)
        self.assertEqual(body["legacyCompare"]["engine"], "aic.engine_model.CredibilityParams")

    def test_underwrite_v1_legacy(self) -> None:
        r = self.client.post(
            "/ct-flex/underwrite/v1",
            json={"transactionCount": 8, "product": "income"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["engine"], "aic.engine_model.CredibilityParams")

    def test_health_life_falls_back_to_v1(self) -> None:
        r = self.client.post(
            "/ct-flex/underwrite",
            json={"transactionCount": 8, "product": "health"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["enginePath"], "v1-fallback-non-income")

    def test_consent_rejected(self) -> None:
        r = self.client.post(
            "/ct-flex/underwrite",
            json={"transactionCount": 8, "product": "income", "ecocashConsent": False},
        )
        self.assertEqual(r.status_code, 400)

    def test_quote_raw(self) -> None:
        r = self.client.post(
            "/ct-flex/quote",
            json={"transactionCount": 8, "product": "income", "occupation": "Courier"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("expected_loss", r.json())


class TestQuoteMapper(unittest.TestCase):
    def test_mapper_shape(self) -> None:
        quote = AICPlatform().quote_ctflex(
            {
                "occupation": "Courier",
                "transaction_count": 8,
                "transactions": [10, 12, 8, 15, 14, 11, 9, 13],
            }
        )
        payload = quote_to_ctflex_underwrite(quote)
        for key in (
            "approved",
            "riskRating",
            "premiumRate",
            "coverageUsd",
            "credibilityZ",
            "classRate",
            "factors",
            "engine",
        ):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
