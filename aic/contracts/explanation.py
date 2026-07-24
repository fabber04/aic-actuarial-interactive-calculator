from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ExplanationFactor:
    name: str
    impact: str
    detail: str = ""


@dataclass
class Explanation:
    summary: str
    factors: List[ExplanationFactor] = field(default_factory=list)
    confidence: float = 0.0
