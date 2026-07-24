"""Tests for motor portfolio prep and modeling workflow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from aic.portfolio_motor import (
    clean_and_engineer,
    live_store_columns,
    run_grouped_cv,
    run_prep,
    temporal_split,
)


def _synthetic_raw() -> pd.DataFrame:
    rows = []
    for pid in range(1, 41):
        for year in range(2015, 2020):
            rows.append(
                {
                    "ID": pid,
                    "Date_start_contract": f"01/01/{year}",
                    "Date_last_renewal": f"01/01/{year}",
                    "Date_next_renewal": f"01/01/{year + 1}",
                    "Date_birth": "01/01/1980",
                    "Date_driving_licence": "01/01/2000",
                    "Distribution_channel": pid % 2,
                    "Seniority": 3,
                    "Policies_in_force": 1,
                    "Max_policies": 2,
                    "Max_products": 1,
                    "Lapse": 0,
                    "Date_lapse": "",
                    "Payment": 0,
                    "Premium": 200.0 + pid + year,
                    "Cost_claims_year": 0,
                    "N_claims_year": 0,
                    "N_claims_history": 0,
                    "R_Claims_history": 0.0,
                    "Type_risk": 1 + (pid % 3),
                    "Area": pid % 2,
                    "Second_driver": 0,
                    "Year_matriculation": 2010,
                    "Power": 80,
                    "Cylinder_capacity": 1400,
                    "Value_vehicle": 10000,
                    "N_doors": 5,
                    "Type_fuel": "P",
                    "Length": 4.0,
                    "Weight": 1100,
                }
            )
    return pd.DataFrame(rows)


class TestPortfolioMotor(unittest.TestCase):
    def test_clean_and_split(self) -> None:
        clean = clean_and_engineer(_synthetic_raw())
        self.assertIn("price", clean.columns)
        self.assertTrue((clean["price"] > 0).all())
        train, valid, holdout, meta = temporal_split(clean, train_end=2016, valid_end=2018, holdout_year=2019)
        self.assertGreater(len(train), 0)
        self.assertGreater(len(holdout), 0)
        self.assertEqual(meta.holdout_year, 2019)

    def test_prep_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            _synthetic_raw().to_csv(raw, sep=";", index=False)
            clean_path = Path(tmp) / "clean.csv"
            splits = Path(tmp) / "splits"
            meta = run_prep(
                raw,
                clean_path=clean_path,
                splits_dir=splits,
                train_end=2016,
                valid_end=2018,
                holdout_year=2019,
            )
            self.assertTrue((splits / "motor_train.csv").is_file())
            self.assertGreater(meta.train_rows, 0)

    def test_grouped_cv_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw.csv"
            _synthetic_raw().to_csv(raw, sep=";", index=False)
            splits = Path(tmp) / "splits"
            run_prep(raw, clean_path=Path(tmp) / "c.csv", splits_dir=splits)
            results = run_grouped_cv(
                splits / "motor_train.csv",
                n_folds=3,
                min_level_count=1,
                sample=120,
            )
            self.assertEqual(len(results), 3)
            self.assertTrue(all(np.isfinite(r.mean_deviance) for r in results))

    def test_live_store_columns_no_leakage(self) -> None:
        clean = clean_and_engineer(_synthetic_raw())
        store = live_store_columns(clean)
        self.assertNotIn("claim_cost", store.columns)
        self.assertNotIn("claim_count", store.columns)
        self.assertIn("price", store.columns)


if __name__ == "__main__":
    unittest.main()
