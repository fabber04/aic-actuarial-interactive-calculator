# AIC Feature Dictionary — Actuarial Knowledge Layer (v1.0)

The AKL converts `StandardizedData` into a `FeatureVector`. Modules must not
compute premiums, GLM predictions, reserves, or underwriting decisions.

## Pipeline

```text
Raw → Product Adapter → StandardizedData
                         → features.aggregator (AKL)
                         → FeatureVector (+ feature_groups + metadata)
                         → Credibility → Risk → Decision
```

## Feature groups

| Group | Module | Examples |
|-------|--------|----------|
| Financial | `aic/features/financial.py` | income_stability, income_volatility, income_trend, transaction_frequency, income_diversity |
| Behavioural | `aic/features/behavioural.py` | activity_consistency, payment_regularity, earning_gap_score, engagement_score |
| Occupational | `aic/features/occupational.py` | occupation_risk (from `OccupationRiskTable`), occupation_safety |
| Environmental | `aic/features/environmental.py` | environmental_exposure, climate_sensitivity |

Composite **0–100** indices: `financial_index`, `behavioural_index`, `occupational_index`, `environmental_index`.

## Cross-product intent

| Feature | CT Flex | Motor | Health | Agriculture |
|---------|---------|-------|--------|-------------|
| Income stability | ✅ | — | ✅ | ✅ |
| Behaviour consistency | ✅ | ✅ | ✅ | ✅ |
| Occupation risk | ✅ | ✅ | ✅ | ✅ |
| Environmental exposure | ✅ | ✅ | ✅ | ✅ |

## Governance metadata

`FeatureVector.metadata` includes `feature_version`, `generated_at`, `generator`, `group_scores`.

## Occupation tables

Hazard scores live in `OccupationRiskTable`, not in function bodies. Actuaries revise scores via table overrides without changing algorithms.
