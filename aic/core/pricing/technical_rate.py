"""
Technical premium assembly.

Uses the classical permissive loading formula:

  technical = (pure_premium + fixed_expense) / (1 - v - p - r - t)

where v, p, r, t are variable expense, profit, risk margin, and tax ratios.
"""

from __future__ import annotations

from aic.core.pricing.base import PricingAssumptions


def technical_premium(
    pure_premium: float,
    assumptions: PricingAssumptions,
) -> float:
    pure = max(0.0, float(pure_premium))
    fixed = max(0.0, float(assumptions.fixed_expense))
    denom = (
        1.0
        - float(assumptions.expense_ratio)
        - float(assumptions.profit_load)
        - float(assumptions.risk_margin)
        - float(assumptions.tax_fee_ratio)
    )
    if denom <= 0.05:
        denom = 0.05
    return (pure + fixed) / denom


def decompose_technical(
    pure_premium: float,
    technical: float,
    assumptions: PricingAssumptions,
) -> dict[str, float]:
    """Attribute loadings implied by the technical premium for transparency."""
    pure = max(0.0, float(pure_premium))
    tech = max(0.0, float(technical))
    expense = tech * float(assumptions.expense_ratio)
    profit = tech * float(assumptions.profit_load)
    risk_m = tech * float(assumptions.risk_margin)
    tax = tech * float(assumptions.tax_fee_ratio)
    fixed = max(0.0, float(assumptions.fixed_expense))
    return {
        "pure_premium": round(pure, 6),
        "fixed_expense": round(fixed, 6),
        "expense_loading": round(expense, 6),
        "profit_loading": round(profit, 6),
        "risk_margin": round(risk_m, 6),
        "taxes_fees": round(tax, 6),
        "technical_premium": round(tech, 6),
    }
