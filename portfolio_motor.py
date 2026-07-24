"""
Motor portfolio workflow: clean semicolon CSV, temporal splits, grouped CV, batch GLM, live deploy.

Usage (via fremtpl_glm.py CLI):
  python fremtpl_glm.py portfolio-prep
  python fremtpl_glm.py portfolio-cv --folds 5
  python fremtpl_glm.py portfolio-fit
  python fremtpl_glm.py portfolio-deploy
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from fremtpl_glm import (
    PORTFOLIO_PROFILE,
    LivePricingEngine,
    PricingDataStore,
    PricingPreprocessor,
    SerializablePriceModel,
    _gamma_mean_deviance,
    collapse_rare_levels,
    fit_frequency_glm,
    fit_price_glm,
    fit_severity_glm,
    predict_on_data,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

PORTFOLIO_DIR = Path("Datasets") / "Dataset of an actual motor vehicle insurance portfolio"
RAW_CSV = PORTFOLIO_DIR / "Motor vehicle insurance data.csv"
CLEAN_CSV = PORTFOLIO_DIR / "motor_clean.csv"
SPLITS_DIR = PORTFOLIO_DIR / "splits"
SPLIT_META = SPLITS_DIR / "split_meta.json"
CV_RESULTS = PORTFOLIO_DIR / "portfolio_cv_results.json"
FIT_SUMMARY = PORTFOLIO_DIR / "portfolio_fit_summary.json"

PORTFOLIO_STORE = Path("pricing_data") / "portfolio_pricing_store.csv"
PORTFOLIO_MODEL_DIR = Path("pricing_models") / "portfolio"
PORTFOLIO_REJECTED = Path("pricing_data") / "portfolio_rejected.csv"

DATE_COLS = (
    "Date_start_contract",
    "Date_last_renewal",
    "Date_next_renewal",
    "Date_birth",
    "Date_driving_licence",
    "Date_lapse",
)
PORTFOLIO_CAT_COLS = list(PORTFOLIO_PROFILE.categorical_cols)

PORTFOLIO_FREQ_FORMULA = (
    "ClaimNb ~ C(Type_risk) + C(Area) + C(Distribution_channel) + C(Type_fuel) + "
    "C(Second_driver) + Power + driver_age + vehicle_age + Value_vehicle + "
    "Seniority + R_Claims_history"
)
PORTFOLIO_SEV_FORMULA = (
    "ClaimAmount ~ C(Type_risk) + C(Area) + C(Distribution_channel) + C(Type_fuel) + "
    "C(Second_driver) + Power + driver_age + vehicle_age + Value_vehicle + "
    "Seniority + R_Claims_history"
)

DEFAULT_TRAIN_END = 2016
DEFAULT_VALID_END = 2017
DEFAULT_HOLDOUT_YEAR = 2018


@dataclass
class SplitMeta:
    train_end: int
    valid_end: int
    holdout_year: int
    train_rows: int
    valid_rows: int
    holdout_rows: int
    term_year_min: int
    term_year_max: int


@dataclass
class CVFoldResult:
    fold: int
    train_rows: int
    valid_rows: int
    mean_deviance: float


def load_raw_motor_csv(path: Path = RAW_CSV) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_csv(
        path,
        sep=";",
        na_values=["NA", ""],
        low_memory=False,
    )


def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in DATE_COLS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], dayfirst=True, errors="coerce")
    return out


def clean_and_engineer(
    df: pd.DataFrame,
    *,
    in_force_only: bool = False,
) -> pd.DataFrame:
    """Build term-level modeling frame with engineered ages and targets."""
    work = _parse_dates(df)
    work["Premium"] = pd.to_numeric(work["Premium"], errors="coerce")
    work = work[work["Premium"].notna() & (work["Premium"] > 0)].copy()

    if in_force_only and "Lapse" in work.columns:
        work = work[work["Lapse"].fillna(0).astype(int) == 0].copy()

    renewal = work["Date_last_renewal"]
    work["term_year"] = renewal.dt.year
    work["driver_age"] = ((renewal - work["Date_birth"]).dt.days / 365.25).clip(lower=16, upper=99)
    work["vehicle_age"] = (
        work["term_year"] - pd.to_numeric(work["Year_matriculation"], errors="coerce")
    ).clip(lower=0, upper=50)

    work["price"] = work["Premium"]
    work["exposure"] = 1.0
    work["claim_count"] = pd.to_numeric(work["N_claims_year"], errors="coerce").fillna(0).clip(lower=0)
    work["claim_cost"] = pd.to_numeric(work["Cost_claims_year"], errors="coerce").fillna(0).clip(lower=0)

    for col in ("Power", "Value_vehicle", "Seniority", "R_Claims_history"):
        if col in work.columns:
            work[col] = pd.to_numeric(work[col], errors="coerce")

    for col in PORTFOLIO_CAT_COLS:
        if col in work.columns:
            work[col] = (
                work[col].astype(str).replace({"nan": "Missing", "None": "Missing"}).fillna("Missing")
            )

    return work


def read_portfolio_csv(path: Path) -> pd.DataFrame:
    dtype = {c: str for c in PORTFOLIO_CAT_COLS}
    return pd.read_csv(path, na_values=["NA", ""], low_memory=False, dtype=dtype)


def temporal_split(
    df: pd.DataFrame,
    *,
    train_end: int = DEFAULT_TRAIN_END,
    valid_end: int = DEFAULT_VALID_END,
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, SplitMeta]:
    if "term_year" not in df.columns:
        raise ValueError("DataFrame must include term_year; run clean_and_engineer first")
    train = df[df["term_year"] <= train_end].copy()
    valid = df[df["term_year"] == valid_end].copy()
    holdout = df[df["term_year"] == holdout_year].copy()
    meta = SplitMeta(
        train_end=train_end,
        valid_end=valid_end,
        holdout_year=holdout_year,
        train_rows=len(train),
        valid_rows=len(valid),
        holdout_rows=len(holdout),
        term_year_min=int(df["term_year"].min()),
        term_year_max=int(df["term_year"].max()),
    )
    return train, valid, holdout, meta


def prepare_portfolio_df(df: pd.DataFrame, min_level_count: int) -> pd.DataFrame:
    out = collapse_rare_levels(df, PORTFOLIO_CAT_COLS, min_level_count)
    for col in PORTFOLIO_CAT_COLS:
        if col in out.columns:
            out[col] = out[col].astype(str).fillna("Missing")
    for col in ("Power", "driver_age", "vehicle_age", "Value_vehicle", "Seniority", "R_Claims_history"):
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    return out


def live_store_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Features + price for live store (no same-term loss outcomes)."""
    cols = ["ID", "term_year", PORTFOLIO_PROFILE.target_col, *PORTFOLIO_PROFILE.feature_cols]
    return df[[c for c in cols if c in df.columns]].copy()


