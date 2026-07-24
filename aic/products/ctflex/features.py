"""
CT Flex product feature entry — thin product overlay on the Actuarial Knowledge Layer.

Product-specific credibility hints live here; actuarial concepts live in ``aic.features``.
"""

from __future__ import annotations

from aic.contracts.data_objects import StandardizedData
from aic.contracts.feature_vector import FeatureVector
from aic.features.aggregator import build_feature_vector
from aic.products.ctflex.rules import CLASS_RATE_INCOME


def generate_ctflex_features(data: StandardizedData) -> FeatureVector:
    """
    Build CT Flex FeatureVector via AKL aggregator + Income class-rate proxy.

    ``individual_rate_proxy`` is a credibility input (experience indication),
    not a commercial premium.
    """
    # Pre-build groups path: we need stability for the proxy — two-pass light:
    fv = build_feature_vector(
        data,
        metadata_extra={"product_slice": "ctflex", "generator": "ctflex_features_v1"},
    )
    stability = float(fv.features.get("income_stability", 0.4))
    individual_proxy = CLASS_RATE_INCOME * (1.1 - 0.2 * stability)
    fv.features["individual_rate_proxy"] = round(individual_proxy, 6)
    fv.metadata["generator"] = "ctflex_akl_v1"
    return fv
