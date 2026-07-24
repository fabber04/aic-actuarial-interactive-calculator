"""Tests for core.risk_engine Gamma GLM wrapper (does not move fremtpl_glm)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from aic.contracts.feature_vector import FeatureVector
from aic.core.credibility.base import CredibilityResult
from aic.core.risk_engine import GammaGLMRiskEngine, GlmPredictor
from aic.fremtpl_glm import PRICE_TARGET, LivePricingEngine


def _pricing_record(price: float = 250.0) -> dict:
    return {
        PRICE_TARGET: price,
        "Area": "A",
        "Region": "R1",
        "VehBrand": "B1",
        "VehGas": "R",
        "VehPower": 5,
        "VehAge": 1,
        "DrivAge": 40,
        "BonusMalus": 50,
        "Density": 120,
    }


def _cred(z: float = 0.5) -> CredibilityResult:
    return CredibilityResult(
        credibility_factor=z,
        adjusted_risk=200.0,
        individual_rate=220.0,
        collective_rate=180.0,
    )


class TestGammaGLMRiskEngine(unittest.TestCase):
    def test_predictor_requires_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pred = GlmPredictor(
                store_path=Path(tmp) / "store.csv",
                model_dir=Path(tmp) / "models",
            )
            with self.assertRaises(RuntimeError):
                pred.predict_records(_pricing_record())

    def test_risk_engine_scores_after_retrain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "store.csv"
            models = Path(tmp) / "models"
            engine = LivePricingEngine(store, models, min_level_count=1)
            rows = pd.DataFrame([_pricing_record(200 + i * 10) for i in range(40)])
            out = engine.append_and_retrain(rows)
            self.assertTrue(out["retrain"]["success"])

            risk_engine = GammaGLMRiskEngine(engine=engine)
            record = {k: v for k, v in _pricing_record(300.0).items() if k != PRICE_TARGET}
            result = risk_engine.predict_record(record, _cred(0.6))
            self.assertEqual(result.model_name, "gamma_glm_price_v1")
            self.assertGreater(result.expected_loss, 0)
            self.assertAlmostEqual(result.credibility_z, 0.6)

            # FeatureVector path (numeric-only subset still needs full schema —
            # pass full record via features as floats where possible + cats as-is
            # by using predict_record for categoricals; FeatureVector holds floats only
            # so we exercise predict() with a numeric-only mock by going through predictor
            # with a patched features dict via predict_record above.
            fv = FeatureVector(product="motor", features={})
            with self.assertRaises(ValueError):
                risk_engine.predict(fv, _cred())


if __name__ == "__main__":
    unittest.main()
