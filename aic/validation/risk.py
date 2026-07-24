"""Risk engine validation — class-rate path + optional Gamma deviance smoke."""

from __future__ import annotations

from aic.contracts.feature_vector import FeatureVector
from aic.core.credibility.base import CredibilityResult
from aic.core.risk_engine import ClassRateRiskEngine
from aic.validation.types import CheckResult, LayerReport


def validate_risk_engine() -> LayerReport:
    report = LayerReport(
        layer="risk_engine",
        notes=(
            "Class-rate engine: E[loss] scales with income and adjusted rate. "
            "Gamma GLM holdout metrics live in portfolio workflows when models are trained."
        ),
    )
    engine = ClassRateRiskEngine()
    features = FeatureVector(
        product="ctflex_income",
        features={"average_weekly_income": 50.0},
        exposure=10.0,
    )
    cred = CredibilityResult(
        credibility_factor=0.5,
        adjusted_risk=0.0263,
        individual_rate=0.03,
        collective_rate=0.0263,
    )
    result = engine.predict(features, cred)
    expected = 0.0263 * 50.0 * 4.0
    report.checks.append(
        CheckResult(
            name="class_rate_expected_loss_identity",
            passed=abs(result.expected_loss - expected) < 1e-4,
            detail=f"loss={result.expected_loss} expected={expected}",
            metric=result.expected_loss,
            threshold=expected,
        )
    )
    report.checks.append(
        CheckResult(
            name="expected_loss_positive",
            passed=result.expected_loss > 0,
            detail=f"loss={result.expected_loss}",
            metric=result.expected_loss,
        )
    )
    report.checks.append(
        CheckResult(
            name="credibility_z_propagated",
            passed=abs(result.credibility_z - 0.5) < 1e-9,
            detail=f"z={result.credibility_z}",
        )
    )
    return report
