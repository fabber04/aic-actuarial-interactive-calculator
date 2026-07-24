from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class StandardizedData:
    """Product-agnostic observations + context after Product Adapter transform."""

    product: str
    observations: List[Dict[str, Any]]
    context: Dict[str, Any] = field(default_factory=dict)
