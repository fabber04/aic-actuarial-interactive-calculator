"""
AIC Platform v1.0 (RC1) — modular actuarial decision engine.

Mission: estimate expected claims/benefit cost and premiums; support reserving
and explainable insurance decisions for products such as CT Flex and motor.

Products never call models directly — they go through adapters → core → decision.

Submission freeze: bug fixes, presentation, and reviewer wording only.
See docs/submission/RELEASE_RC1.md and docs/ROADMAP.md.
"""

from aic.contracts import (
    DecisionResult,
    Explanation,
    FeatureVector,
    RiskResult,
    StandardizedData,
)

__version__ = "1.0.0"

__all__ = [
    "DecisionResult",
    "Explanation",
    "FeatureVector",
    "RiskResult",
    "StandardizedData",
    "__version__",
]
