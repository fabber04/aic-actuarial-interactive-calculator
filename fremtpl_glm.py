"""
freMTPL-style motor CSV -> full GLM pricing (frequency + severity) -> CSV outputs.

Frequency: Poisson GLM with log(Exposure) offset (claim counts).
Severity:  Gamma GLM on claim amounts when --sev CSV is provided; else constant severity.
Calibration: portfolio indicated rate from engine_model.RatemakingModel.

Live Gamma GLM pricing engine (log link on strictly positive ``price``):
  python fremtpl_glm.py bootstrap archive/freMTPL2freq.csv --sample 5000
  python fremtpl_glm.py serve --port 8000
  python fremtpl_glm.py ingest new_records.csv
  python fremtpl_glm.py retrain

Motor portfolio workflow:
  python fremtpl_glm.py portfolio-prep
  python fremtpl_glm.py portfolio-cv --folds 5
  python fremtpl_glm.py portfolio-fit
  python fremtpl_glm.py portfolio-deploy
  python fremtpl_glm.py serve --profile portfolio --port 8000

US claims CSV (insurance_claims.csv) — separate model, same engine:
  python fremtpl_glm.py claims-prep
  python fremtpl_glm.py claims-fit
  python fremtpl_glm.py claims-deploy
  python fremtpl_glm.py claims-score
  python fremtpl_glm.py serve --profile claims --port 8001

Batch CSV pricing (legacy):
  python fremtpl_glm.py archive/freMTPL2freq.csv
  python fremtpl_glm.py archive/freMTPL2freq.csv --sev archive/freMTPL2sev.csv
  python engine_model.py glm archive/freMTPL2freq.csv --out-dir archive
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import warnings
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import joblib

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
from statsmodels.genmod.families.links import Log as LogLink

from engine_model import (
    CredibilityParams,
    ExpenseStructure,
    ExperienceData,
    RatemakingModel,
)

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_AVG_SEVERITY = 1500.0
DEFAULT_PREMIUM_PER_EXPOSURE = 300.0
MIN_LEVEL_COUNT = 500
FREQ_FORMULA = (
    "ClaimNb ~ C(Area) + C(Region) + C(VehBrand) + C(VehGas) + "
    "VehPower + VehAge + DrivAge + BonusMalus + Density"
)
SEV_FORMULA = (
    "ClaimAmount ~ C(Area) + C(Region) + C(VehBrand) + C(VehGas) + "
    "VehPower + VehAge + DrivAge + BonusMalus + Density"
)
REQUIRED_FREQ_COLS = {"IDpol", "ClaimNb", "Exposure"}
SEV_AMOUNT_ALIASES = ("ClaimAmount", "claim_amount", "Amount", "amount", "ClaimNb_sev")


@dataclass
class GLMResult:
    name: str
    family: str
    formula: str
    result: object
    design_info: patsy.DesignInfo


@dataclass
class PricingRun:
    freq_glm: GLMResult
    sev_glm: Optional[GLMResult]
    df_scored: pd.DataFrame
    calibration_factor: float
    indicated_rate: float
    summary_rows: pd.DataFrame


# ── Load & prepare ────────────────────────────────────────────────────────────


def load_freq_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_FREQ_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Frequency file missing columns: {missing}")
    df["ClaimNb"] = pd.to_numeric(df["ClaimNb"], errors="coerce").fillna(0).clip(lower=0)
    df["Exposure"] = pd.to_numeric(df["Exposure"], errors="coerce").fillna(0)
    df = df[df["Exposure"] > 0].copy()
    return df


def load_sev_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "IDpol" not in df.columns:
        raise ValueError("Severity file must contain IDpol")
    amount_col = next((c for c in SEV_AMOUNT_ALIASES if c in df.columns), None)
    if amount_col is None:
        raise ValueError(f"Severity file needs one of: {SEV_AMOUNT_ALIASES}")
    if amount_col != "ClaimAmount":
        df = df.rename(columns={amount_col: "ClaimAmount"})
    df["ClaimAmount"] = pd.to_numeric(df["ClaimAmount"], errors="coerce")
    df = df[df["ClaimAmount"] > 0].copy()
    return df


def collapse_rare_levels(df: pd.DataFrame, cols: Sequence[str], min_count: int) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        counts = out[col].astype(str).value_counts()
        rare = set(counts[counts < min_count].index)
        if rare:
            out[col] = out[col].astype(str).where(~out[col].astype(str).isin(rare), "Other")
    return out


def prepare_freq_df(df: pd.DataFrame, min_level_count: int) -> pd.DataFrame:
    cat_cols = [c for c in ("Area", "Region", "VehBrand", "VehGas") if c in df.columns]
    out = collapse_rare_levels(df, cat_cols, min_level_count)
    for c in ("VehPower", "VehAge", "DrivAge", "BonusMalus", "Density"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["Exposure"])
    return out


def merge_sev_factors(freq: pd.DataFrame, sev: pd.DataFrame) -> pd.DataFrame:
    factor_cols = [c for c in freq.columns if c not in ("IDpol", "ClaimNb", "Exposure")]
    claims = sev.merge(freq[["IDpol"] + factor_cols], on="IDpol", how="left")
    claims = claims.dropna(subset=["ClaimAmount"])
    return prepare_freq_df(claims, MIN_LEVEL_COUNT)


# ── GLM fit ───────────────────────────────────────────────────────────────────


def _fit_glm(
    formula: str,
    data: pd.DataFrame,
    *,
    family: sm.families.Family,
    offset: Optional[np.ndarray] = None,
    name: str = "glm",
) -> GLMResult:
    y, x = patsy.dmatrices(formula, data, return_type="dataframe", NA_action="drop")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        model = sm.GLM(
            y.iloc[:, 0],
            x,
            family=family,
            offset=offset,
        )
        result = model.fit(maxiter=100)
    return GLMResult(
        name=name,
        family=type(family).__name__,
        formula=formula,
        result=result,
        design_info=x.design_info,
    )


def fit_frequency_glm(df: pd.DataFrame, formula: str = FREQ_FORMULA) -> GLMResult:
    offset = np.log(df["Exposure"].astype(float).values)
    return _fit_glm(
        formula,
        df,
        family=sm.families.Poisson(link=LogLink()),
        offset=offset,
        name="frequency",
    )


def fit_severity_glm(claims: pd.DataFrame, formula: str = SEV_FORMULA) -> GLMResult:
    return _fit_glm(
        formula,
        claims,
        family=sm.families.Gamma(link=LogLink()),
        offset=None,
        name="severity",
    )


def predict_on_data(
    glm: GLMResult,
    data: pd.DataFrame,
    *,
    offset: Optional[np.ndarray] = None,
) -> np.ndarray:
    _, x = patsy.dmatrices(glm.formula, data, return_type="dataframe")
    x = x.reindex(columns=glm.result.model.exog_names, fill_value=0)
    if offset is not None:
        return np.asarray(glm.result.predict(exog=x, offset=offset))
    return np.asarray(glm.result.predict(exog=x))


def coefficients_table(glm: GLMResult) -> pd.DataFrame:
    res = glm.result
    return pd.DataFrame(
        {
            "Model": glm.name,
            "Term": res.params.index,
            "Coefficient": res.params.values,
            "StdErr": res.bse,
            "Relativity": np.exp(res.params.values),
            "PValue": res.pvalues.values,
        }
    )


# ── Ratemaking calibration ─────────────────────────────────────────────────────


def portfolio_ratemaking(
    df: pd.DataFrame,
    *,
    avg_severity: float,
    premium_per_exposure: float,
) -> RatemakingModel:
    exposure = float(df["Exposure"].sum())
    claims = float(df["ClaimNb"].sum())
    paid = claims * avg_severity
    prem = exposure * premium_per_exposure
    exp = [
        ExperienceData(
            year=2014,
            exposure=exposure,
            earned_premium=prem,
            claim_count=claims,
            paid_losses=paid,
            incurred_losses=paid,
        )
    ]
    return RatemakingModel(
        name="GLM calibration anchor",
        experience=exp,
        expenses=ExpenseStructure(
            fixed_expense_per_unit=12.0,
            variable_expense_ratio=0.18,
            profit_contingency_load=0.05,
        ),
        credibility=CredibilityParams(full_credibility_claims=1082),
        freq_trend=-0.01,
        sev_trend=0.05,
        trend_period=1.0,
        current_rate=premium_per_exposure,
    )


def gross_up_pure_premium(pp_per_exposure: np.ndarray, rm: RatemakingModel) -> np.ndarray:
    denom = 1.0 - rm.expenses.total_variable
    if denom <= 0:
        raise ValueError("Expense load >= 100%")
    return (pp_per_exposure + rm.expenses.fixed_expense_per_unit) / denom


# ── Full pipeline ─────────────────────────────────────────────────────────────


def run_glm_pricing(
    freq_path: str,
    *,
    sev_path: Optional[str] = None,
    out_dir: Optional[str] = None,
    avg_severity: float = DEFAULT_AVG_SEVERITY,
    premium_per_exposure: float = DEFAULT_PREMIUM_PER_EXPOSURE,
    min_level_count: int = MIN_LEVEL_COUNT,
    sample: Optional[int] = None,
    freq_formula: str = FREQ_FORMULA,
    sev_formula: str = SEV_FORMULA,
) -> PricingRun:
    path = Path(freq_path)
    if not path.is_file():
        raise FileNotFoundError(freq_path)

    df = load_freq_csv(str(path))
    if sample is not None and sample > 0 and len(df) > sample:
        df = df.sample(n=sample, random_state=42)

    df = prepare_freq_df(df, min_level_count)

    print(f"Fitting frequency GLM on {len(df):,} policies …")
    freq_glm = fit_frequency_glm(df, freq_formula)
    exp_offset = np.log(df["Exposure"].astype(float).values)
    expected_claims = predict_on_data(freq_glm, df, offset=exp_offset)
    df = df.copy()
    df["GLM_Expected_Claims"] = expected_claims
    df["GLM_Frequency_Rate"] = expected_claims / df["Exposure"]

    sev_glm: Optional[GLMResult] = None
    if sev_path and Path(sev_path).is_file():
        print("Fitting severity GLM on claim records …")
        sev_raw = load_sev_csv(sev_path)
        claims = merge_sev_factors(df, sev_raw)
        sev_glm = fit_severity_glm(claims, sev_formula)
        sev_pred = predict_on_data(sev_glm, df)
        df["GLM_Expected_Severity"] = sev_pred
        severity_source = "glm"
    else:
        df["GLM_Expected_Severity"] = avg_severity
        severity_source = "constant"

    df["GLM_Pure_Premium_Per_Exposure"] = df["GLM_Frequency_Rate"] * df["GLM_Expected_Severity"]

    rm = portfolio_ratemaking(df, avg_severity=avg_severity, premium_per_exposure=premium_per_exposure)
    indicated = rm.credibility_rate()
    book_pp = float(
        (df["GLM_Pure_Premium_Per_Exposure"] * df["Exposure"]).sum() / df["Exposure"].sum()
    )
    calib = indicated / book_pp if book_pp > 0 else 1.0
    df["Calibration_Factor"] = calib
    df["GLM_Pure_Premium_Per_Exposure_Calibrated"] = df["GLM_Pure_Premium_Per_Exposure"] * calib

    gross_rate = gross_up_pure_premium(df["GLM_Pure_Premium_Per_Exposure_Calibrated"].values, rm)
    df["GLM_Gross_Rate_Per_Exposure"] = gross_rate
    df["GLM_Indicated_Premium"] = gross_rate * df["Exposure"]

    summary = _build_summary(
        path, df, freq_glm, sev_glm, rm, calib, indicated, severity_source, sample
    )

    out = Path(out_dir) if out_dir else path.parent
    out.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    priced_path = out / f"{stem}_glm_priced.csv"
    coef_path = out / f"{stem}_glm_coefficients.csv"
    summary_path = out / f"{stem}_glm_summary.csv"

    df.to_csv(priced_path, index=False)
    coef_frames = [coefficients_table(freq_glm)]
    if sev_glm is not None:
        coef_frames.append(coefficients_table(sev_glm))
    pd.concat(coef_frames, ignore_index=True).to_csv(coef_path, index=False)
    summary.to_csv(summary_path, index=False)

    print(f"Wrote {priced_path} ({len(df):,} rows)")
    print(f"Wrote {coef_path}")
    print(f"Wrote {summary_path}")
    print(f"Calibration factor: {calib:.6f}  |  Indicated rate: {indicated:.4f}")

    return PricingRun(
        freq_glm=freq_glm,
        sev_glm=sev_glm,
        df_scored=df,
        calibration_factor=calib,
        indicated_rate=indicated,
        summary_rows=summary,
    )


def _build_summary(
    path: Path,
    df: pd.DataFrame,
    freq_glm: GLMResult,
    sev_glm: Optional[GLMResult],
    rm: RatemakingModel,
    calib: float,
    indicated: float,
    severity_source: str,
    sample: Optional[int],
) -> pd.DataFrame:
    rows = [
        ("source_file", str(path.resolve())),
        ("policy_rows", len(df)),
        ("total_exposure", float(df["Exposure"].sum())),
        ("total_claims", float(df["ClaimNb"].sum())),
        ("portfolio_frequency", float(df["ClaimNb"].sum() / df["Exposure"].sum())),
        ("severity_source", severity_source),
        ("calibration_factor", calib),
        ("indicated_rate_per_exposure", indicated),
        ("current_rate_proxy", rm.current_rate),
        ("rate_change_pct", rm.rate_change_pct()),
        ("freq_glm_aic", float(freq_glm.result.aic)),
        ("freq_glm_deviance", float(freq_glm.result.deviance)),
        ("sample_used", sample if sample else len(df)),
    ]
    if sev_glm is not None:
        rows.extend(
            [
                ("sev_glm_aic", float(sev_glm.result.aic)),
                ("sev_glm_deviance", float(sev_glm.result.deviance)),
            ]
        )
    return pd.DataFrame(rows, columns=["Metric", "Value"])


# ── Live Gamma GLM pricing engine (Model definition) ─────────────────────────

logger = logging.getLogger("fremtpl_glm.pricing_engine")

PRICE_TARGET = "price"
LOG_EPSILON = 1.0
DRIFT_Z_THRESHOLD = 3.0
LATEST_MODEL_NAME = "pricing_gamma_latest.joblib"

PRICING_FEATURE_COLS = (
    "Area",
    "Region",
    "VehBrand",
    "VehGas",
    "VehPower",
    "VehAge",
    "DrivAge",
    "BonusMalus",
    "Density",
)
PRICING_CATEGORICAL_COLS = ("Area", "Region", "VehBrand", "VehGas")
PRICING_LOG_COLS = ("VehPower", "BonusMalus", "Density")
PRICING_SCALE_COLS = ("VehPower", "VehAge", "DrivAge", "BonusMalus", "Density")
PRICE_FORMULA = (
    "price ~ C(Area) + C(Region) + C(VehBrand) + C(VehGas) + "
    "VehPower_t + VehAge_t + DrivAge_t + BonusMalus_t + Density_t"
)
DEFAULT_STORE_PATH = Path("pricing_data") / "pricing_store.csv"
DEFAULT_MODEL_DIR = Path("pricing_models")
DEFAULT_REJECTED_PATH = Path("pricing_data") / "pricing_rejected.csv"


@dataclass(frozen=True)
class PricingProfile:
    """Column lists and formula for a live Gamma pricing model."""

    name: str
    target_col: str
    feature_cols: Tuple[str, ...]
    categorical_cols: Tuple[str, ...]
    log_cols: Tuple[str, ...]
    linear_cols: Tuple[str, ...]
    scale_cols: Tuple[str, ...]
    formula: str
    drift_numeric_cols: Tuple[str, ...]
    min_level_count: int = MIN_LEVEL_COUNT


FREMTPL_PROFILE = PricingProfile(
    name="fremtpl",
    target_col=PRICE_TARGET,
    feature_cols=PRICING_FEATURE_COLS,
    categorical_cols=PRICING_CATEGORICAL_COLS,
    log_cols=PRICING_LOG_COLS,
    linear_cols=("VehAge", "DrivAge"),
    scale_cols=PRICING_SCALE_COLS,
    formula=PRICE_FORMULA,
    drift_numeric_cols=PRICING_SCALE_COLS,
)

PORTFOLIO_FEATURE_COLS = (
    "Type_risk",
    "Area",
    "Distribution_channel",
    "Type_fuel",
    "Second_driver",
    "Payment",
    "Power",
    "driver_age",
    "vehicle_age",
    "Value_vehicle",
    "Seniority",
    "R_Claims_history",
)
PORTFOLIO_FORMULA = (
    "price ~ C(Type_risk) + C(Area) + C(Distribution_channel) + C(Type_fuel) + "
    "C(Second_driver) + C(Payment) + Power_t + driver_age_t + vehicle_age_t + "
    "Value_vehicle_t + Seniority_t + R_Claims_history_t"
)
PORTFOLIO_PROFILE = PricingProfile(
    name="portfolio",
    target_col=PRICE_TARGET,
    feature_cols=PORTFOLIO_FEATURE_COLS,
    categorical_cols=(
        "Type_risk",
        "Area",
        "Distribution_channel",
        "Type_fuel",
        "Second_driver",
        "Payment",
    ),
    log_cols=("Power", "Value_vehicle", "R_Claims_history"),
    linear_cols=("driver_age", "vehicle_age", "Seniority"),
    scale_cols=("Power", "driver_age", "vehicle_age", "Value_vehicle", "Seniority", "R_Claims_history"),
    formula=PORTFOLIO_FORMULA,
    drift_numeric_cols=("Power", "driver_age", "vehicle_age", "Value_vehicle", "Seniority", "R_Claims_history"),
    min_level_count=200,
)

CLAIMS_FEATURE_COLS = (
    "policy_state",
    "insured_sex",
    "insured_education_level",
    "policy_csl",
    "driver_age",
    "vehicle_age",
    "months_as_customer",
    "policy_deductable",
    "umbrella_limit",
)
CLAIMS_FORMULA = (
    "price ~ C(policy_state) + C(insured_sex) + C(insured_education_level) + C(policy_csl) + "
    "driver_age_t + vehicle_age_t + months_as_customer_t + policy_deductable_t + umbrella_limit_t"
)
CLAIMS_PROFILE = PricingProfile(
    name="claims",
    target_col=PRICE_TARGET,
    feature_cols=CLAIMS_FEATURE_COLS,
    categorical_cols=("policy_state", "insured_sex", "insured_education_level", "policy_csl"),
    log_cols=(),
    linear_cols=("driver_age", "vehicle_age", "months_as_customer", "policy_deductable", "umbrella_limit"),
    scale_cols=("driver_age", "vehicle_age", "months_as_customer", "policy_deductable", "umbrella_limit"),
    formula=CLAIMS_FORMULA,
    drift_numeric_cols=("driver_age", "vehicle_age", "months_as_customer", "policy_deductable", "umbrella_limit"),
    min_level_count=30,
)

PROFILE_BY_NAME = {"fremtpl": FREMTPL_PROFILE, "portfolio": PORTFOLIO_PROFILE, "claims": CLAIMS_PROFILE}


@dataclass
class PriceValidationResult:
    accepted: pd.DataFrame
    rejected: pd.DataFrame
    reasons: List[str]


@dataclass
class SerializablePriceModel:
    """Pickle-safe GLM state (patsy DesignInfo is not serializable)."""

    formula: str
    exog_names: List[str]
    params: np.ndarray

    @classmethod
    def from_glm(cls, glm: GLMResult) -> "SerializablePriceModel":
        return cls(
            formula=glm.formula,
            exog_names=list(glm.result.model.exog_names),
            params=np.asarray(glm.result.params.values, dtype=float),
        )

    def predict(self, prepared: pd.DataFrame, *, target_col: str = PRICE_TARGET) -> np.ndarray:
        work = prepared
        if target_col not in work.columns:
            work = work.copy()
            work[target_col] = 1.0
        _, x = patsy.dmatrices(self.formula, work, return_type="dataframe")
        x = x.reindex(columns=self.exog_names, fill_value=0)
        linear = np.dot(x.values, self.params)
        return np.exp(linear)


@dataclass
class ModelBundle:
    """Serialized artifact: preprocessor + fitted GLM + monitoring baselines."""

    version_id: str
    trained_at: str
    formula: str
    preprocessor: "PricingPreprocessor"
    model: SerializablePriceModel
    row_count: int
    drift_baseline: Dict[str, Dict[str, float]]
    mean_training_price: float
    profile_name: str = "fremtpl"
    target_col: str = PRICE_TARGET


@dataclass
class RetrainOutcome:
    success: bool
    version_id: Optional[str]
    message: str
    mean_deviance: Optional[float] = None
    drift_alerts: List[str] = field(default_factory=list)


@dataclass
class EngineMetrics:
    last_mean_deviance: Optional[float] = None
    last_drift_alerts: List[str] = field(default_factory=list)
    last_retrain_at: Optional[str] = None
    active_version_id: Optional[str] = None
    prediction_count: int = 0
    store_row_count: int = 0


class PricingPreprocessor:
    """Shared fit/transform pipeline for training and API inference."""

    def __init__(
        self,
        *,
        profile: PricingProfile = FREMTPL_PROFILE,
        min_level_count: Optional[int] = None,
        log_epsilon: float = LOG_EPSILON,
    ) -> None:
        self.profile = profile
        self.min_level_count = min_level_count if min_level_count is not None else profile.min_level_count
        self.log_epsilon = log_epsilon
        self._rare_levels: Dict[str, set] = {}
        self._scale_mean: Dict[str, float] = {}
        self._scale_std: Dict[str, float] = {}
        self._fitted = False

    def fit(self, df: pd.DataFrame) -> "PricingPreprocessor":
        cats = self.profile.categorical_cols
        work = collapse_rare_levels(df, cats, self.min_level_count)
        for col in cats:
            if col not in work.columns:
                continue
            counts = work[col].astype(str).value_counts()
            self._rare_levels[col] = set(counts[counts < self.min_level_count].index)
        self._apply_feature_math(work, fitting=True)
        self._fitted = True
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("PricingPreprocessor.transform called before fit")
        work = df.copy()
        for col in self.profile.categorical_cols:
            if col not in work.columns or col not in self._rare_levels:
                continue
            rare = self._rare_levels[col]
            if rare:
                work[col] = work[col].astype(str).where(
                    ~work[col].astype(str).isin(rare), "Other"
                )
        return self._apply_feature_math(work, fitting=False)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.fit(df).transform(df)

    def _apply_feature_math(self, df: pd.DataFrame, *, fitting: bool) -> pd.DataFrame:
        out = df.copy()
        prof = self.profile
        for col in prof.log_cols:
            if col not in out.columns:
                continue
            vals = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
            out[f"{col}_t"] = np.log(vals + self.log_epsilon)
        for col in prof.linear_cols:
            if col not in out.columns:
                continue
            out[f"{col}_t"] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
        for col in prof.scale_cols:
            tcol = f"{col}_t"
            if tcol not in out.columns:
                continue
            series = pd.to_numeric(out[tcol], errors="coerce").fillna(0.0)
            if fitting:
                self._scale_mean[col] = float(series.mean())
                std = float(series.std())
                self._scale_std[col] = std if std > 0 else 1.0
            mean = self._scale_mean[col]
            std = self._scale_std[col]
            out[tcol] = (series - mean) / std
        return out

    @staticmethod
    def drift_baseline(df: pd.DataFrame, profile: PricingProfile = FREMTPL_PROFILE) -> Dict[str, Dict[str, float]]:
        baseline: Dict[str, Dict[str, float]] = {}
        for col in profile.drift_numeric_cols:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            std = float(series.std())
            baseline[col] = {"mean": float(series.mean()), "std": std if std > 0 else 1.0}
        return baseline


def validate_price_records(
    df: pd.DataFrame,
    *,
    target_col: str = PRICE_TARGET,
) -> PriceValidationResult:
    """Reject rows where price is missing, zero, or negative."""
    if target_col not in df.columns:
        raise ValueError(f"Records must include target column '{target_col}'")
    work = df.copy()
    price = pd.to_numeric(work[target_col], errors="coerce")
    valid = price.notna() & (price > 0)
    rejected = work.loc[~valid].copy()
    reasons: List[str] = []
    if not rejected.empty:
        reasons.append(
            f"rejected {len(rejected)} row(s): price must be strictly positive"
        )
    return PriceValidationResult(
        accepted=work.loc[valid].copy(),
        rejected=rejected,
        reasons=reasons,
    )


class PricingDataStore:
    """Append-only CSV store; never overwrites historical pricing rows."""

    def __init__(self, path: Union[str, Path]) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self, profile: Optional["PricingProfile"] = None) -> pd.DataFrame:
        if not self.path.is_file():
            return pd.DataFrame()
        dtype = None
        if profile is not None:
            dtype = {c: str for c in profile.categorical_cols}
        return pd.read_csv(self.path, dtype=dtype, low_memory=False)

    def append(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        existing = self.load()
        combined = pd.concat([existing, df], ignore_index=True) if not existing.empty else df
        combined.to_csv(self.path, index=False)
        return len(df)

    def row_count(self) -> int:
        return len(self.load())


def _ensure_feature_columns(df: pd.DataFrame, profile: PricingProfile = FREMTPL_PROFILE) -> None:
    missing = set(profile.feature_cols) - set(df.columns)
    if missing:
        raise ValueError(f"Pricing records missing feature columns: {missing}")


def fit_price_glm(
    df: pd.DataFrame,
    preprocessor: PricingPreprocessor,
    *,
    formula: Optional[str] = None,
) -> GLMResult:
    formula = formula or preprocessor.profile.formula
    prepared = preprocessor.fit_transform(df)
    return _fit_glm(
        formula,
        prepared,
        family=sm.families.Gamma(link=LogLink()),
        offset=None,
        name="price_gamma",
    )


def _gamma_mean_deviance(y: np.ndarray, mu: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    mu = np.maximum(np.asarray(mu, dtype=float), 1e-12)
    # Gamma deviance with log link (standard GLM form).
    term = (y - mu) / mu
    dev = 2.0 * np.sum(y * term - np.log((y + 1e-12) / mu))
    return float(dev / len(y)) if len(y) else 0.0


def check_feature_drift(
    batch: pd.DataFrame,
    baseline: Dict[str, Dict[str, float]],
    *,
    threshold: float = DRIFT_Z_THRESHOLD,
) -> List[str]:
    alerts: List[str] = []
    for col, stats in baseline.items():
        if col not in batch.columns:
            continue
        series = pd.to_numeric(batch[col], errors="coerce").dropna()
        if series.empty:
            continue
        batch_mean = float(series.mean())
        z = abs(batch_mean - stats["mean"]) / stats["std"]
        if z > threshold:
            msg = (
                f"drift alert: {col} batch mean {batch_mean:.4f} "
                f"vs training {stats['mean']:.4f} (z={z:.2f})"
            )
            alerts.append(msg)
            logger.warning(msg)
    return alerts


def save_model_bundle(bundle: ModelBundle, model_dir: Union[str, Path]) -> Tuple[Path, Path]:
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    stamped = model_dir / f"pricing_gamma_{bundle.version_id}.joblib"
    latest = model_dir / LATEST_MODEL_NAME
    joblib.dump(bundle, stamped)
    joblib.dump(bundle, latest)
    return stamped, latest


def load_model_bundle(path: Union[str, Path]) -> ModelBundle:
    bundle = joblib.load(path)
    if not isinstance(bundle, ModelBundle):
        raise TypeError(f"Expected ModelBundle in {path}, got {type(bundle)}")
    return bundle


def retrain_pricing_model(
    store: PricingDataStore,
    model_dir: Union[str, Path],
    *,
    profile: PricingProfile = FREMTPL_PROFILE,
    min_level_count: Optional[int] = None,
    formula: Optional[str] = None,
) -> ModelBundle:
    """Retrain Gamma GLM on the full historical store (statsmodels + joblib)."""
    raw = store.load(profile)
    if raw.empty:
        raise ValueError("Cannot retrain: pricing store is empty")
    mlc = min_level_count if min_level_count is not None else profile.min_level_count
    formula = formula or profile.formula
    if profile.name == "portfolio":
        from portfolio_motor import prepare_portfolio_df

        raw = prepare_portfolio_df(raw, mlc)
    elif profile.name == "claims":
        from claims_us import prepare_claims_df

        raw = prepare_claims_df(raw, mlc)
    validation = validate_price_records(raw, target_col=profile.target_col)
    if validation.rejected.shape[0] > 0:
        raise ValueError(
            "Store contains invalid prices; clean data before retrain: "
            + "; ".join(validation.reasons)
        )
    _ensure_feature_columns(validation.accepted, profile)
    preprocessor = PricingPreprocessor(profile=profile, min_level_count=mlc)
    glm = fit_price_glm(validation.accepted, preprocessor, formula=formula)
    version_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle = ModelBundle(
        version_id=version_id,
        trained_at=datetime.now(timezone.utc).isoformat(),
        formula=formula,
        preprocessor=preprocessor,
        model=SerializablePriceModel.from_glm(glm),
        row_count=len(validation.accepted),
        drift_baseline=PricingPreprocessor.drift_baseline(validation.accepted, profile),
        mean_training_price=float(validation.accepted[profile.target_col].mean()),
        profile_name=profile.name,
        target_col=profile.target_col,
    )
    save_model_bundle(bundle, model_dir)
    logger.info("Saved pricing model version %s (%s rows)", version_id, bundle.row_count)
    return bundle


def bootstrap_store_from_freq(
    freq_path: str,
    store: PricingDataStore,
    *,
    premium_per_exposure: float = DEFAULT_PREMIUM_PER_EXPOSURE,
    min_level_count: int = MIN_LEVEL_COUNT,
    sample: Optional[int] = None,
) -> int:
    """Seed the pricing store from freMTPL frequency CSV (synthetic strictly positive price)."""
    df = load_freq_csv(freq_path)
    if sample is not None and sample > 0 and len(df) > sample:
        df = df.sample(n=sample, random_state=42)
    df = prepare_freq_df(df, min_level_count)
    df[PRICE_TARGET] = premium_per_exposure * df["Exposure"].astype(float)
    cols = [PRICE_TARGET, *PRICING_FEATURE_COLS]
    if "IDpol" in df.columns:
        cols = ["IDpol", *cols]
    payload = df[[c for c in cols if c in df.columns]].copy()
    validation = validate_price_records(payload)
    return store.append(validation.accepted)


class LivePricingEngine:
    """Thread-safe hot-swapped Gamma GLM loaded from the latest joblib artifact."""

    def __init__(
        self,
        store_path: Union[str, Path] = DEFAULT_STORE_PATH,
        model_dir: Union[str, Path] = DEFAULT_MODEL_DIR,
        *,
        rejected_path: Union[str, Path] = DEFAULT_REJECTED_PATH,
        profile: PricingProfile = FREMTPL_PROFILE,
        min_level_count: Optional[int] = None,
    ) -> None:
        self.store = PricingDataStore(store_path)
        self.model_dir = Path(model_dir)
        self.rejected_path = Path(rejected_path)
        self.profile = profile
        self.min_level_count = min_level_count if min_level_count is not None else profile.min_level_count
        self._lock = threading.RLock()
        self._bundle: Optional[ModelBundle] = None
        self.metrics = EngineMetrics()
        self._load_latest_if_present()

    def _load_latest_if_present(self) -> None:
        latest = self.model_dir / LATEST_MODEL_NAME
        if latest.is_file():
            try:
                self._bundle = load_model_bundle(latest)
                self.metrics.active_version_id = self._bundle.version_id
                self.metrics.store_row_count = self.store.row_count()
            except (OSError, TypeError, ValueError) as exc:
                logger.error("Failed to load latest model: %s", exc)

    def has_model(self) -> bool:
        return self._bundle is not None

    def append_and_retrain(
        self,
        records: pd.DataFrame,
        *,
        retrain: bool = True,
    ) -> Dict[str, Any]:
        validation = validate_price_records(records, target_col=self.profile.target_col)
        _ensure_feature_columns(validation.accepted, self.profile)
        if not validation.rejected.empty:
            self._log_rejected(validation.rejected)
        appended = 0
        drift_alerts: List[str] = []
        if not validation.accepted.empty:
            if self._bundle is not None:
                drift_alerts = check_feature_drift(
                    validation.accepted, self._bundle.drift_baseline
                )
            appended = self.store.append(validation.accepted)
        outcome = RetrainOutcome(
            success=False,
            version_id=None,
            message="no retrain requested",
            drift_alerts=drift_alerts,
        )
        if retrain and appended > 0:
            outcome = self.retrain(drift_alerts=drift_alerts)
        self.metrics.store_row_count = self.store.row_count()
        return {
            "appended": appended,
            "rejected": len(validation.rejected),
            "reasons": validation.reasons,
            "retrain": asdict(outcome),
            "drift_alerts": drift_alerts,
        }

    def _log_rejected(self, rejected: pd.DataFrame) -> None:
        self.rejected_path.parent.mkdir(parents=True, exist_ok=True)
        header = not self.rejected_path.is_file()
        rejected.to_csv(self.rejected_path, mode="a", header=header, index=False)

    def retrain(self, *, drift_alerts: Optional[List[str]] = None) -> RetrainOutcome:
        previous = self._bundle
        try:
            bundle = retrain_pricing_model(
                self.store,
                self.model_dir,
                profile=self.profile,
                min_level_count=self.min_level_count,
            )
        except Exception as exc:
            msg = f"retrain failed, keeping previous model: {exc}"
            logger.exception(msg)
            return RetrainOutcome(success=False, version_id=None, message=msg)

        batch = self.store.load(self.profile).tail(min(500, self.store.row_count()))
        mean_dev: Optional[float] = None
        tcol = self.profile.target_col
        if not batch.empty and tcol in batch.columns:
            work = batch.drop(columns=[tcol])
            prepared = bundle.preprocessor.transform(work)
            preds = bundle.model.predict(prepared, target_col=tcol)
            y = batch[tcol].astype(float).values
            mean_dev = _gamma_mean_deviance(y, preds)
            logger.info("Batch mean deviance after retrain: %.6f", mean_dev)

        alerts = list(drift_alerts or [])
        with self._lock:
            self._bundle = bundle
            self.metrics.active_version_id = bundle.version_id
            self.metrics.last_retrain_at = bundle.trained_at
            self.metrics.last_mean_deviance = mean_dev
            self.metrics.last_drift_alerts = alerts
            self.metrics.store_row_count = bundle.row_count

        if previous is not None and previous.version_id != bundle.version_id:
            logger.info("Hot-swapped model %s -> %s", previous.version_id, bundle.version_id)

        return RetrainOutcome(
            success=True,
            version_id=bundle.version_id,
            message="retrain ok",
            mean_deviance=mean_dev,
            drift_alerts=alerts,
        )

    def rollback(self, version_path: Union[str, Path]) -> None:
        bundle = load_model_bundle(version_path)
        stamped = save_model_bundle(bundle, self.model_dir)
        with self._lock:
            self._bundle = bundle
            self.metrics.active_version_id = bundle.version_id
        logger.info("Rolled back to version %s via %s", bundle.version_id, stamped[0])

    def predict(self, records: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]) -> np.ndarray:
        if isinstance(records, dict):
            frame = pd.DataFrame([records])
        elif isinstance(records, list):
            frame = pd.DataFrame(records)
        else:
            frame = records
        with self._lock:
            if self._bundle is None:
                raise RuntimeError("No trained pricing model loaded")
            preds = self._predict_unlocked(frame)
            self.metrics.prediction_count += len(preds)
        return preds

    def _predict_unlocked(self, records: pd.DataFrame) -> np.ndarray:
        assert self._bundle is not None
        tcol = self.profile.target_col
        if tcol in records.columns:
            work = records.drop(columns=[tcol])
        else:
            work = records
        _ensure_feature_columns(work, self.profile)
        prepared = self._bundle.preprocessor.transform(work)
        return self._bundle.model.predict(prepared, target_col=tcol)

    def predict_price(
        self, features: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]]
    ) -> List[float]:
        preds = self.predict(features)
        if np.any(preds <= 0):
            raise ValueError("Model produced non-positive price prediction")
        return [float(x) for x in preds]


def create_pricing_app(engine: LivePricingEngine):
    """FastAPI application for live price prediction and data ingest."""
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    class PredictRequest(BaseModel):
        features: Union[Dict[str, Any], List[Dict[str, Any]]] = Field(
            ..., description="One record or a list of feature dicts"
        )

    class PredictResponse(BaseModel):
        prices: List[float]
        model_version: Optional[str]

    class AppendRequest(BaseModel):
        records: List[Dict[str, Any]]

    app = FastAPI(title="Gamma GLM Pricing Engine", version="1.0")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {
            "status": "ok",
            "model_loaded": engine.has_model(),
            "model_version": engine.metrics.active_version_id,
            "store_rows": engine.store.row_count(),
        }

    @app.get("/metrics")
    def metrics() -> Dict[str, Any]:
        m = engine.metrics
        return {
            "active_version_id": m.active_version_id,
            "last_retrain_at": m.last_retrain_at,
            "last_mean_deviance": m.last_mean_deviance,
            "last_drift_alerts": m.last_drift_alerts,
            "prediction_count": m.prediction_count,
            "store_row_count": m.store_row_count,
        }

    @app.post("/predict", response_model=PredictResponse)
    def predict_endpoint(body: PredictRequest) -> PredictResponse:
        if not engine.has_model():
            raise HTTPException(status_code=503, detail="No trained model available")
        try:
            prices = engine.predict_price(body.features)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PredictResponse(
            prices=prices,
            model_version=engine.metrics.active_version_id,
        )

    @app.post("/data/append")
    def append_endpoint(body: AppendRequest) -> Dict[str, Any]:
        if not body.records:
            raise HTTPException(status_code=400, detail="records must not be empty")
        frame = pd.DataFrame(body.records)
        try:
            return engine.append_and_retrain(frame, retrain=True)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/retrain")
    def retrain_endpoint() -> Dict[str, Any]:
        outcome = engine.retrain()
        if not outcome.success:
            raise HTTPException(status_code=500, detail=outcome.message)
        return asdict(outcome)

    return app


def _run_batch_pricing(argv: Sequence[str]) -> int:
    p = argparse.ArgumentParser(description="Full GLM pricing for freMTPL-style CSV")
    p.add_argument("freq_csv", help="Policy file (IDpol, ClaimNb, Exposure, factors)")
    p.add_argument("--sev", default=None, help="Optional claim severity CSV (IDpol, ClaimAmount)")
    p.add_argument("--out-dir", default=None, help="Output directory (default: same as input)")
    p.add_argument("--avg-severity", type=float, default=DEFAULT_AVG_SEVERITY)
    p.add_argument("--premium-per-exposure", type=float, default=DEFAULT_PREMIUM_PER_EXPOSURE)
    p.add_argument("--min-level-count", type=int, default=MIN_LEVEL_COUNT)
    p.add_argument("--sample", type=int, default=None, help="Random sample size for fast runs")
    args = p.parse_args(list(argv))

    try:
        run_glm_pricing(
            args.freq_csv,
            sev_path=args.sev,
            out_dir=args.out_dir,
            avg_severity=args.avg_severity,
            premium_per_exposure=args.premium_per_exposure,
            min_level_count=args.min_level_count,
            sample=args.sample,
        )
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


def _run_engine_command(argv: Sequence[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cmd = argv[0] if argv else ""
    rest = list(argv[1:])

    def _engine_from_args(ns: argparse.Namespace) -> LivePricingEngine:
        profile = PROFILE_BY_NAME.get(getattr(ns, "profile", "fremtpl"), FREMTPL_PROFILE)
        return LivePricingEngine(
            store_path=ns.store,
            model_dir=ns.model_dir,
            rejected_path=getattr(ns, "rejected", DEFAULT_REJECTED_PATH),
            profile=profile,
            min_level_count=ns.min_level_count,
        )

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--store", type=Path, default=None)
    common.add_argument("--model-dir", type=Path, default=None)
    common.add_argument(
        "--profile",
        choices=sorted(PROFILE_BY_NAME),
        default="fremtpl",
        help="Pricing profile (portfolio uses separate store/model paths by default)",
    )
    common.add_argument("--min-level-count", type=int, default=None)

    def _resolve_engine_paths(ns: argparse.Namespace) -> None:
        if ns.profile == "portfolio":
            from portfolio_motor import PORTFOLIO_MODEL_DIR, PORTFOLIO_REJECTED, PORTFOLIO_STORE

            if ns.store is None:
                ns.store = PORTFOLIO_STORE
            if ns.model_dir is None:
                ns.model_dir = PORTFOLIO_MODEL_DIR
            if not hasattr(ns, "rejected") or getattr(ns, "rejected", None) is None:
                ns.rejected = PORTFOLIO_REJECTED
        elif ns.profile == "claims":
            from claims_us import CLAIMS_MODEL_DIR, CLAIMS_REJECTED, CLAIMS_STORE

            if ns.store is None:
                ns.store = CLAIMS_STORE
            if ns.model_dir is None:
                ns.model_dir = CLAIMS_MODEL_DIR
            if not hasattr(ns, "rejected") or getattr(ns, "rejected", None) is None:
                ns.rejected = CLAIMS_REJECTED
        else:
            if ns.store is None:
                ns.store = DEFAULT_STORE_PATH
            if ns.model_dir is None:
                ns.model_dir = DEFAULT_MODEL_DIR
            ns.rejected = DEFAULT_REJECTED_PATH
        prof = PROFILE_BY_NAME[ns.profile]
        if ns.min_level_count is None:
            ns.min_level_count = prof.min_level_count

    if cmd == "serve":
        sp = argparse.ArgumentParser(description="Run REST pricing API", parents=[common])
        sp.add_argument("--host", default="127.0.0.1")
        sp.add_argument("--port", type=int, default=8000)
        ns = sp.parse_args(rest)
        _resolve_engine_paths(ns)
        engine = _engine_from_args(ns)
        if not engine.has_model():
            print("No model on disk; run bootstrap + retrain first.", file=sys.stderr)
            return 1
        import uvicorn

        app = create_pricing_app(engine)
        uvicorn.run(app, host=ns.host, port=ns.port)
        return 0

    if cmd == "bootstrap":
        sp = argparse.ArgumentParser(description="Seed pricing store from freMTPL freq CSV", parents=[common])
        sp.add_argument("freq_csv", help="freMTPL frequency CSV")
        sp.add_argument("--sample", type=int, default=None)
        sp.add_argument(
            "--premium-per-exposure",
            type=float,
            default=DEFAULT_PREMIUM_PER_EXPOSURE,
        )
        sp.add_argument(
            "--no-retrain",
            action="store_true",
            help="Only append to store; do not fit GLM",
        )
        ns = sp.parse_args(rest)
        _resolve_engine_paths(ns)
        engine = _engine_from_args(ns)
        n = bootstrap_store_from_freq(
            ns.freq_csv,
            engine.store,
            premium_per_exposure=ns.premium_per_exposure,
            min_level_count=ns.min_level_count,
            sample=ns.sample,
        )
        print(f"Bootstrapped {n} rows into {engine.store.path}")
        if not ns.no_retrain:
            outcome = engine.retrain()
            print(json.dumps(asdict(outcome), indent=2))
            if not outcome.success:
                return 1
        return 0

    if cmd == "ingest":
        sp = argparse.ArgumentParser(description="Append pricing CSV and retrain", parents=[common])
        sp.add_argument("records_csv", help="CSV with price + rating features")
        ns = sp.parse_args(rest)
        _resolve_engine_paths(ns)
        engine = _engine_from_args(ns)
        frame = pd.read_csv(ns.records_csv)
        result = engine.append_and_retrain(frame)
        print(json.dumps(result, indent=2, default=str))
        if result["rejected"] and result["appended"] == 0:
            return 1
        return 0

    if cmd == "retrain":
        sp = argparse.ArgumentParser(description="Retrain on full pricing store", parents=[common])
        ns = sp.parse_args(rest)
        _resolve_engine_paths(ns)
        engine = _engine_from_args(ns)
        outcome = engine.retrain()
        print(json.dumps(asdict(outcome), indent=2))
        return 0 if outcome.success else 1

    if cmd == "rollback":
        sp = argparse.ArgumentParser(description="Activate a versioned joblib snapshot", parents=[common])
        sp.add_argument("version_file", type=Path, help="pricing_gamma_YYYYMMDD_HHMMSS.joblib")
        ns = sp.parse_args(rest)
        _resolve_engine_paths(ns)
        engine = _engine_from_args(ns)
        engine.rollback(ns.version_file)
        print(f"Active version: {engine.metrics.active_version_id}")
        return 0

    print(f"Unknown engine command: {cmd}", file=sys.stderr)
    return 1


def _run_portfolio_command(argv: Sequence[str]) -> int:
    import portfolio_motor as pm

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cmd = argv[0] if argv else ""
    rest = list(argv[1:])

    if cmd == "portfolio-prep":
        sp = argparse.ArgumentParser(description="Clean motor CSV and write temporal splits")
        sp.add_argument("--raw", type=Path, default=pm.RAW_CSV)
        sp.add_argument("--train-end", type=int, default=pm.DEFAULT_TRAIN_END)
        sp.add_argument("--valid-end", type=int, default=pm.DEFAULT_VALID_END)
        sp.add_argument("--holdout-year", type=int, default=pm.DEFAULT_HOLDOUT_YEAR)
        sp.add_argument("--in-force-only", action="store_true")
        ns = sp.parse_args(rest)
        meta = pm.run_prep(
            ns.raw,
            train_end=ns.train_end,
            valid_end=ns.valid_end,
            holdout_year=ns.holdout_year,
            in_force_only=ns.in_force_only,
        )
        print(json.dumps(asdict(meta), indent=2))
        print(f"Wrote {pm.CLEAN_CSV}")
        print(f"Splits in {pm.SPLITS_DIR}")
        return 0

    if cmd == "portfolio-cv":
        sp = argparse.ArgumentParser(description="Grouped CV on train split (Gamma premium)")
        sp.add_argument("--folds", type=int, default=5)
        sp.add_argument("--sample", type=int, default=None)
        sp.add_argument("--seed", type=int, default=42)
        ns = sp.parse_args(rest)
        results = pm.run_grouped_cv(n_folds=ns.folds, sample=ns.sample, seed=ns.seed)
        avg_dev = sum(r.mean_deviance for r in results) / len(results) if results else 0.0
        print(json.dumps([asdict(r) for r in results], indent=2))
        print(f"Mean CV deviance: {avg_dev:.6f}")
        print(f"Wrote {pm.CV_RESULTS}")
        return 0

    if cmd == "portfolio-fit":
        sp = argparse.ArgumentParser(description="Fit models and score holdout")
        sp.add_argument("--sample", type=int, default=None, help="Subsample for quick runs")
        ns = sp.parse_args(rest)
        summary = pm.run_fit(sample=ns.sample)
        print(json.dumps(summary, indent=2))
        return 0

    if cmd == "portfolio-deploy":
        sp = argparse.ArgumentParser(description="Deploy train+valid to live portfolio engine")
        ns = sp.parse_args(rest)
        result = pm.run_deploy()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["retrain"].get("success") else 1

    print(f"Unknown portfolio command: {cmd}", file=sys.stderr)
    return 1


_ENGINE_COMMANDS = frozenset({"serve", "bootstrap", "ingest", "retrain", "rollback"})
_PORTFOLIO_COMMANDS = frozenset(
    {"portfolio-prep", "portfolio-cv", "portfolio-fit", "portfolio-deploy"}
)
_CLAIMS_COMMANDS = frozenset({"claims-prep", "claims-fit", "claims-deploy", "claims-score"})


def _run_claims_command(argv: Sequence[str]) -> int:
    import claims_us as cu

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    cmd = argv[0] if argv else ""
    rest = list(argv[1:])

    if cmd == "claims-prep":
        sp = argparse.ArgumentParser(description="Clean US claims CSV and write splits")
        sp.add_argument("--raw", type=Path, default=cu.RAW_CSV)
        sp.add_argument("--train-end", type=int, default=cu.DEFAULT_TRAIN_END)
        sp.add_argument("--valid-year", type=int, default=cu.DEFAULT_VALID_YEAR)
        sp.add_argument("--holdout-year", type=int, default=cu.DEFAULT_HOLDOUT_YEAR)
        ns = sp.parse_args(rest)
        meta = cu.run_prep(
            ns.raw,
            train_end=ns.train_end,
            valid_year=ns.valid_year,
            holdout_year=ns.holdout_year,
        )
        print(json.dumps(asdict(meta), indent=2))
        return 0

    if cmd == "claims-fit":
        sp = argparse.ArgumentParser(description="Fit claims premium Gamma GLM and score holdout")
        ns = sp.parse_args(rest)
        print(json.dumps(cu.run_fit(), indent=2))
        return 0

    if cmd == "claims-deploy":
        sp = argparse.ArgumentParser(description="Deploy claims model to live engine")
        ns = sp.parse_args(rest)
        result = cu.run_deploy()
        print(json.dumps(result, indent=2, default=str))
        return 0 if result["retrain"].get("success") else 1

    if cmd == "claims-score":
        sp = argparse.ArgumentParser(description="Score a claims-format CSV with deployed claims model")
        sp.add_argument("input_csv", type=Path, nargs="?", default=cu.RAW_CSV)
        sp.add_argument("--out", type=Path, default=cu.CLAIMS_DIR / "insurance_claims_scored.csv")
        ns = sp.parse_args(rest)
        n = cu.score_file(ns.input_csv, ns.out)
        print(f"Scored {n} rows -> {ns.out}")
        return 0

    print(f"Unknown claims command: {cmd}", file=sys.stderr)
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if args and args[0] in _CLAIMS_COMMANDS:
        return _run_claims_command(args)
    if args and args[0] in _PORTFOLIO_COMMANDS:
        return _run_portfolio_command(args)
    if args and args[0] in _ENGINE_COMMANDS:
        return _run_engine_command(args)
    if not args:
        argparse.ArgumentParser(
            description="freMTPL batch GLM, live engine, or portfolio workflow (portfolio-prep|cv|fit|deploy)"
        ).print_help()
        return 1
    return _run_batch_pricing(args)


if __name__ == "__main__":
    sys.exit(main())
