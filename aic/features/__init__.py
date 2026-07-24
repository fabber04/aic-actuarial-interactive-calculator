"""
Actuarial Knowledge Layer (AKL).

Transforms StandardizedData into FeatureVector via financial, behavioural,
occupational, and environmental concept modules. No GLM / premium / reserves /
decision logic.
"""

from aic.features.aggregator import (
    FEATURE_LAYER_VERSION,
    build_feature_groups,
    build_feature_vector,
    flatten_groups,
    group_index_scores,
)
from aic.features.occupational import DEFAULT_OCCUPATION_TABLE, OccupationRiskTable

__all__ = [
    "FEATURE_LAYER_VERSION",
    "OccupationRiskTable",
    "DEFAULT_OCCUPATION_TABLE",
    "build_feature_groups",
    "build_feature_vector",
    "flatten_groups",
    "group_index_scores",
]
