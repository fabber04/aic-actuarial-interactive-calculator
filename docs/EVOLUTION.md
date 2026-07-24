# Evolution of AIC

AIC was not designed as a green-field monolith. It evolved from a product calculator into a governed platform through deliberate architectural decisions.

```text
CT Flex Prototype
        │
        ▼
AIC Concept
        │
        ▼
Layered Architecture
        │
        ▼
Actuarial Knowledge Layer (AKL)
        │
        ▼
Credibility Framework
        │
        ▼
Risk + Pricing Engines
        │
        ▼
Validation & Governance
        │
        ▼
AIC Platform v1.0 RC1
```

## What each stage contributed

| Stage | Intent |
|-------|--------|
| **CT Flex Prototype** | Prove PAYG microinsurance feasibility with classical concepts (class rates, simple Bühlmann \(Z\)) in one calculator |
| **AIC Concept** | Treat actuarial logic as reusable platform services, not product-local code |
| **Layered Architecture** | Enforce Adapter → features → credibility → risk → pricing → decision → explain |
| **AKL** | Turn alternative-data observations into actuarial feature groups (amount vs reliability) |
| **Credibility Framework** | Answer individual vs collective weight behind a pluggable interface |
| **Risk + Pricing** | Separate E[loss] estimation from loadings and from product payment mechanics |
| **Validation & Governance** | Make assumptions, versions, limits, and checks first-class |
| **v1.0 RC1** | Freeze a coherent, evidenced release for submission |

## Continuity claim

The actuarial *methodology* is continuous with the prototype. The *organization* of that methodology—contracts, layers, governance, and evidence—is the platform contribution of AIC v1.0.

Future ideas (additional adapters, Bayesian credibility, empirical calibration) belong on the [roadmap](ROADMAP.md), not in a rewrite of RC1 history.
