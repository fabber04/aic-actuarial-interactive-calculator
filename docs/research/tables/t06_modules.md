# Table T6 — Module Responsibilities

| Package | Responsibility | Does *not* |
|---------|----------------|------------|
| `products/` | Adapter + product rules | Call GLM/credibility directly |
| `features/` | AKL concepts → FeatureVector | Price or decide |
| `core/credibility/` | Individual vs collective weight | Set premiums |
| `core/risk_engine/` | E[loss] | Commercial packaging |
| `core/pricing/` | Pure → technical → indicated commercial | PAYG / bind-refer |
| `decision/` | Product outcome | Actuarial loading mathematics |
| `core/explainability/` | Human-readable factors | Change the decision |
| `validation/` | Layer consistency evidence | Train models |
| `benchmark/` | Prototype vs platform comparison | Claim loss outperformance |
