# AIC Credibility Framework

The Credibility Layer answers one question only:

> How much weight should we place on this individual's own experience versus the collective?

It does **not** set premiums, benefits, approvals, or pricing rules.

## Strategies

```text
CredibilityEngine  (interface)
├── Bühlmann–Straub     ✅ aic/core/credibility/buhlmann.py
├── Bühlmann–Jewell     ⏳ placeholder
├── Bayesian            ⏳ future
└── Custom AIC          ⏳ future
```

## Contracts

### CredibilityContext (inputs)

Built from `FeatureVector` but **excluding** occupation risk, premiums, and expected loss.

| Field | Role |
|-------|------|
| `exposure` | Volume for Z |
| `observation_count` | Diagnostics / confidence |
| `individual_rate_proxy` | Individual indication |
| `collective_rate` | Portfolio / class rate |
| `loss_history` | Optional experience |
| `group_scores` | financial/behavioural indices for diagnostics only |
| `portfolio` | Governance label |

### CredibilityResult (outputs)

| Field | Meaning |
|-------|---------|
| `z` / `credibility_factor` | Credibility weight |
| `credibility_class` | Initial / Emerging / Established / Mature |
| `adjusted_rate` / `adjusted_risk` | Z·individual + (1−Z)·collective |
| `drivers` | Why Z is high/low (explainability) |
| `confidence` | Confidence in the Z estimate |
| `metadata` | method, version, portfolio, inputs_used, timestamp |

## Credibility classes

| Z range | Class |
|---------|--------|
| 0.00–0.20 | Initial |
| 0.20–0.50 | Emerging |
| 0.50–0.80 | Established |
| 0.80–1.00 | Mature |

## Pipeline position

```text
AKL FeatureVector → CredibilityContext → CredibilityEngine → CredibilityResult
                         → RiskEngine → DecisionEngine → Explainability
```
