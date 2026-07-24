"""Pure premium = expected loss cost (before expense / profit / tax loads)."""

from __future__ import annotations


def pure_premium_from_expected_loss(expected_loss: float) -> float:
    """Identity mapping: pure premium is the risk engine's E(Loss)."""
    return max(0.0, float(expected_loss))
