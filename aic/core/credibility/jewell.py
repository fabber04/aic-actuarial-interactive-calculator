"""Future: Bühlmann–Jewell credibility strategy (placeholder)."""

from __future__ import annotations

from aic.core.credibility.base import CredibilityContext, CredibilityEngine, CredibilityResult


class BuhlmannJewellEngine(CredibilityEngine):
    method_name = "Bühlmann–Jewell"
    method_version = "0.0.0-placeholder"

    def calculate(self, context: CredibilityContext) -> CredibilityResult:
        raise NotImplementedError("Bühlmann–Jewell strategy is reserved for a future release")
