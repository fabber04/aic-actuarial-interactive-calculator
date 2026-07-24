from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskResult:
    """Risk Engine output — expected liability, NOT commercial premium."""

    expected_loss: float
    confidence: float
    model_name: str
    model_version: str
    credibility_z: float = 0.0
    risk_class: str = "Medium"
