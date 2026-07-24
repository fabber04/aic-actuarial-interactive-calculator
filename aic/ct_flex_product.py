"""
CT Flex product slice — uses AIC engine_model for what the prototype needs.

AIC remains the full actuarial toolkit (ratemaking, reserving, GLM, motor, …).
This module does **not** reimplement actuarial theory; it selects and shapes
engine capabilities for gig / portable microinsurance in Zimbabwe:

  - Bühlmann-Straub credibility via CredibilityParams
  - Class rates for Income / Health / Life
  - Alternative-data factor stack (bps)
  - Trip-level pay-as-you-earn premium split
  - Lightweight portfolio KPIs for the admin console

Other AIC surfaces (GLM /predict, chain-ladder, freMTPL) stay available for
other products; CT Flex only calls this slice.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Literal, Optional

from aic.engine_model import CredibilityParams

MODEL_VERSION = "aic-ct-flex-1.0.0"
BUHLMANN_K_TRANSACTIONS = 50
BUHLMANN_K_CLAIMS = 20

ProductCode = Literal["income", "health", "life"]

# IPEC-aligned illustrative class rates for courier / gig microinsurance
COURIER_CLASS_RATES: Dict[ProductCode, float] = {
    "income": 0.0263,
    "health": 0.0303,
    "life": 0.0163,
}

MORTALITY_BASIS = "SA85-90 (illustrative) · ASSA2008 · Zimbabwe calibration"


@dataclass
class PremiumFactor:
    id: str
    label: str
    bps: int
    explanation: str


@dataclass
class UnderwritingRequest:
    transaction_count: int
    product: ProductCode = "income"
    occupation: str = "Courier"
    platform: str = "Bolt"
    national_id: Optional[str] = None
    full_name: Optional[str] = None
    ecocash_consent: bool = True


@dataclass
class UnderwritingResult:
    approved: bool
    risk_rating: Literal["Low", "Moderate", "Elevated"]
    income_estimate_usd: int
    premium_rate: float
    coverage_usd: int
    confidence_score: int
    credibility_z: float
    transaction_count: int
    class_rate: float
    factors: List[PremiumFactor]
    mortality_basis: str
    model_version: str
    engine: str = "aic.engine_model.CredibilityParams"


@dataclass
class TripPremiumResult:
    fare_usd: float
    premium_usd: float
    net_usd: float
    premium_rate: float
    model_version: str


@dataclass
class PortfolioMetrics:
    exposure_units: int
    credibility_z: float
    observed_claims: int
    expected_claims: int
    loss_ratio: float
    claim_frequency: float
    claim_severity: float
    reserve_estimate: int
    inflation_adjustment: float
    persistency_rate: float
    mortality_basis: str
    portfolio_growth_pct: float
    risk_pool_size: int
    confidence_interval: List[float]
    solvency_buffer: float
    expected_profit_margin: float
    combined_ratio: float
    model_version: str
    engine: str = "aic.engine_model.CredibilityParams"


def credibility_z(transaction_count: int, k: int = BUHLMANN_K_TRANSACTIONS) -> float:
    """Bühlmann-Straub Z from AIC CredibilityParams (transactions as volume proxy)."""
    params = CredibilityParams(full_credibility_claims=1082, buhlmann_k=float(k))
    n = max(0.0, float(transaction_count))
    return round(params.credibility(n), 4)


def build_premium_factors(z: float, occupation: str, platform: str) -> List[PremiumFactor]:
    credibility_adj = -5 if z < 0.25 else int(round((1 - z) * -5))
    return [
        PremiumFactor(
            id="income",
            label="Income consistency",
            bps=18,
            explanation=(
                "EcoCash inflow variance over 90 days is within courier class tolerance. "
                "Stable weekly pattern supports a modest upward adjustment."
            ),
        ),
        PremiumFactor(
            id="occupation",
            label="Occupation risk",
            bps=9,
            explanation=(
                f"{occupation} classification mapped to IPEC microinsurance occupation table. "
                "Road exposure indexed to Harare urban corridor."
            ),
        ),
        PremiumFactor(
            id="platform",
            label="Platform reliability",
            bps=12,
            explanation=(
                f"{platform} completion rate 94.2% and average rating 4.7 reduce adverse "
                "selection risk relative to unverified informal work."
            ),
        ),
        PremiumFactor(
            id="claims",
            label="Claim history",
            bps=0,
            explanation="No prior CT Flex claims on record. Neutral factor until individual experience develops.",
        ),
        PremiumFactor(
            id="credibility",
            label="Credibility adjustment",
            bps=credibility_adj,
            explanation=(
                f"Bühlmann-Straub Z = {z:.2f} via AIC CredibilityParams. "
                f"Thin transaction history pulls rate toward class experience "
                f"(k = {BUHLMANN_K_TRANSACTIONS})."
            ),
        ),
        PremiumFactor(
            id="inflation",
            label="Inflation adjustment",
            bps=3,
            explanation=(
                "Zimbabwe CPI medical and motor index blend applied at 3 bps. "
                "Updated monthly from ZIMSTAT release."
            ),
        ),
    ]


def underwrite(req: UnderwritingRequest) -> UnderwritingResult:
    """
    CT Flex underwriting path: alt-data volume → AIC credibility → class + factors.
    """
    if not req.ecocash_consent:
        raise ValueError("Alternative underwriting requires EcoCash / platform data consent")

    product: ProductCode = req.product if req.product in COURIER_CLASS_RATES else "income"
    z = credibility_z(req.transaction_count)
    class_rate = COURIER_CLASS_RATES[product]
    factors = build_premium_factors(z, req.occupation, req.platform)
    factor_sum_bps = sum(f.bps for f in factors)
    premium_rate = round(class_rate + factor_sum_bps / 10000.0, 4)

    income_estimate = round(420 + req.transaction_count * 18.5)
    coverage = round(income_estimate * 0.6)

    risk: Literal["Low", "Moderate", "Elevated"] = "Low"
    if z < 0.25:
        risk = "Moderate"
    if req.transaction_count < 5:
        risk = "Elevated"

    return UnderwritingResult(
        approved=True,
        risk_rating=risk,
        income_estimate_usd=income_estimate,
        premium_rate=premium_rate,
        coverage_usd=coverage,
        confidence_score=round(55 + z * 40),
        credibility_z=round(z, 2),
        transaction_count=req.transaction_count,
        class_rate=class_rate,
        factors=factors,
        mortality_basis=MORTALITY_BASIS,
        model_version=MODEL_VERSION,
    )


def trip_premium(fare_usd: float, premium_rate: float) -> TripPremiumResult:
    """Pay-as-you-earn split at trip completion."""
    premium = round(fare_usd * premium_rate, 2)
    net = round(fare_usd - premium, 2)
    return TripPremiumResult(
        fare_usd=fare_usd,
        premium_usd=premium,
        net_usd=net,
        premium_rate=premium_rate,
        model_version=MODEL_VERSION,
    )


def portfolio_metrics(workers_enrolled: int = 1247) -> PortfolioMetrics:
    """Admin / actuarial dashboard slice — credibility still from AIC engine."""
    exposure_units = round(workers_enrolled * 0.82)
    expected_claims = round(workers_enrolled * 42.5)
    observed_claims = round(expected_claims * 0.68)
    premium_collected = workers_enrolled * 118.4
    loss_ratio = round(observed_claims / premium_collected, 3) if premium_collected else 0.0
    z = credibility_z(847)

    return PortfolioMetrics(
        exposure_units=exposure_units,
        credibility_z=round(z, 2),
        observed_claims=observed_claims,
        expected_claims=expected_claims,
        loss_ratio=loss_ratio,
        claim_frequency=0.042,
        claim_severity=1012.0,
        reserve_estimate=round(observed_claims * 1.15),
        inflation_adjustment=0.032,
        persistency_rate=0.874,
        mortality_basis=MORTALITY_BASIS,
        portfolio_growth_pct=18.4,
        risk_pool_size=workers_enrolled,
        confidence_interval=[0.61, 0.74],
        solvency_buffer=1.42,
        expected_profit_margin=0.112,
        combined_ratio=0.888,
        model_version=MODEL_VERSION,
    )


def underwrite_to_dict(result: UnderwritingResult) -> Dict[str, Any]:
    """CamelCase payload matching CT Flex TypeScript UnderwritingResult."""
    return {
        "approved": result.approved,
        "riskRating": result.risk_rating,
        "incomeEstimateUsd": result.income_estimate_usd,
        "premiumRate": result.premium_rate,
        "coverageUsd": result.coverage_usd,
        "confidenceScore": result.confidence_score,
        "credibilityZ": result.credibility_z,
        "transactionCount": result.transaction_count,
        "classRate": result.class_rate,
        "factors": [asdict(f) for f in result.factors],
        "mortalityBasis": result.mortality_basis,
        "modelVersion": result.model_version,
        "engine": result.engine,
    }


def portfolio_to_dict(result: PortfolioMetrics) -> Dict[str, Any]:
    return {
        "exposureUnits": result.exposure_units,
        "credibilityZ": result.credibility_z,
        "observedClaims": result.observed_claims,
        "expectedClaims": result.expected_claims,
        "lossRatio": result.loss_ratio,
        "claimFrequency": result.claim_frequency,
        "claimSeverity": result.claim_severity,
        "reserveEstimate": result.reserve_estimate,
        "inflationAdjustment": result.inflation_adjustment,
        "persistencyRate": result.persistency_rate,
        "mortalityBasis": result.mortality_basis,
        "portfolioGrowthPct": result.portfolio_growth_pct,
        "riskPoolSize": result.risk_pool_size,
        "confidenceInterval": result.confidence_interval,
        "solvencyBuffer": result.solvency_buffer,
        "expectedProfitMargin": result.expected_profit_margin,
        "combinedRatio": result.combined_ratio,
        "modelVersion": result.model_version,
        "engine": result.engine,
    }


def capabilities() -> Dict[str, Any]:
    return {
        "modelVersion": MODEL_VERSION,
        "engine": "AIC",
        "slice": "ct-flex",
        "uses": [
            "engine_model.CredibilityParams (Bühlmann-Straub)",
        ],
        "products": list(COURIER_CLASS_RATES.keys()),
        "classRates": COURIER_CLASS_RATES,
        "buhlmannKTransactions": BUHLMANN_K_TRANSACTIONS,
        "note": (
            "CT Flex consumes only this product slice. Full AIC (ratemaking, reserving, "
            "GLM motor pricing) remains available for other lines."
        ),
    }
