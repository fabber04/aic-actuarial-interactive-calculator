"""
Actuarial Knowledge Layer aggregator.

Orchestrates financial / behavioural / occupational / environmental groups into
a FeatureVector. No pricing, GLM, reserves, or decision rules.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from aic.contracts.data_objects import StandardizedData
from aic.contracts.feature_vector import FeatureVector
from aic.features.behavioural import (
    behavioural_group_score,
    build_behavioural_features,
)
from aic.features.environmental import (
    build_environmental_features,
    environmental_group_score,
)
from aic.features.financial import build_financial_features, financial_group_score
from aic.features.occupational import (
    OccupationRiskTable,
    build_occupational_features,
    occupational_group_score,
)
from aic.features.series import income_amounts, observation_dates

FEATURE_LAYER_VERSION = "1.0.0"
GENERATOR_ID = "akl_aggregator_v1"


def flatten_groups(groups: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    flat: Dict[str, float] = {}
    for _group_name, feats in groups.items():
        for key, value in feats.items():
            flat[key] = float(value)
    return flat


def group_index_scores(groups: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """Dashboard-ready 0–100 composites per feature group."""
    return {
        "financial_index": financial_group_score(groups.get("financial", {})),
        "behavioural_index": behavioural_group_score(groups.get("behavioural", {})),
        "occupational_index": occupational_group_score(groups.get("occupational", {})),
        "environmental_index": environmental_group_score(groups.get("environmental", {})),
    }


def build_feature_groups(
    data: StandardizedData,
    *,
    occupation_table: Optional[OccupationRiskTable] = None,
) -> Dict[str, Dict[str, float]]:
    values = income_amounts(data.observations)
    dates = observation_dates(data.observations)
    ctx = data.context or {}
    declared = ctx.get("transaction_count")
    declared_f = float(declared) if declared is not None else None

    financial = build_financial_features(values, declared_count=declared_f)
    behavioural = build_behavioural_features(
        values,
        declared_count=declared_f,
        platform=ctx.get("platform"),
        dates=dates,
    )
    occupational = build_occupational_features(
        ctx.get("occupation"),
        table=occupation_table,
    )
    environmental = build_environmental_features(
        area=ctx.get("area") or ctx.get("city"),
        corridor=ctx.get("corridor"),
    )
    return {
        "financial": financial,
        "behavioural": behavioural,
        "occupational": occupational,
        "environmental": environmental,
    }


def build_feature_vector(
    data: StandardizedData,
    *,
    occupation_table: Optional[OccupationRiskTable] = None,
    extra_features: Optional[Dict[str, float]] = None,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> FeatureVector:
    """
    Actuarial Knowledge Layer entry point.

    Builds grouped features, flattens to FeatureVector.features, and attaches
    governance metadata + group composites.
    """
    groups = build_feature_groups(data, occupation_table=occupation_table)
    flat = flatten_groups(groups)
    if extra_features:
        flat.update({k: float(v) for k, v in extra_features.items()})

    indices = group_index_scores(groups)
    # Also expose indices on the flat vector for simple consumers
    flat.update(indices)

    txn_n = flat.get("transaction_frequency", float(len(data.observations)))
    metadata: Dict[str, Any] = {
        "feature_version": FEATURE_LAYER_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": GENERATOR_ID,
        "group_scores": indices,
    }
    if occupation_table is not None:
        metadata["occupation_table_version"] = occupation_table.version
    if metadata_extra:
        metadata.update(metadata_extra)

    return FeatureVector(
        product=data.product,
        features=flat,
        exposure=float(txn_n),
        claim_count=0.0,
        loss_history=[],
        metadata=metadata,
        feature_groups=groups,
    )
