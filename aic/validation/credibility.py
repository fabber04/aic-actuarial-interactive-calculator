"""Credibility validation — Bühlmann–Straub monotone Z and class behaviour."""

from __future__ import annotations

from aic.core.credibility import BuhlmannStraubEngine, CredibilityContext, classify_credibility
from aic.validation.types import CheckResult, LayerReport


def validate_credibility(k: float = 50.0) -> LayerReport:
    report = LayerReport(
        layer="credibility",
        notes="Z = n/(n+k) must rise with exposure; classes follow published bands.",
    )
    engine = BuhlmannStraubEngine(k=k)

    exposures = [2.0, 8.0, 25.0, 50.0, 200.0]
    zs = []
    for n in exposures:
        result = engine.calculate(
            CredibilityContext(
                exposure=n,
                observation_count=n,
                individual_rate_proxy=0.03,
                collective_rate=0.0263,
                portfolio="validation",
            )
        )
        zs.append(result.z)
        expected = n / (n + k)
        report.checks.append(
            CheckResult(
                name=f"z_formula_n_{int(n)}",
                passed=abs(result.z - expected) < 5e-4,  # engine rounds Z to 4 d.p.
                detail=f"z={result.z} expected={expected:.6f}",
                metric=result.z,
                threshold=round(expected, 4),
            )
        )

    # Monotone non-decreasing in exposure
    monotone = all(zs[i] <= zs[i + 1] + 1e-12 for i in range(len(zs) - 1))
    report.checks.append(
        CheckResult(
            name="z_monotone_in_exposure",
            passed=monotone,
            detail=f"z_path={zs}",
        )
    )

    # Low exposure → Initial; high → Mature/Established
    low = engine.calculate(
        CredibilityContext(
            exposure=5.0,
            observation_count=5.0,
            individual_rate_proxy=0.03,
            collective_rate=0.0263,
        )
    )
    high = engine.calculate(
        CredibilityContext(
            exposure=200.0,
            observation_count=200.0,
            individual_rate_proxy=0.03,
            collective_rate=0.0263,
        )
    )
    report.checks.append(
        CheckResult(
            name="low_exposure_initial_or_emerging",
            passed=low.credibility_class in ("Initial", "Emerging"),
            detail=f"class={low.credibility_class} z={low.z}",
        )
    )
    report.checks.append(
        CheckResult(
            name="high_exposure_established_or_mature",
            passed=high.credibility_class in ("Established", "Mature"),
            detail=f"class={high.credibility_class} z={high.z}",
        )
    )

    # Blend identity: adjusted = z*ind + (1-z)*coll
    ind, coll, z = 0.04, 0.02, high.z
    expected_adj = z * ind + (1 - z) * coll
    blended = engine.calculate(
        CredibilityContext(
            exposure=200.0,
            observation_count=200.0,
            individual_rate_proxy=ind,
            collective_rate=coll,
        )
    )
    report.checks.append(
        CheckResult(
            name="credibility_blend_identity",
            passed=abs(blended.adjusted_rate - expected_adj) < 1e-6,
            detail=f"adj={blended.adjusted_rate} expected={expected_adj}",
            metric=blended.adjusted_rate,
        )
    )

    report.checks.append(
        CheckResult(
            name="class_bands_consistency",
            passed=classify_credibility(0.1) == "Initial"
            and classify_credibility(0.9) == "Mature",
            detail="band table smoke",
        )
    )

    return report
