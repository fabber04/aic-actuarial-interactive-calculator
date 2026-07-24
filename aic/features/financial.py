"""
Financial actuarial concepts — product-agnostic.

Transforms income / payment observation series into knowledge features.
No GLM, premium, reserve, or decision logic.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence


def average_income(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def income_variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = average_income(values)
    return sum((x - mean) ** 2 for x in values) / len(values)


def income_volatility(values: Sequence[float]) -> float:
    """Coefficient of variation mapped to [0, 1] (higher = more volatile)."""
    mean = average_income(values)
    if mean <= 0 or len(values) < 2:
        return 0.5 if not values else 0.0
    cv = math.sqrt(income_variance(values)) / mean
    return max(0.0, min(1.0, cv / 1.5))


def income_stability(values: Sequence[float]) -> float:
    """Inverse of volatility on [0, 1] (higher = more stable)."""
    if len(values) < 2:
        return 0.4
    return max(0.0, min(1.0, 1.0 - income_volatility(values)))


def income_trend(values: Sequence[float]) -> float:
    """
    Simple linear slope of income vs index, scaled relative to mean.
    Positive → growing; negative → declining. Clipped to [-1, 1].
    """
    n = len(values)
    if n < 2:
        return 0.0
    mean = average_income(values)
    if mean <= 0:
        return 0.0
    x_mean = (n - 1) / 2.0
    num = sum((i - x_mean) * (values[i] - mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den <= 0:
        return 0.0
    slope = num / den
    return max(-1.0, min(1.0, slope / mean))


def transaction_frequency(values: Sequence[float], *, declared_count: float | None = None) -> float:
    """Observation count, or declared volume when provided (e.g. platform txn count)."""
    if declared_count is not None and declared_count > 0:
        return float(declared_count)
    return float(len(values))


def income_growth(values: Sequence[float]) -> float:
    """(last - first) / first, clipped to [-1, 2]."""
    if len(values) < 2:
        return 0.0
    first = values[0]
    if first == 0:
        return 0.0
    g = (values[-1] - first) / abs(first)
    return max(-1.0, min(2.0, g))


def income_concentration(values: Sequence[float]) -> float:
    """
    Herfindahl-style concentration of absolute incomes on [0, 1].
    1 = single observation dominates; ~1/n = even spread.
    """
    if not values:
        return 0.0
    abs_vals = [abs(x) for x in values]
    total = sum(abs_vals)
    if total <= 0:
        return 0.0
    shares = [x / total for x in abs_vals]
    hhi = sum(s * s for s in shares)
    # Rescale so uniform n → ~0, single → 1
    n = len(values)
    if n <= 1:
        return 1.0
    return max(0.0, min(1.0, (hhi - 1.0 / n) / (1.0 - 1.0 / n)))


def income_diversity(values: Sequence[float]) -> float:
    """1 - concentration (higher = more diversified earning pattern)."""
    return max(0.0, min(1.0, 1.0 - income_concentration(values)))


def average_weekly_income(values: Sequence[float], *, days_per_week: float = 5.0) -> float:
    """Mean observation treated as a job/day amount → weekly proxy."""
    if not values:
        return 0.0
    return average_income(values) * days_per_week


def build_financial_features(
    values: Sequence[float],
    *,
    declared_count: float | None = None,
) -> Dict[str, float]:
    """Compute the financial feature group."""
    vals = [float(v) for v in values]
    return {
        "average_income": round(average_income(vals), 4),
        "average_weekly_income": round(average_weekly_income(vals), 2),
        "income_variance": round(income_variance(vals), 4),
        "income_volatility": round(income_volatility(vals), 4),
        "income_stability": round(income_stability(vals), 4),
        "income_trend": round(income_trend(vals), 4),
        "transaction_frequency": round(transaction_frequency(vals, declared_count=declared_count), 4),
        "income_growth": round(income_growth(vals), 4),
        "income_concentration": round(income_concentration(vals), 4),
        "income_diversity": round(income_diversity(vals), 4),
    }


def financial_group_score(features: Dict[str, float]) -> float:
    """Composite 0–100: stability + diversity − volatility (illustrative)."""
    stability = features.get("income_stability", 0.5)
    diversity = features.get("income_diversity", 0.5)
    volatility = features.get("income_volatility", 0.5)
    trend = max(0.0, features.get("income_trend", 0.0))
    raw = 0.45 * stability + 0.25 * diversity + 0.15 * (1.0 - volatility) + 0.15 * (0.5 + 0.5 * trend)
    return round(max(0.0, min(100.0, raw * 100.0)), 1)
