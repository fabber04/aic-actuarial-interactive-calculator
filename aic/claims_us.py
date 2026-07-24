"""
US synthetic auto claims CSV -> clean features, splits, fit/deploy via shared pricing engine.

This is a separate model from the motor portfolio (different population and schema).
Target: policy_annual_premium (strictly positive premium proxy).

Usage:
  python fremtpl_glm.py claims-prep
  python fremtpl_glm.py claims-fit
  python fremtpl_glm.py claims-deploy
  python fremtpl_glm.py serve --profile claims
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from aic.fremtpl_glm import (
    CLAIMS_PROFILE,
    LivePricingEngine,
    PricingDataStore,
    PricingPreprocessor,
    SerializablePriceModel,
    _gamma_mean_deviance,
    collapse_rare_levels,
    fit_price_glm,
)

CLAIMS_DIR = Path("Datasets")
RAW_CSV = CLAIMS_DIR / "insurance_claims.csv"
CLEAN_CSV = CLAIMS_DIR / "claims_clean.csv"
SPLITS_DIR = CLAIMS_DIR / "claims_splits"
FIT_SUMMARY = CLAIMS_DIR / "claims_fit_summary.json"

CLAIMS_STORE = Path("pricing_data") / "claims_pricing_store.csv"
CLAIMS_MODEL_DIR = Path("pricing_models") / "claims"
CLAIMS_REJECTED = Path("pricing_data") / "claims_rejected.csv"

CLAIMS_CAT_COLS = list(CLAIMS_PROFILE.categorical_cols)

# Bind years in file ~1990-2014; use bind year for temporal split
DEFAULT_TRAIN_END = 2011
DEFAULT_VALID_YEAR = 2012
DEFAULT_HOLDOUT_YEAR = 2013


@dataclass
class ClaimsSplitMeta:
    train_end: int
    valid_year: int
    holdout_year: int
    train_rows: int
    valid_rows: int
    holdout_rows: int
    bind_year_min: int
    bind_year_max: int


def load_raw_claims(path: Path = RAW_CSV) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, na_values=["?", ""], low_memory=False)
    # drop empty trailing column if present
    drop_cols = [c for c in df.columns if c.startswith("_") or c.strip() == ""]
    if drop_cols:
        df = df.drop(columns=drop_cols, errors="ignore")
    return df


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["policy_bind_date"] = pd.to_datetime(work["policy_bind_date"], errors="coerce")
    work["incident_date"] = pd.to_datetime(work["incident_date"], errors="coerce")
    work["price"] = pd.to_numeric(work["policy_annual_premium"], errors="coerce")
    work = work[work["price"].notna() & (work["price"] > 0)].copy()

    work["bind_year"] = work["policy_bind_date"].dt.year
    work["driver_age"] = pd.to_numeric(work["age"], errors="coerce").clip(16, 99)
    ref_year = work["incident_date"].dt.year.fillna(work["bind_year"])
    auto_year = pd.to_numeric(work["auto_year"], errors="coerce")
    work["vehicle_age"] = (ref_year - auto_year).clip(0, 50)

    work["months_as_customer"] = pd.to_numeric(work["months_as_customer"], errors="coerce").fillna(0)
    work["policy_deductable"] = pd.to_numeric(work["policy_deductable"], errors="coerce").fillna(0)
    work["umbrella_limit"] = pd.to_numeric(work["umbrella_limit"], errors="coerce").fillna(0)
    work["total_claim_amount"] = pd.to_numeric(work["total_claim_amount"], errors="coerce").fillna(0)

    for col in CLAIMS_CAT_COLS:
        if col in work.columns:
            work[col] = work[col].astype(str).replace({"nan": "Missing"}).fillna("Missing")

    return work


def temporal_split_claims(
    df: pd.DataFrame,
    *,
    train_end: int = DEFAULT_TRAIN_END,
    valid_year: int = DEFAULT_VALID_YEAR,
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, ClaimsSplitMeta]:
    train = df[df["bind_year"] <= train_end].copy()
    valid = df[df["bind_year"] == valid_year].copy()
    holdout = df[df["bind_year"] == holdout_year].copy()
    meta = ClaimsSplitMeta(
        train_end=train_end,
        valid_year=valid_year,
        holdout_year=holdout_year,
        train_rows=len(train),
        valid_rows=len(valid),
        holdout_rows=len(holdout),
        bind_year_min=int(df["bind_year"].min()),
        bind_year_max=int(df["bind_year"].max()),
    )
    return train, valid, holdout, meta


def prepare_claims_df(df: pd.DataFrame, min_level_count: int) -> pd.DataFrame:
    out = collapse_rare_levels(df, CLAIMS_CAT_COLS, min_level_count)
    for col in CLAIMS_CAT_COLS:
        if col in out.columns:
            out[col] = out[col].astype(str).fillna("Missing")
    for col in ("driver_age", "vehicle_age", "months_as_customer", "policy_deductable", "umbrella_limit"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    return out


def read_claims_csv(path: Path) -> pd.DataFrame:
    dtype = {c: str for c in CLAIMS_CAT_COLS}
    return pd.read_csv(path, dtype=dtype, low_memory=False)


def live_store_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["policy_number", "bind_year", CLAIMS_PROFILE.target_col, *CLAIMS_PROFILE.feature_cols]
    return df[[c for c in cols if c in df.columns]].copy()


def run_prep(
    raw_path: Path = RAW_CSV,
    *,
    clean_path: Path = CLEAN_CSV,
    splits_dir: Path = SPLITS_DIR,
    train_end: int = DEFAULT_TRAIN_END,
    valid_year: int = DEFAULT_VALID_YEAR,
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> ClaimsSplitMeta:
    raw = load_raw_claims(raw_path)
    clean = clean_and_engineer(raw)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(clean_path, index=False)

    train, valid, holdout, meta = temporal_split_claims(
        clean, train_end=train_end, valid_year=valid_year, holdout_year=holdout_year
    )
    splits_dir.mkdir(parents=True, exist_ok=True)
    train.to_csv(splits_dir / "claims_train.csv", index=False)
    valid.to_csv(splits_dir / "claims_valid.csv", index=False)
    holdout.to_csv(splits_dir / "claims_holdout.csv", index=False)
    (splits_dir / "split_meta.json").write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")
    return meta


def run_fit(
    *,
    splits_dir: Path = SPLITS_DIR,
    min_level_count: int = CLAIMS_PROFILE.min_level_count,
) -> Dict[str, Any]:
    train = read_claims_csv(splits_dir / "claims_train.csv")
    valid = read_claims_csv(splits_dir / "claims_valid.csv")
    holdout = read_claims_csv(splits_dir / "claims_holdout.csv")
    fit_df = pd.concat([train, valid], ignore_index=True)

    profile = CLAIMS_PROFILE
    cols = [profile.target_col, *profile.feature_cols]
    prep = PricingPreprocessor(profile=profile, min_level_count=min_level_count)
    glm = fit_price_glm(fit_df[cols], prep, formula=profile.formula)
    model = SerializablePriceModel.from_glm(glm)

    work_ho = prep.transform(holdout[cols]).copy()
    work_ho[profile.target_col] = holdout[profile.target_col].values
    import patsy

    y_ho, x_ho = patsy.dmatrices(profile.formula, work_ho, return_type="dataframe", NA_action="drop")
    x_ho = x_ho.reindex(columns=model.exog_names, fill_value=0)
    preds = np.exp(np.dot(x_ho.values, model.params))
    deviance = _gamma_mean_deviance(np.asarray(y_ho).ravel(), preds)

    out = holdout.loc[y_ho.index].copy()
    out["predicted_price"] = preds
    out["prediction_error"] = out["price"] - out["predicted_price"]
    scored = CLAIMS_DIR / "claims_holdout_scored.csv"
    out.to_csv(scored, index=False)

    # total_claim_amount retained in scored file for comparison only
    summary = {
        "holdout_rows": len(holdout),
        "scored_rows": len(out),
        "premium_mean_deviance": deviance,
        "holdout_mean_actual_premium": float(out["price"].mean()),
        "holdout_mean_predicted_premium": float(np.mean(preds)),
        "holdout_mean_claim_amount": float(out["total_claim_amount"].mean()),
        "scored_holdout": str(scored.resolve()),
    }
    FIT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_deploy(
    *,
    splits_dir: Path = SPLITS_DIR,
    store_path: Path = CLAIMS_STORE,
    model_dir: Path = CLAIMS_MODEL_DIR,
    min_level_count: int = CLAIMS_PROFILE.min_level_count,
) -> Dict[str, Any]:
    train = read_claims_csv(splits_dir / "claims_train.csv")
    valid = read_claims_csv(splits_dir / "claims_valid.csv")
    combined = prepare_claims_df(pd.concat([train, valid], ignore_index=True), min_level_count)
    payload = live_store_columns(combined)

    store = PricingDataStore(store_path)
    if store.path.is_file():
        store.path.unlink()
    store.append(payload)

    engine = LivePricingEngine(
        store_path=store_path,
        model_dir=model_dir,
        rejected_path=CLAIMS_REJECTED,
        profile=CLAIMS_PROFILE,
        min_level_count=min_level_count,
    )
    outcome = engine.retrain()
    return {
        "store": str(store.path.resolve()),
        "model_dir": str(model_dir.resolve()),
        "rows": len(payload),
        "retrain": asdict(outcome),
    }


def score_file(
    input_csv: Path,
    output_csv: Path,
    *,
    model_dir: Path = CLAIMS_MODEL_DIR,
) -> int:
    """Score any CSV that can be engineered via clean_and_engineer (e.g. full insurance_claims.csv)."""
    from aic.fremtpl_glm import load_model_bundle, LATEST_MODEL_NAME

    raw = load_raw_claims(input_csv)
    clean = clean_and_engineer(raw)
    clean = prepare_claims_df(clean, CLAIMS_PROFILE.min_level_count)
    cols = [CLAIMS_PROFILE.target_col, *CLAIMS_PROFILE.feature_cols]
    bundle = load_model_bundle(model_dir / LATEST_MODEL_NAME)
    prepared = bundle.preprocessor.transform(clean[cols])
    preds = bundle.model.predict(prepared, target_col=CLAIMS_PROFILE.target_col)
    out = clean.copy()
    out["predicted_price"] = preds
    if CLAIMS_PROFILE.target_col in out.columns:
        out["prediction_error"] = out[CLAIMS_PROFILE.target_col] - out["predicted_price"]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False)
    return len(out)
