"""Indicated commercial premium after discounts and minimum premium floors."""

from __future__ import annotations

from aic.core.pricing.base import PricingAssumptions
from aic.core.pricing.discounts import apply_discount, discount_amount


def commercial_premium(
    technical: float,
    assumptions: PricingAssumptions,
) -> tuple[float, float]:
    """
    Returns (commercial_premium, discount_amount).

    Still actuarial indicated commercial — not product packaging (PAYG / annual).
    """
    disc = discount_amount(technical, assumptions.discount_ratio)
    commercial = apply_discount(technical, assumptions.discount_ratio)
    commercial = max(float(assumptions.min_premium), commercial)
    return commercial, disc