def run_prep(
    raw_path: Path = RAW_CSV,
    *,
    clean_path: Path = CLEAN_CSV,
    splits_dir: Path = SPLITS_DIR,
    train_end: int = DEFAULT_TRAIN_END,
    valid_end: int = DEFAULT_VALID_END,
    holdout_year: int = DEFAULT_HOLDOUT_YEAR,
    in_force_only: bool = False,
) -> SplitMeta:
    raw = load_raw_motor_csv(raw_path)
    clean = clean_and_engineer(raw, in_force_only=in_force_only)
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(clean_path, index=False)

    train, valid, holdout, meta = temporal_split(
        clean, train_end=train_end, valid_end=valid_end, holdout_year=holdout_year
    )
    splits_dir.mkdir(parents=True, exist_ok=True)
    train.to_csv(splits_dir / "motor_train.csv", index=False)
    valid.to_csv(splits_dir / "motor_valid.csv", index=False)
    holdout.to_csv(splits_dir / "motor_holdout.csv", index=False)
    (splits_dir / "split_meta.json").write_text(
        json.dumps(asdict(meta), indent=2), encoding="utf-8"
    )
    return meta


def _grouped_folds(ids: np.ndarray, n_splits: int, seed: int) -> List[np.ndarray]:
    unique = np.array(sorted(set(ids)))
    rng = np.random.default_rng(seed)
    rng.shuffle(unique)
    return [a for a in np.array_split(unique, n_splits) if len(a)]


