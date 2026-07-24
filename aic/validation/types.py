"""
AIC Research Validation Framework — shared result types.

Validates actuarial methodology layer-by-layer. Does not set premiums or
override product decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    metric: Optional[float] = None
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LayerReport:
    layer: str
    checks: List[CheckResult] = field(default_factory=list)
    notes: str = ""

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks) if self.checks else False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer": self.layer,
            "passed": self.passed,
            "notes": self.notes,
            "checks": [c.to_dict() for c in self.checks],
        }


@dataclass
class ValidationSuiteReport:
    suite: str = "aic_research_validation"
    version: str = "1.0.0"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    layers: List[LayerReport] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(layer.passed for layer in self.layers) if self.layers else False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite": self.suite,
            "version": self.version,
            "generated_at": self.generated_at,
            "passed": self.passed,
            "layers": [layer.to_dict() for layer in self.layers],
        }
