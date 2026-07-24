"""
Behavioural actuarial concepts — product-agnostic.

Models consistency of activity and engagement from observation patterns.
No GLM, premium, reserve, or decision logic.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence


def activity_consistency(values: Sequence[float]) -> float:
    """
    Fraction of observations that are strictly positive (active earning events).
    Thin or empty history → low consistency.
    """
    if not values:
        return 0.0
    active = sum(1 for v in values if v > 0)
    return active / len(values)


def payment_regularity(values: Sequence[float]) -> float:
    """
    Regularity of magnitudes: 1 - normalized mean absolute successive difference.
    """
    if len(values) < 2:
        return 0.5 if values else 0.0
    mean = sum(abs(v) for v in values) / len(values)
    if mean <= 0:
        return 0.0
    diffs = [abs(values[i] - values[i - 1]) for i in range(1, len(values))]
    mad = sum(diffs) / len(diffs)
    return max(0.0, min(1.0, 1.0 - min(mad / mean, 1.5) / 1.5))


def coverage_persistence(values: Sequence[float], *, min_active: int = 3) -> float:
    """Proxy for continued cover eligibility: length of positive streak vs history."""
    if not values:
        return 0.0
    streak = 0
    best = 0
    for v in values:
        if v > 0:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    if best < min_active and len(values) < min_active:
        return max(0.0, best / max(min_active, 1))
    return max(0.0, min(1.0, best / max(len(values), 1)))


def earning_gap_score(values: Sequence[float]) -> float:
    """
    Share of zero/near-zero observations (gaps). Higher = more gaps (riskier).
    """
    if not values:
        return 1.0
    gaps = sum(1 for v in values if v <= 0)
    return gaps / len(values)


def engagement_score(
    values: Sequence[float],
    *,
    declared_count: float | None = None,
    full_engagement_n: float = 50.0,
) -> float:
    """Volume engagement toward a full-credibility-style reference count."""
    n = float(declared_count) if declared_count and declared_count > 0 else float(len(values))
    if full_engagement_n <= 0:
        return 0.0
    return max(0.0, min(1.0, n / full_engagement_n))


def renewal_consistency(values: Sequence[float]) -> float:
    """
    Proxy for renewal-like stickiness: activity_consistency × payment_regularity.
    """
    return activity_consistency(values) * payment_regularity(values)


def platform_dependency(platform: str | None = None) -> float:
    """
    Illustrative single-platform dependency (0–1). Multi-platform products can
    override via context later; default assumes high dependency on one platform.
    """
    if not platform:
        return 0.70
    # Known gig platforms → high dependency; unknown → slightly lower
    known = {"bolt", "indrive", "uber", "ecocash", "mukuru"}
    return 0.75 if str(platform).lower() in known else 0.65


def build_behavioural_features(
    values: Sequence[float],
    *,
    declared_count: float | None = None,
    platform: str | None = None,
    dates: Sequence[Optional[str]] | None = None,
) -> Dict[str, float]:
    """Compute the behavioural feature group. ``dates`` reserved for future cadence."""
    _ = dates  # future: inter-arrival regularity
    vals = [float(v) for v in values]
    return {
        "activity_consistency": round(activity_consistency(vals), 4),
        "payment_regularity": round(payment_regularity(vals), 4),
        "coverage_persistence": round(coverage_persistence(vals), 4),
        "earning_gap_score": round(earning_gap_score(vals), 4),
        "engagement_score": round(
            engagement_score(vals, declared_count=declared_count), 4
        ),
        "renewal_consistency": round(renewal_consistency(vals), 4),
        "platform_dependency": round(platform_dependency(platform), 4),
    }


def behavioural_group_score(features: Dict[str, float]) -> float:
    """Composite 0–100 behavioural consistency index."""
    parts = [
        features.get("activity_consistency", 0.0),
        features.get("payment_regularity", 0.0),
        features.get("coverage_persistence", 0.0),
        features.get("engagement_score", 0.0),
        features.get("renewal_consistency", 0.0),
        1.0 - features.get("earning_gap_score", 0.0),
    ]
    raw = sum(parts) / len(parts)
    return round(max(0.0, min(100.0, raw * 100.0)), 1)
