"""
Faithful Python mirror of CT Flex ``actuarial.ts`` local prototype.

Source of truth: CT FLEX MVP/ct-flex/src/engine/actuarial.ts
Used only for actuarial-system benchmarking — not for production quotes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Literal

MODEL_VERSION = "ct-flex-1.0.0-local-fallback"
BUHLMANN_K_TRANSACTIONS = 50

ProductCode = Literal["income", "health", "life"]

COURIER_CLASS_RATES: Dict[ProductCode, float] = {
    "income": 0.0263,
    "health": 0.0303,
    "life": 0.0163,
}


@dataclass
class PrototypeFactor:
    id: str
    label: str
    bps: int
    explanation: str


@dataclass
class PrototypeUnderwriting:
    approved: bool
    risk_rating: str
    income_estimate_usd: int
    premium_rate: float
    coverage_usd: int
    confidence_score: int
    credibility_z: float
    transaction_count: int
    class_rate: float
    factors: List[PrototypeFactor]
    model_version: str = MODEL_VERSION
    engine: str = "ct-flex-actuarial.ts"


def credibility_factor(n: float, k: float = BUHLMANN_K_TRANSACTIONS) -> float:
    if n <= 0:
        return 0.0
    return n / (n + k)


def build_premium_factors(z: float) -> List[PrototypeFactor]:
    credibility_adj = -5 if z < 0.25 else int(round((1 - z) * -5))
    return [
        PrototypeFactor(
            id="income",
            label="Income consistency",
            bps=18,
            explanation="EcoCash inflow variance over 90 days is within courier class tolerance.",
        ),
        PrototypeFactor(
            id="occupation",
            label="Occupation risk",
            bps=9,
            explanation="Bolt courier classification mapped to IPEC microinsurance occupation table.",
        ),
        PrototypeFactor(
            id="platform",
            label="Platform reliability",
            bps=12,
            explanation="Completion rate 94.2% and average rider rating 4.7.",
        ),
        PrototypeFactor(
            id="claims",
            label="Claim history",
            bps=0,
            explanation="No prior CT Flex claims on record.",
        ),
        PrototypeFactor(
            id="credibility",
            label="Credibility adjustment",
            bps=credibility_adj,
            explanation=f"Bühlmann-Straub Z = {z:.2f}. Thin history pulls toward class (k={BUHLMANN_K_TRANSACTIONS}).",
        ),
        PrototypeFactor(
            id="inflation",
            label="Inflation adjustment",
            bps=3,
            explanation="Zimbabwe CPI medical and motor index blend at 3 bps.",
        ),
    ]


def compute_underwriting(
    transaction_count: int,
    product: ProductCode = "income",
) -> PrototypeUnderwriting:
    """Mirror of actuarial.ts ``computeUnderwriting`` — ignores income path shape."""
    z = credibility_factor(float(transaction_count), BUHLMANN_K_TRANSACTIONS)
    class_rate = COURIER_CLASS_RATES[product]
    factors = build_premium_factors(z)
    factor_sum_bps = sum(f.bps for f in factors)
    premium_rate = round(class_rate + factor_sum_bps / 10000.0, 4)
    income_estimate = round(420 + transaction_count * 18.5)
    coverage = round(income_estimate * 0.6)

    risk_rating = "Low"
    if z < 0.25:
        risk_rating = "Moderate"
    if transaction_count < 5:
        risk_rating = "Elevated"

    return PrototypeUnderwriting(
        approved=True,
        risk_rating=risk_rating,
        income_estimate_usd=income_estimate,
        premium_rate=premium_rate,
        coverage_usd=coverage,
        confidence_score=round(55 + z * 40),
        credibility_z=round(z, 2),
        transaction_count=transaction_count,
        class_rate=class_rate,
        factors=factors,
    )
