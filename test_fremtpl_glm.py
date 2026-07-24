"""Smoke tests for fremtpl_glm (small synthetic sample)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import pandas as pd

from fremtpl_glm import (
    PRICE_TARGET,
    LivePricingEngine,
    PRICING_FEATURE_COLS,
    load_freq_csv,
    run_glm_pricing,
    validate_price_records,
)


def _tiny_freq() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "IDpol": [1, 2, 3, 4, 5, 6],
            "ClaimNb": [0, 1, 0, 2, 1, 0],
            "Exposure": [1.0, 0.5, 1.0, 0.8, 0.6, 1.2],
            "Area": ["A", "A", "B", "B", "A", "B"],
            "VehPower": [5, 6, 7, 5, 6, 7],
            "VehAge": [0, 1, 2, 0, 1, 2],
            "DrivAge": [30, 45, 55, 22, 38, 60],
            "BonusMalus": [50, 58, 50, 70, 50, 64],
            "VehBrand": ["B1", "B1", "B2", "B2", "B1", "B2"],
            "VehGas": ["R", "D", "R", "D", "R", "D"],
            "Density": [100, 200, 300, 150, 250, 400],
            "Region": ["R1", "R1", "R2", "R2", "R1", "R2"],
        }
    )


class TestFremtplGLM(unittest.TestCase):
    def test_run_on_tiny_sample(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "tiny_freq.csv"
            _tiny_freq().to_csv(p, index=False)
            run = run_glm_pricing(str(p), out_dir=tmp, min_level_count=1)
            self.assertEqual(len(run.df_scored), 6)
            self.assertIn("GLM_Indicated_Premium", run.df_scored.columns)
            self.assertTrue((run.df_scored["GLM_Indicated_Premium"] > 0).all())
            self.assertTrue((Path(tmp) / "tiny_freq_glm_priced.csv").is_file())

    def test_load_requires_columns(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            pd.DataFrame({"a": [1]}).to_csv(f.name, index=False)
            with self.assertRaises(ValueError):
                load_freq_csv(f.name)


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


class TestLivePricingEngine(unittest.TestCase):
    def test_validate_rejects_non_positive_price(self) -> None:
        bad = pd.DataFrame([{**_pricing_record(), PRICE_TARGET: 0}])
        result = validate_price_records(bad)
        self.assertTrue(result.accepted.empty)
        self.assertEqual(len(result.rejected), 1)

    def test_append_retrain_predict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "store.csv"
            models = Path(tmp) / "models"
            engine = LivePricingEngine(store, models, min_level_count=1)
            rows = pd.DataFrame([_pricing_record(200 + i * 10) for i in range(40)])
            out = engine.append_and_retrain(rows)
            self.assertGreater(out["appended"], 0)
            self.assertTrue(out["retrain"]["success"])
            self.assertTrue(engine.has_model())
            prices = engine.predict_price(_pricing_record(300.0))
            self.assertEqual(len(prices), 1)
            self.assertGreater(prices[0], 0)

    def test_retrain_failure_keeps_prior_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "store.csv"
            models = Path(tmp) / "models"
            engine = LivePricingEngine(store, models, min_level_count=1)
            engine.append_and_retrain(pd.DataFrame([_pricing_record() for _ in range(30)]))
            v1 = engine.metrics.active_version_id
            pd.DataFrame([{PRICE_TARGET: -1, **{c: 1 for c in PRICING_FEATURE_COLS}}]).to_csv(
                store, index=False
            )
            outcome = engine.retrain()
            self.assertFalse(outcome.success)
            self.assertEqual(engine.metrics.active_version_id, v1)


if __name__ == "__main__":
    unittest.main()