def run_grouped_cv(
    train_path: Path = SPLITS_DIR / "motor_train.csv",
    *,
    n_folds: int = 5,
    seed: int = 42,
    min_level_count: int = PORTFOLIO_PROFILE.min_level_count,
    sample: Optional[int] = None,
) -> List[CVFoldResult]:
    """GroupKFold on policy ID for Gamma premium model."""
    df = read_portfolio_csv(train_path)
    if sample and len(df) > sample:
        df = df.sample(n=sample, random_state=seed)
    if "ID" not in df.columns:
        raise ValueError("train split must contain ID column")

    profile = PORTFOLIO_PROFILE
    feature_cols = [profile.target_col, *profile.feature_cols]
    folds = _grouped_folds(df["ID"].values, n_folds, seed)
    results: List[CVFoldResult] = []

    for i, valid_ids in enumerate(folds):
        valid_mask = df["ID"].isin(valid_ids)
        valid_df = df.loc[valid_mask]
        train_df = df.loc[~valid_mask]
        prep = PricingPreprocessor(profile=profile, min_level_count=min_level_count)
        glm = fit_price_glm(train_df[feature_cols], prep, formula=profile.formula)
        smodel = SerializablePriceModel.from_glm(glm)
        prepared = prep.transform(valid_df[feature_cols])
        work = prepared.copy()
        work[profile.target_col] = valid_df[profile.target_col].values
        import patsy

        y, x = patsy.dmatrices(
            profile.formula, work, return_type="dataframe", NA_action="drop"
        )
        x = x.reindex(columns=smodel.exog_names, fill_value=0)
        preds = np.exp(np.dot(x.values, smodel.params))
        dev = _gamma_mean_deviance(np.asarray(y).ravel(), preds)
        results.append(
            CVFoldResult(fold=i + 1, train_rows=len(train_df), valid_rows=len(valid_df), mean_deviance=dev)
        )

    CV_RESULTS.write_text(
        json.dumps([asdict(r) for r in results], indent=2),
        encoding="utf-8",
    )
    return results


def run_portfolio_batch_glm(
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    *,
    min_level_count: int = PORTFOLIO_PROFILE.min_level_count,
) -> Dict[str, Any]:
    """Poisson frequency + Gamma severity; score holdout pure premium."""
    tr = prepare_portfolio_df(train, min_level_count)
    ho = prepare_portfolio_df(holdout, min_level_count)

    tr_f = tr.rename(columns={"claim_count": "ClaimNb", "exposure": "Exposure"})
    ho_f = ho.rename(columns={"claim_count": "ClaimNb", "exposure": "Exposure"})
    freq = fit_frequency_glm(tr_f, formula=PORTFOLIO_FREQ_FORMULA)
    offset_tr = np.log(tr_f["Exposure"].astype(float).values)
    offset_ho = np.log(ho_f["Exposure"].astype(float).values)
    tr_f["expected_claims"] = predict_on_data(freq, tr_f, offset=offset_tr)
    ho_f["expected_claims"] = predict_on_data(freq, ho_f, offset=offset_ho)

    claims = tr[(tr["claim_count"] > 0) & (tr["claim_cost"] > 0)].copy()
    claims = claims.rename(columns={"claim_cost": "ClaimAmount"})
    sev_glm = None
    if len(claims) >= 50:
        claims_prep = prepare_portfolio_df(claims, min_level_count)
        sev_glm = fit_severity_glm(claims_prep, formula=PORTFOLIO_SEV_FORMULA)
        tr_sev = tr.copy()
        ho_sev = ho.copy()
        tr_sev["ClaimAmount"] = 1.0
        ho_sev["ClaimAmount"] = 1.0
        tr["expected_severity"] = predict_on_data(sev_glm, tr_sev)
        ho["expected_severity"] = predict_on_data(sev_glm, ho_sev)
    else:
        avg_sev = (
            float(tr.loc[tr["claim_cost"] > 0, "claim_cost"].mean())
            if (tr["claim_cost"] > 0).any()
            else 1.0
        )
        tr["expected_severity"] = avg_sev
        ho["expected_severity"] = avg_sev

    tr["freq_rate"] = tr_f["expected_claims"] / tr_f["Exposure"]
    ho["freq_rate"] = ho_f["expected_claims"] / ho_f["Exposure"]
    tr["pure_premium"] = tr["freq_rate"] * tr["expected_severity"]
    ho["pure_premium"] = ho["freq_rate"] * ho["expected_severity"]

    return {
        "freq_aic": float(freq.result.aic),
        "freq_deviance": float(freq.result.deviance),
        "sev_fitted": sev_glm is not None,
        "holdout_mean_pure_premium": float(ho["pure_premium"].mean()),
        "holdout_mean_actual_price": float(ho["price"].mean()),
    }


