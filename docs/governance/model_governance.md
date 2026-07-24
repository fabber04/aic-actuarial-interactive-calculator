# Model Governance

AIC treats models as governed actuarial assets, not disposable scripts.

## Principles

1. **Separation of concerns** — AKL, credibility, risk, pricing, and decision never collapse into one module.
2. **Version everything** — FeatureVector, CredibilityResult, and PricingResult carry method/version metadata.
3. **No silent hot-swap of tariff logic** — live GLM versioning exists; product rates and assumptions are explicit.
4. **Explainability is mandatory** — every quote exposes credibility drivers and pricing components.
5. **Validation before expansion** — new products (motor, health) land only after core validation passes.

## Owned artifacts

| Artifact | Location | Owner role |
|----------|----------|------------|
| Feature layer version | `FeatureVector.metadata.feature_version` | Actuarial / data |
| Credibility method | `CredibilityResult.metadata.method` | Pricing actuary |
| Pricing assumptions | `PricingResult.metadata.assumptions` | Pricing actuary |
| Decision rules | `aic/products/*/rules.py` | Product actuary |
| Validation suite | `python -m aic.validation` | Research / QA |

## Change control

- Changing occupation tables, class rates, or loading ratios requires updating `docs/governance/assumptions.md` and re-running the validation suite.
- Changing credibility strategy (e.g. adding Bayesian) requires a new `CredibilityEngine` implementation and suite checks — do not edit Decision Engine to compensate.
