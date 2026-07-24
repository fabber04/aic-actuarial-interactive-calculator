# AIC Platform Architecture v2

## Mission

AIC is a **premium and claims decision engine**. It estimates expected insurance liability (claims / benefit cost), prices that loss cost into a technical / indicated commercial premium, then applies product rules (e.g. PAYG) to produce the insurance decision and explanation.

CEO framing: **premiums and claims** — credibility, GLM, reserving, and pricing support those decisions.

## Pipeline

```text
RAW DATA
   → Product Adapter
   → Actuarial Knowledge Layer (AKL)
   → FeatureVector (+ metadata / groups)
   → Credibility Framework
   → Risk Engine  →  RiskResult (expected loss)
   → Pricing Engine  →  technical / indicated commercial premium
   → Decision Engine  →  product packaging (PAYG, bind/refer, benefits)
   → Explainability
```

**Rule:** Products never call actuarial models directly.

## Packages

| Path | Role |
|------|------|
| `aic/contracts/` | Shared objects (FeatureVector, RiskResult, …) |
| `aic/features/` | Actuarial Knowledge Layer |
| `aic/products/` | CT Flex / future motor adapters & product rules |
| `aic/core/credibility/` | Credibility Framework |
| `aic/core/risk_engine/` | Expected loss |
| `aic/core/pricing/` | Pure → loads → technical → indicated commercial |
| `aic/core/reserving/` | Chain-Ladder / BF / … |
| `aic/decision/` | Product decisions (PAYG, bind/refer) |
| `aic/orchestrator.py` | End-to-end quote for CT Flex |

## CT Flex Phase 1

- Product: **Income** PAYG (`premium_rate` on earnings / fare)
- Credibility: Bühlmann–Straub strategy
- Risk: class-rate engine (Gamma GLM available as another `RiskEngine`)
- Pricing: `StandardPricingEngine` from CT Flex expense/profit assumptions
- Decision: PAYG packaging, benefit cap, Z refer threshold

## Docs

- [`feature_dictionary.md`](feature_dictionary.md)
- [`credibility_framework.md`](credibility_framework.md)
- [`pricing_engine.md`](pricing_engine.md)
- [`migration_plan.md`](migration_plan.md)

## Next

1. ~~Core + validation + benchmark~~ **done**
2. ~~Research paper draft~~ **done** — [`docs/research/paper.md`](research/paper.md) (**v1.0 freeze**)
3. Typeset / submit manuscript; then motor adapter as extensibility proof