def run_fit(
    *,
    splits_dir: Path = SPLITS_DIR,
    min_level_count: int = PORTFOLIO_PROFILE.min_level_count,
    sample: Optional[int] = None,
) -> Dict[str, Any]:
    """Fit premium Gamma on train+valid; batch freq×sev; evaluate holdout."""
    train = read_portfolio_csv(splits_dir / "motor_train.csv")
    valid = read_portfolio_csv(splits_dir / "motor_valid.csv")
    holdout = read_portfolio_csv(splits_dir / "motor_holdout.csv")
    fit_df = pd.concat([train, valid], ignore_index=True)
    if sample and len(fit_df) > sample:
        fit_df = fit_df.sample(n=sample, random_state=42)
        holdout = holdout.sample(n=min(max(sample // 5, 500), len(holdout)), random_state=43)

    profile = PORTFOLIO_PROFILE
    cols = [profile.target_col, *profile.feature_cols]
    prep = PricingPreprocessor(profile=profile, min_level_count=min_level_count)
    glm = fit_price_glm(fit_df[cols], prep, formula=profile.formula)
    model = SerializablePriceModel.from_glm(glm)
    work_ho = prep.transform(holdout[cols]).copy()
    work_ho[profile.target_col] = holdout[profile.target_col].values
    import patsy

    y_ho, x_ho = patsy.dmatrices(
        profile.formula, work_ho, return_type="dataframe", NA_action="drop"
    )
    x_ho = x_ho.reindex(columns=model.exog_names, fill_value=0)
    preds = np.exp(np.dot(x_ho.values, model.params))
    premium_deviance = _gamma_mean_deviance(np.asarray(y_ho).ravel(), preds)

    batch_stats = run_portfolio_batch_glm(train, holdout, min_level_count=min_level_count)

    scored_path = PORTFOLIO_DIR / "motor_holdout_scored.csv"
    aligned_idx = y_ho.index
    out = holdout.loc[aligned_idx].copy()
    out["predicted_price"] = preds
    out["prediction_error"] = out["price"] - out["predicted_price"]
    out.to_csv(scored_path, index=False)

    summary = {
        "holdout_rows": len(holdout),
        "premium_mean_deviance": premium_deviance,
        "batch_glm": batch_stats,
        "scored_holdout": str(scored_path.resolve()),
    }
    FIT_SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def run_deploy(
    *,
    splits_dir: Path = SPLITS_DIR,
    store_path: Path = PORTFOLIO_STORE,
    model_dir: Path = PORTFOLIO_MODEL_DIR,
    min_level_count: int = PORTFOLIO_PROFILE.min_level_count,
) -> Dict[str, Any]:
    """Load train+valid into portfolio pricing store and retrain live engine."""
    train = read_portfolio_csv(splits_dir / "motor_train.csv")
    valid = read_portfolio_csv(splits_dir / "motor_valid.csv")
    combined = pd.concat([train, valid], ignore_index=True)
    combined = prepare_portfolio_df(combined, min_level_count)
    payload = live_store_columns(combined)

    store = PricingDataStore(store_path)
    if store.path.is_file():
        store.path.unlink()
    store.append(payload)

    engine = LivePricingEngine(
        store_path=store_path,
        model_dir=model_dir,
        rejected_path=PORTFOLIO_REJECTED,
        profile=PORTFOLIO_PROFILE,
        min_level_count=min_level_count,
    )
    outcome = engine.retrain()
    return {
        "store": str(store.path.resolve()),
        "model_dir": str(model_dir.resolve()),
        "rows": len(payload),
        "retrain": asdict(outcome),
    }
