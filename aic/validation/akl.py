"""AKL validation — feature stability and admissible ranges."""

from __future__ import annotations

from aic.contracts.data_objects import StandardizedData
from aic.features import build_feature_vector
from aic.validation.types import CheckResult, LayerReport


def _stable_series() -> StandardizedData:
    return StandardizedData(
        product="validation",
        observations=[{"income": 12.0 + (i % 3) * 0.5} for i in range(20)],
        context={"occupation": "Courier", "platform": "Bolt", "transaction_count": 20},
    )


def _volatile_series() -> StandardizedData:
    vals = [5, 40, 2, 55, 1, 60, 3, 50]
    return StandardizedData(
        product="validation",
        observations=[{"income": float(v)} for v in vals],
        context={"occupation": "Driver", "platform": "Bolt", "transaction_count": len(vals)},
    )


def validate_akl() -> LayerReport:
    report = LayerReport(
        layer="akl",
        notes="Features must be finite, in documented ranges, and respond to volatility.",
    )
    stable = build_feature_vector(_stable_series())
    volatile = build_feature_vector(_volatile_series())

    # Range checks on key [0,1] concepts
    for key in (
        "income_stability",
        "income_volatility",
        "activity_consistency",
        "occupation_risk",
    ):
        v = stable.features.get(key)
        ok = v is not None and 0.0 <= float(v) <= 1.0
        report.checks.append(
            CheckResult(
                name=f"range_{key}",
                passed=ok,
                detail=f"{key}={v}",
                metric=None if v is None else float(v),
                threshold=1.0,
            )
        )

    # Stability should be higher for stable series than volatile
    s_stab = float(stable.features["income_stability"])
    v_stab = float(volatile.features["income_stability"])
    report.checks.append(
        CheckResult(
            name="stability_orders_series",
            passed=s_stab > v_stab,
            detail=f"stable={s_stab:.4f} volatile={v_stab:.4f}",
            metric=s_stab - v_stab,
            threshold=0.0,
        )
    )

    # Metadata / groups present for governance
    report.checks.append(
        CheckResult(
            name="metadata_present",
            passed=bool(stable.metadata.get("feature_version"))
            and stable.feature_groups is not None,
            detail=f"version={stable.metadata.get('feature_version')}",
        )
    )

    # Index scores in 0–100
    for idx in ("financial_index", "behavioural_index"):
        val = float(stable.features.get(idx, -1))
        report.checks.append(
            CheckResult(
                name=f"index_range_{idx}",
                passed=0.0 <= val <= 100.0,
                detail=f"{idx}={val}",
                metric=val,
                threshold=100.0,
            )
        )

    return report
