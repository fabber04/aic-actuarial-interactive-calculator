"""Commercial discounts / credits applied after technical premium."""

from __future__ import annotations


def discount_amount(technical_premium: float, discount_ratio: float) -> float:
    ratio = max(0.0, min(0.95, float(discount_ratio)))
    return max(0.0, float(technical_premium) * ratio)


def apply_discount(technical_premium: float, discount_ratio: float) -> float:
    return max(0.0, float(technical_premium) - discount_amount(technical_premium, discount_ratio))
