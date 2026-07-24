from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DecisionResult:
    """Decision Engine output — insurance outcome for a product."""

    decision: str  # Approved | Refer | Decline
    premium: float
    benefit: float
    status: str  # ACTIVE | GRACE | LAPSED | REFER
    risk_class: str
    payment_method: str = "PAYG"
    premium_rate: Optional[float] = None
    extras: Dict[str, Any] = field(default_factory=dict)
