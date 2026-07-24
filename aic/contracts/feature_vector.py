"""Universal actuarial feature language for the core engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class FeatureVector:
    """
    Flattened actuarial feature language for credibility / risk / decision.

    ``feature_groups`` retains the Actuarial Knowledge Layer grouping for
    dashboards and composite indices (IRI, behavioural consistency, …).
    """

    product: str
    features: Dict[str, float] = field(default_factory=dict)
    exposure: float = 0.0
    claim_count: float = 0.0
    loss_history: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    feature_groups: Optional[Dict[str, Dict[str, float]]] = None
