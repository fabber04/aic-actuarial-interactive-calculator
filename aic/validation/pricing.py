"""Pricing validation — technical premium covers pure premium under loads."""

from __future__ import annotations

from aic.contracts.risk_result import RiskResult
from aic.core.pricing import PricingAssumptions, StandardPricingEngine
from aic.validation.types import CheckResult, LayerReport


def validate_pricing() -> LayerReport:
    report = LayerReport(
        layer="pricing",
        notes="Technical premium must cover pure premium when loads are non-negative.",
    )
    engine = StandardPricingEngine()
    risk = RiskResult(
        expected_loss=120.0,
        confidence=0.8,
        model_name="validation",
        model_version="1",
        credibility_z=0.5,
    )
    assumptions = PricingAssumptions(
        expense_ratio=0.12,
        profit_load=0.05,
        risk_margin=0.03,
        tax_fee_ratio=0.0,
        portfolio="validation",
    )
    priced = engine.price(risk, assumptions)

    report.checks.append(
        CheckResult(
            name="technical_covers_pure",
            passed=priced.technical_premium >= priced.pure_premium - 1e-9,
            detail=(
                f"technical={priced.technical_premium} pure={priced.pure_premium}"
            ),
            metric=priced.technical_premium - priced.pure_premium,
        )
    )
    # Exact classical identity for these assumptions: 120 / 0.80 = 150
    report.checks.append(
        CheckResult(
            name="technical_formula_identity",
            passed=abs(priced.technical_premium - 150.0) < 1e-6,
            detail=f"technical={priced.technical_premium}",
            metric=priced.technical_premium,
            threshold=150.0,
        )
    )
    report.checks.append(
        CheckResult(
            name="commercial_at_least_min_premium",
            passed=priced.commercial_premium >= assumptions.min_premium - 1e-9,
            detail=f"commercial={priced.commercial_premium}",
        )
    )
    report.checks.append(
        CheckResult(
            name="component_sum_reconcilable",
            passed=priced.components.get("technical_premium", 0) == priced.technical_premium,
            detail="components mirror technical_premium field",
        )
    )
    return report
