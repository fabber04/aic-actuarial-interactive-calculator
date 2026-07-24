"""Decision + explainability validation — rule consistency and explanation linkage."""

from __future__ import annotations

from aic.orchestrator import AICPlatform
from aic.validation.types import CheckResult, LayerReport


def validate_decision_and_explainability() -> LayerReport:
    report = LayerReport(
        layer="decision_explainability",
        notes="Thin history should Refer; explanations must cite credibility drivers.",
    )
    platform = AICPlatform()

    thin = platform.quote_ctflex(
        {
            "occupation": "Courier",
            "transaction_count": 2,
            "transactions": [5.0, 6.0],
        }
    )
    rich = platform.quote_ctflex(
        {
            "occupation": "Courier",
            "transaction_count": 40,
            "transactions": [10.0 + (i % 5) for i in range(40)],
        }
    )

    report.checks.append(
        CheckResult(
            name="thin_history_refer",
            passed=thin["decision"] == "Refer" and thin["status"] == "REFER",
            detail=f"decision={thin['decision']} z={thin['credibility_z']}",
        )
    )
    report.checks.append(
        CheckResult(
            name="rich_history_approved",
            passed=rich["decision"] == "Approved" and rich["status"] == "ACTIVE",
            detail=f"decision={rich['decision']} z={rich['credibility_z']}",
        )
    )
    report.checks.append(
        CheckResult(
            name="payg_rate_positive",
            passed=float(rich["premium_rate"]) > 0,
            detail=f"premium_rate={rich['premium_rate']}",
            metric=float(rich["premium_rate"]),
        )
    )
    report.checks.append(
        CheckResult(
            name="pricing_before_decision",
            passed=float(rich["technical_premium"]) > 0
            and float(rich["commercial_premium"]) > 0,
            detail=(
                f"technical={rich['technical_premium']} "
                f"commercial={rich['commercial_premium']}"
            ),
        )
    )

    # Explainability consistent with inputs
    drivers = thin.get("credibility_drivers") or []
    factors = (thin.get("explanation") or {}).get("factors") or []
    factor_text = " ".join(
        f"{f.get('name', '')} {f.get('detail', '')}" for f in factors
    ).lower()
    report.checks.append(
        CheckResult(
            name="explanation_mentions_credibility",
            passed=bool(drivers) and "credibility" in factor_text,
            detail=f"drivers={len(drivers)} factors={len(factors)}",
        )
    )
    report.checks.append(
        CheckResult(
            name="explanation_includes_pricing_terms",
            passed="technical" in factor_text or "pure premium" in factor_text,
            detail="pricing factors present in explanation",
        )
    )

    return report
