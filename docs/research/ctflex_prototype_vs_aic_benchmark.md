# CT Flex Prototype vs AIC Actuarial Platform

_Generated: 2026-07-24T22:20:18.599672+00:00_

## Narrative

The CT Flex prototype demonstrated the **feasibility** of PAYG microinsurance pricing using classical actuarial concepts (class rates and a simple Bühlmann Z). However, actuarial logic, pricing adjustments, and product rules were tightly coupled inside one calculator.

AIC separates those concerns into reusable layers—adapter, Actuarial Knowledge Layer, credibility, risk, pricing, decision, and explainability—enabling governance and extensibility while preserving the underlying actuarial methodology. This report therefore compares **actuarial systems**, not programming languages, and evaluates **architectural capability**, not predictive superiority.

## Claim (defensible)

The CT Flex prototype proved PAYG pricing feasibility with classical methods tightly coupled in one calculator. AIC preserves that methodology while separating concerns into reusable, governed layers, yielding greater architectural capability and explainability. This benchmark does not claim superior empirical loss prediction without portfolio outcome data.

## Capability matrix

| Dimension | CT Flex Prototype | AIC Platform |
|-----------|-------------------|--------------|
| Data Inputs | Fixed product inputs (transaction count) | Standardized product adapter + observation series |
| Feature Engineering | Manual / fixed bps factors | Actuarial Knowledge Layer (grouped features + indices) |
| Credibility | Simple Bühlmann Z = n/(n+k) | Credibility Framework (context, class, drivers, metadata) |
| Risk Estimation | Embedded calculator (no E[loss] object) | Modular RiskEngine → RiskResult (expected loss) |
| Pricing | Direct product premium rate logic | Dedicated Pricing Engine (pure → technical → commercial) |
| Decision Logic | Product-specific always-approved UW | Decision Engine (bind/refer, PAYG packaging, benefits) |
| Explainability | Basic factor list (static text + bps) | Structured explanation + credibility drivers + pricing components |

## Architecture scorecard

| Capability | Prototype | AIC |
|------------|-----------|-----|
| Layered architecture | ❌ | ✅ |
| Product independence | ❌ | ✅ |
| Actuarial Knowledge Layer | ❌ | ✅ |
| Pluggable credibility | ❌ | ✅ |
| Pricing engine | ❌ | ✅ |
| Governance metadata | ❌ | ✅ |
| Validation framework | ❌ | ✅ |

## Persona results

### New Worker (`new_worker`)

~2 weeks history, sparse jobs, low exposure.

**Expected behaviour:** Low credibility; lean on collective; conservative / Refer.

| Metric | Prototype | AIC |
|--------|-----------|-----|
| Transaction count | 2 | 2 |
| Credibility Z | 0.04 | 0.0385 |
| Credibility class | — | Initial |
| Decision | Approved | Refer |
| Premium rate | 0.03 | 0.033 |
| Expected loss | — | 4.9818 |
| Technical premium | — | 6.22725 |
| Income stability | — | 0.8947 |
| Explainability coverage | 0.0 | 1.0 |
| Explanation factors | 6 | 35 |

### Established Driver (`established_driver`)

~18 months proxy via dense stable earnings, high exposure.

**Expected behaviour:** High credibility; pricing reflects individual experience.

| Metric | Prototype | AIC |
|--------|-----------|-----|
| Transaction count | 80 | 80 |
| Credibility Z | 0.62 | 0.6154 |
| Credibility class | — | Established |
| Decision | Approved | Approved |
| Premium rate | 0.0303 | 0.0309 |
| Expected loss | — | 7.1084 |
| Technical premium | — | 8.8855 |
| Income stability | — | 0.987 |
| Explainability coverage | 0.0 | 1.0 |
| Explanation factors | 6 | 34 |

### Volatile Income (`volatile_income`)

Same volume as high-income-stable, but large gaps and variance.

**Expected behaviour:** Lower income stability; AKL should flag volatility.

| Metric | Prototype | AIC |
|--------|-----------|-----|
| Transaction count | 20 | 20 |
| Credibility Z | 0.29 | 0.2857 |
| Credibility class | — | Emerging |
| Decision | Approved | Approved |
| Premium rate | 0.0301 | 0.0348 |
| Expected loss | — | 10.4419 |
| Technical premium | — | 13.052375 |
| Income stability | — | 0.1845 |
| Explainability coverage | 0.0 | 1.0 |
| Explanation factors | 6 | 34 |

### High Income Stable (`high_income_stable`)

Same transaction count as volatile persona; high, steady fares.

**Expected behaviour:** Higher stability than volatile; prototype (count-only) identical.

| Metric | Prototype | AIC |
|--------|-----------|-----|
| Transaction count | 20 | 20 |
| Credibility Z | 0.29 | 0.2857 |
| Credibility class | — | Emerging |
| Decision | Approved | Approved |
| Premium rate | 0.0301 | 0.0322 |
| Expected loss | — | 14.3074 |
| Technical premium | — | 17.88425 |
| Income stability | — | 1.0 |
| Explainability coverage | 0.0 | 1.0 |
| Explanation factors | 6 | 34 |

## Conceptual contribution — income amount vs reliability

Higher income ≠ automatically higher risk; AKL separates amount from reliability.

- Same transaction count for volatile vs high-stable: **True**
- Prototype premium rates identical: **True** (count-only calculator)
- AKL income_stability (volatile → high-stable): **0.1845 → 1.0**
- AKL distinguishes reliability: **True**

## Pipeline metrics (capability growth)

| Metric | Prototype | AIC |
|--------|-----------|-----|
| Engineered features | fixed bps factors (6) | AKL feature groups + indices |
| Credibility output | True | True |
| Risk estimate E[loss] | False | True |
| Technical premium | False | True |
| Decision confidence object | False | True |
| Explainability | basic | structured |
| Governance metadata | False | True |

## Conclusion

The prototype remains a coherent product demo. AIC is the platform evolution of that methodology: the same classical building blocks, reorganized so that income **amount** and income **reliability** can differ when transaction counts do not; so that expected loss and technical premium are first-class objects; and so that thin history can trigger Refer rather than unconditional Approve. We do **not** claim better empirical loss prediction, improved loss ratios, or outperformance of production insurer systems without portfolio outcome data.

See also: `docs/research/paper.md` §8.3 · `figures/fig06_benchmark.md`.
