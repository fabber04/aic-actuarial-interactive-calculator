# Table T1 — Feature Groups (AKL)

| Group | Module | Example concepts |
|-------|--------|------------------|
| Financial | `aic/features/financial.py` | income_stability, income_volatility, income_trend, transaction_frequency |
| Behavioural | `aic/features/behavioural.py` | activity_consistency, payment_regularity, earning_gap_score |
| Occupational | `aic/features/occupational.py` | occupation_risk (OccupationRiskTable), occupation_safety |
| Environmental | `aic/features/environmental.py` | environmental_exposure, climate_sensitivity |

Composite indices (0–100): `financial_index`, `behavioural_index`, `occupational_index`, `environmental_index`.
