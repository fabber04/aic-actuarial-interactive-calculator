# Validation Framework

**Purpose:** Provide measurable evidence that AIC's actuarial layers behave as designed — for researchers, supervisors, and competition judges.

## How to run

```bash
python -m aic.validation
python -m aic.validation --json
```

## Layer checks

| Layer | What we measure |
|-------|-----------------|
| **AKL** | Feature ranges; stability orders volatile vs stable series; metadata/groups present |
| **Credibility** | \(Z=n/(n+k)\) identity; monotone in exposure; class bands; blend identity |
| **Risk** | Class-rate E[loss] identity; positivity; Z propagation |
| **Pricing** | Technical ≥ pure; classical loading identity; commercial floor |
| **Decision / Explain** | Thin history → Refer; rich → Approved; PAYG rate > 0; explanations cite credibility & pricing |

## Pass criterion

All checks in all layers must pass (`OVERALL: PASS`).

## What this is not

- Not a full CAS exam syllabus proof
- Not a regulatory capital model
- Not a substitute for portfolio-level GLM holdout (that lives in `portfolio_motor` / `fremtpl_glm` workflows when models are trained)

## Extension

Add a new file under `aic/validation/`, register it in `suite.py`, and document the check here.
