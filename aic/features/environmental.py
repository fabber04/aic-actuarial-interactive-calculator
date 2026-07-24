"""
Environmental actuarial concepts — product-agnostic scaffold.

Geography / corridor / climate exposure placeholders for CT Flex, motor,
agriculture, and health. No GLM or pricing logic.
"""

from __future__ import annotations

from typing import Dict, Optional


# Illustrative corridor / urban exposure (0–1). Data-driven later.
_AREA_EXPOSURE = {
    "harare": 0.55,
    "bulawayo": 0.50,
    "urban": 0.55,
    "rural": 0.40,
    "highway": 0.70,
    "unknown": 0.50,
}


def environmental_exposure(
    area: str | None = None,
    *,
    corridor: str | None = None,
) -> float:
    """Combined environmental exposure score on [0, 1]."""
    key = (corridor or area or "unknown").strip().lower()
    return float(_AREA_EXPOSURE.get(key, _AREA_EXPOSURE["unknown"]))


def climate_sensitivity(area: str | None = None) -> float:
    """Placeholder climate sensitivity (agriculture / health later)."""
    if not area:
        return 0.45
    ruralish = area.strip().lower() in {"rural", "farm", "agriculture"}
    return 0.65 if ruralish else 0.40


def build_environmental_features(
    *,
    area: str | None = None,
    corridor: str | None = None,
) -> Dict[str, float]:
    return {
        "environmental_exposure": round(environmental_exposure(area, corridor=corridor), 4),
        "climate_sensitivity": round(climate_sensitivity(area), 4),
    }


def environmental_group_score(features: Dict[str, float]) -> float:
    """Composite 0–100 (higher = lower environmental pressure)."""
    exposure = features.get("environmental_exposure", 0.5)
    climate = features.get("climate_sensitivity", 0.5)
    safety = 1.0 - 0.6 * exposure - 0.4 * climate
    return round(max(0.0, min(100.0, safety * 100.0)), 1)
