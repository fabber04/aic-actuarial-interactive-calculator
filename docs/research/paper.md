# AIC: A Modular Actuarial Intelligence Platform for Explainable Insurance Decision Support Using Classical Actuarial Methods and Alternative Data

**AIC Platform v1.0 · Release Candidate 1 — Research Manuscript**  
**Status:** Submission mode · paper is the source of truth for architecture and claims  
**Reproduce:** `python -m aic.validation` · `python -m aic.benchmark --write-report` · `python -m pytest tests -q`  
**Companions:** `docs/governance/` · `docs/ROADMAP.md` · `docs/submission/` · `figures/` · `tables/`

---

## Abstract

Insurance products that serve informal and platform-mediated workers must price thin, alternative-data experience without abandoning classical actuarial discipline or explainability. Many digital insurance prototypes embed credibility, pricing, and product rules in a single calculator, which limits reuse, governance, and transparent review. This paper introduces **AIC**—a modular actuarial intelligence platform that organizes classical methods (credibility, expected-loss estimation, loading-based technical premium, and reserving) behind product-independent contracts.

AIC separates product adapters; an **Actuarial Knowledge Layer (AKL)** that maps standardized observations to actuarial feature groups; a **Credibility Framework** designed for multiple strategies (Bühlmann–Straub production-wired in v1.0); modular **Risk** and **Pricing** engines; a product **Decision Engine**; and structured **explainability** with governance metadata. On a CT Flex informal-income case study, a research validation suite verifies architectural integrity and decision-rule behaviour—not predictive holdout or regulatory model validation. A system benchmark against the original CT Flex prototype shows architectural capability growth and a conceptual result: for equal transaction counts, the prototype yields identical rates, while the AKL distinguishes **income reliability** from **income amount**.

We do **not** claim improved empirical loss prediction or reduced claims cost. The contribution is a governed, explainable actuarial *platform architecture* for alternative-data insurance decision support.

---

## 1. Introduction

Digital distribution and mobile money create opportunities to insure workers who lack payslips and long policy histories. Actuarial practice, however, continues to rely on established tools: credibility theory [@buhlmann1967; @buhlmannStraub1970], generalized linear models for pricing [@nelderWedderburn1972; @casMonographGLM], and triangular reserving [@mack1993; @brownGottlieb]. The central difficulty for digital products is often organizational rather than mathematical: how should classical methods be *structured in software* so that product teams can iterate on user experience without rewriting actuarial logic—and so that actuaries can audit assumptions, versions, and explanations?

AIC addresses that difficulty. Alternative data (for example, platform transaction streams) enter through a product adapter, become actuarial features in the AKL, receive credibility weight, convert to expected loss, load into technical and indicated commercial premium, and only then receive product packaging such as pay-as-you-earn (PAYG) collection.

In this work, **actuarial intelligence** refers to the structured integration of classical actuarial methods, standardized feature engineering, governance, and explainable decision support within a modular platform architecture. It does not imply autonomous discovery or machine-learning-based reasoning beyond the methods explicitly implemented.

**This paper introduces AIC**, states its contributions explicitly, documents architecture and actuarial interfaces, reports validation and prototype-benchmark evidence at the v1.0 freeze, and delimits claims that the evidence does not support.

### 1.0 Evolution lineage

AIC evolved from a product calculator into a platform through staged decisions (full note: `docs/EVOLUTION.md`):

```text
CT Flex Prototype → AIC Concept → Layered Architecture → AKL
  → Credibility Framework → Risk + Pricing → Validation & Governance
  → AIC Platform v1.0 RC1
```

The actuarial methodology is continuous with the CT Flex prototype; the contribution of this release is the governed, layered organization of that methodology.

### 1.1 Contributions

**The primary contributions of this work are:**

1. **A modular actuarial platform architecture** that separates product logic from actuarial reasoning through typed layer contracts.
2. **An Actuarial Knowledge Layer (AKL)** that transforms heterogeneous insurance observations into standardized actuarial feature groups and composite indices.
3. **A credibility framework designed to support multiple credibility strategies**, with Bühlmann–Straub implemented as the first production strategy and additional methods defined as extension points.
4. **A reusable pricing pipeline** that separates expected-loss estimation from technical and indicated commercial premium, leaving product payment mechanics to a Decision Engine.
5. **A governance and validation framework** supporting explainable actuarial decision-making (assumptions register, limitations, versioning, and an executable validation suite).
6. **A system benchmark** demonstrating the architectural evolution from the CT Flex prototype calculator to AIC, including evidence that income *amount* and income *reliability* are distinct actuarial concepts.

---

## 2. Problem Statement

We distinguish software-systems problems from market-actuarial motivation.

### 2.1 Software / systems problems

- **Product-specific implementations.** Pricing and credibility are often hard-wired inside a single product calculator (as in early CT Flex prototypes), blocking reuse across motor, health, or agriculture lines.
- **Duplicated pricing logic.** Expense and profit loads appear in multiple places, inviting inconsistency between “technical” and “product” premiums.
- **Weak explainability for review.** A premium rate may be returned without a traceable path through expected loss and loadings.
- **Limited governance.** Assumptions and model versions are not first-class objects on the decision response.
- **Limited validation culture.** Helper unit tests are not a substitute for layer-wise actuarial validation.

### 2.2 Actuarial / market motivation

- Thin individual experience in informal markets requires credibility blending with collective class rates.
- Alternative data are noisy; **amount** of earnings must not be conflated with **reliability** of earnings.
- Actuarial judges and supervisors typically ask whether methods are classical, documented, and limited appropriately—not whether a demonstration “uses AI.”

These problems motivate modular architecture with explicit assumptions and validation—not a claim of new credibility mathematics.

---

## 3. Related Work

**GLMs in insurance pricing.** Generalized linear models are standard for frequency, severity, and premium modelling [@nelderWedderburn1972; @casMonographGLM; @oakes2004]. AIC’s class-rate risk path and optional Gamma GLM adapter sit in this tradition; the contribution is packaging them behind a `RiskEngine` interface, not inventing a new link function.

**Credibility.** Bühlmann and Bühlmann–Straub credibility remain foundational for experience rating [@buhlmann1967; @buhlmannStraub1970]. AIC implements Bühlmann–Straub as the first strategy of a *framework* that can later host Jewell or Bayesian variants without rewriting product code.

**Reserving.** Chain-Ladder and related methods [@mack1993; @brownGottlieb] are implemented in `aic.core.reserving` as part of the classical toolkit. They are not on the CT Flex quote path in v1.0.

**Explainability in insurance.** Much XAI work emphasizes post-hoc interpretation of black-box models. AIC prioritizes *structural* explainability: each layer emits objects (features, credibility drivers, pricing components) that explanations can cite.

**Modular actuarial systems.** Production pricing systems are modular; many prototypes are not. AIC’s contribution is an open, research-oriented modularization with published contracts, validation, and a benchmark against a product prototype.

**Distinction.** The actuarial *methods* are classical. The *platform architecture* that organizes them for alternative-data products is the contribution of this work.

---

## 4. AIC Architecture

AIC Core v1.0 implements the pipeline in Figure 1:

```text
Client
  → Product Adapter
  → Actuarial Knowledge Layer
  → FeatureVector (+ metadata / groups)
  → Credibility Framework → CredibilityResult
  → Risk Engine → RiskResult (expected loss)
  → Pricing Engine → technical / indicated commercial premium
  → Decision Engine → product outcome (e.g. PAYG)
  → Explainability
```

**Design rule:** products never call actuarial engines directly. The orchestrator (`AICPlatform`) composes layers for CT Flex Income in v1.0.

See Figure 1 (`figures/fig01_architecture.md`) and Table T6 (`tables/t06_modules.md`).

### 4.1 Contracts

Primary objects include `StandardizedData`, `FeatureVector`, `CredibilityContext` / `CredibilityResult`, `RiskResult`, `PricingResult`, `DecisionResult`, and `Explanation`. Metadata fields record method names, versions, timestamps, and inputs used—supporting audit and reproducibility.

### 4.2 Layer consistency audit

Every v1.0 layer is required to answer the following (Table below). This audit is the paper’s check that architecture, code, and validation tell one story.

| Layer | Why it exists | Inputs | Outputs | Validated by | Governed by | Extensible? |
|-------|---------------|--------|---------|--------------|-------------|-------------|
| Product adapter | Hide product schemas from core | Raw product JSON | `StandardizedData` | Adapter/unit tests; quote smoke | Product rules docs | New adapters |
| AKL | Actuarial language from observations | `StandardizedData` | `FeatureVector` + groups | Validation suite (AKL) | Feature version metadata | New feature modules |
| Credibility | Weight individual vs collective | `CredibilityContext` | `CredibilityResult` | Validation suite (Z identities) | Method metadata; assumptions | New strategies |
| Risk | Estimate E[loss] | Features + credibility | `RiskResult` | Validation suite (class-rate identity) | Model name/version | New `RiskEngine`s |
| Pricing | Load E[loss] to premium | `RiskResult` + assumptions | `PricingResult` | Validation suite (loading identity) | Assumptions register | New loading policies |
| Decision | Product packaging | Features, risk, pricing | `DecisionResult` | Thin→Refer / rich→Approved checks | Product rules | New product rules |
| Explainability | Communicate “why” | Upstream objects | `Explanation` | Factor presence checks | — | Richer narratives |

### 4.3 Example quote walkthrough

The following New Worker persona (Table T5; Section 8.3) shows how an actuary would read a single quote through the layer contracts. Values are from the v1.0 benchmark freeze.

```text
Applicant (New Worker — ~2 weeks sparse history)
  ↓
CT Flex Adapter → StandardizedData
  ↓
AKL
  Income stability ≈ 0.89   (variation within the short series)
  Transaction volume n = 2
  ↓
Credibility
  Z ≈ 0.04
  Class = Initial
  ↓
Risk Engine
  Expected loss ≈ 4.98
  ↓
Pricing Engine
  Technical premium ≈ 6.23
  ↓
Decision Engine
  Refer
  ↓
Explanation
  Limited individual experience; greater reliance on collective estimates.
```

**Actuarial reading.** Income stability reflects observed variation *within the available series*, whereas credibility reflects the *sufficiency* of that experience. A short but relatively even income history may therefore produce a high stability index while still receiving a low credibility weight and a conservative underwriting decision (Refer). That separation is intentional: the AKL and the Credibility Framework answer different questions.

---

## 5. Actuarial Knowledge Layer

The AKL converts `StandardizedData` into a `FeatureVector` **without** computing premiums, GLM predictions, reserves, or underwriting decisions (Figure 2).

### 5.1 Feature groups

Financial, behavioural, occupational, and environmental groups are computed first, then flattened (Table T1). Composite indices on \([0,100]\) support dashboards and explanations.

### 5.2 Occupation as data, not code

Occupational hazard scores live in an `OccupationRiskTable`. Scores can be revised via table overrides without changing algorithms—separating assumptions from logic.

### 5.3 Income amount versus income reliability

For two workers with the **same transaction count** but different earnings paths (volatile with gaps versus high, stable fares), a count-only calculator produces identical credibility inputs, while the AKL yields materially different stability and financial indices. That distinction is central to alternative-data underwriting and is evidenced in Section 8.3 and Table T5.

Income stability must also be read together with credibility volume. Stability summarizes variation in the observed series; credibility \(Z\) summarizes whether that series is long enough to trust. Section 4.3 illustrates the New Worker case: high short-series stability with low \(Z\) and Refer.

---

## 6. Credibility Framework

AIC defines credibility as answering one question: *how much weight should be placed on this individual’s own experience versus the collective?* (Figure 3).

### 6.1 Interface and context

`CredibilityEngine.calculate(CredibilityContext) → CredibilityResult`. Context is derived from the FeatureVector but **omits** occupation risk, commercial premiums, and expected loss.

### 6.2 Bühlmann–Straub (v1.0)

With volume \(n\) and parameter \(k\),

\[
Z = \frac{n}{n+k}, \qquad
r_{\text{adj}} = Z\, r_{\text{ind}} + (1-Z)\, r_{\text{coll}}.
\]

Results include credibility **class** (Initial / Emerging / Established / Mature), **drivers**, confidence in \(Z\), and governance metadata.

### 6.3 Extensibility

Additional strategies (e.g. Bühlmann–Jewell, Bayesian) are architectural extension points. Only Bühlmann–Straub is production-wired in v1.0.

---

## 7. Risk and Pricing Framework

### 7.1 Risk

The `RiskEngine` estimates expected loss. CT Flex Income v1.0 uses a class-rate engine:

\[
\mathbb{E}[\text{Loss}] \approx r_{\text{adj}} \times \text{weekly income proxy} \times 4.
\]

A Gamma GLM adapter is available for motor-style schemas as a pluggable engine; it is not required for the CT Flex Income path.

### 7.2 Pricing

With pure premium \(P\), fixed expense \(F\), and ratios \(v,p,r,t\) (variable expense, profit, risk margin, tax):

\[
\text{Technical premium} = \frac{P + F}{1 - v - p - r - t}.
\]

Discounts and floors yield an **indicated commercial** premium. **PAYG rates and bind/refer rules remain in the Decision Engine** (Figure 4). The same technical premium can therefore feed annual motor billing or CT Flex earnings-share collection without rewriting actuarial loads.

---

## 8. Validation

### 8.1 Research validation suite

`python -m aic.validation` executes layer checks (Table T2; Figure 5): AKL ranges and ordering; credibility identities and monotonicity; risk identity; pricing identities; decision/explainability consistency (thin history → Refer; rich history → Approved). Under the v1.0 freeze the suite reports **OVERALL: PASS**.

The validation framework verifies **architectural integrity**, contract consistency, decision-rule behaviour, and layer interactions. It is **not** intended to replace actuarial experience studies, predictive holdout validation, or regulatory model validation.

### 8.2 Governance

Assumptions, limitations, versioning, and model governance are documented under `docs/governance/` (Table T3). Quote responses carry feature, credibility, and pricing metadata for audit trails.

### 8.3 Benchmark narrative: from prototype to platform

The CT Flex prototype demonstrated the **feasibility** of PAYG microinsurance pricing using classical actuarial concepts (class rates and a simple Bühlmann \(Z\)). However, actuarial logic, pricing adjustments, and product rules were tightly coupled inside one calculator. AIC separates those concerns into reusable layers, enabling explainability, governance, and extensibility while preserving the underlying actuarial methodology.

We therefore benchmark **actuarial systems**, not programming languages (Figure 6; Table T4; full appendix: `ctflex_prototype_vs_aic_benchmark.md`).

**Personas.** New Worker; Established Driver; Volatile Income; High Income Stable (Table T5).

**Supported findings.**

1. AIC exposes expected loss, technical premium, credibility class/drivers, and governance metadata; the prototype does not.
2. New Worker: AIC applies Refer on low \(Z\); the prototype always Approves.
3. Equal \(n\), different earnings paths: prototype rates are identical; AKL stability diverges (reliability versus amount).
4. Explainability coverage—defined as the share of expected pipeline layers represented in the explanation object—is higher for AIC.

**Explicit non-claims.** This benchmark evaluates architectural capability and methodological transparency. It does **not** demonstrate predictive superiority, loss-ratio improvement, or outperformance of production insurer systems.

### 8.4 Software tests

A passing unit/integration suite (including validation and benchmark tests) supports engineering quality. It does not replace empirical portfolio studies.

---

## 9. Discussion

### 9.1 Strengths

- Clear separation of product and actuarial concerns.
- Structural explainability tied to layer outputs.
- Governance hooks (metadata, assumptions, validation).
- Product independence by design (CT Flex is the first adapter, not the architecture).
- Claims aligned with available evidence.

### 9.2 Limitations (tightened)

The following delimit the scope of v1.0:

1. **The benchmark evaluates architectural capabilities rather than predictive superiority.** No claim is made that AIC reduces losses or improves loss ratios.
2. **Real-world outcome validation remains future work.** Personas and synthetic/alternative-data demos are not multi-year portfolio studies.
3. **Bühlmann–Straub is the first credibility strategy**; additional methods are planned but not production-wired.
4. **Product expansion beyond CT Flex was intentionally deferred** until after validation and this manuscript—motor/health adapters are applications of a frozen core, not part of v1.0 delivery.
5. **Parameters are illustrative** (class rates, occupation table, loadings), not filed tariffs.
6. **Optional Gamma GLM artifacts**, when trained, may reflect charged-premium proxies; full loss-cost indicated motor rates require further calibration.
7. **Environmental AKL features** are scaffolds for future products.

Open statement of these limits is intentional: reviewers should be able to trust what the paper *does* claim because it does not claim what the evidence cannot support.

---

## 10. Future Work

1. Empirical calibration on real alternative-data portfolios.  
2. Motor / health / agriculture / life adapters as applications of the frozen core.  
3. Additional credibility strategies (Jewell, Bayesian).  
4. Model registry and additional risk engines.  
5. Deeper reserving integration into portfolio monitoring.  
6. Regulatory-facing validation packs.  
7. Optional PDF polish of exported SVGs in `figures/export/`, then LaTeX typesetting for formal submission.

---

## 11. Conclusion

AIC demonstrates that classical actuarial methods can be organized into a modular, governed, explainable platform capable of supporting multiple insurance products while separating product logic from actuarial reasoning. Through an Actuarial Knowledge Layer, a pluggable credibility framework, modular risk and pricing engines, and structured explainability—backed by a validation suite and a prototype benchmark—AIC provides a research-grade software architecture for alternative-data insurance decision support. Predictive superiority is out of scope for v1.0; architectural completeness and methodological transparency are in scope and evidenced.

---

## Acknowledgements

This work builds on classical P&C pedagogy [@brownGottlieb] and on the CT Flex informal-sector product prototype used as the case study and benchmark baseline [@ctflexDemo2026].

---

## References

See `references.bib`.

---

## Appendix A — Reproduction

```bash
python -m aic.validation
python -m aic.benchmark --write-report
python -m pytest tests -q
```

## Appendix B — Figure and table index

| ID | File | Role |
|----|------|------|
| Fig 1 | `figures/fig01_architecture.md` · `figures/export/fig01_architecture.svg` | Overall architecture |
| Fig 2 | `figures/fig02_akl.md` · `figures/export/fig02_akl.svg` | Actuarial Knowledge Layer |
| Fig 3 | `figures/fig03_credibility.md` · `figures/export/fig03_credibility.svg` | Credibility Framework |
| Fig 4 | `figures/fig04_pricing_pipeline.md` · `figures/export/fig04_pricing_pipeline.svg` | Risk → Pricing → Decision |
| Fig 5 | `figures/fig05_validation.md` · `figures/export/fig05_validation.svg` | Validation workflow |
| Fig 6 | `figures/fig06_benchmark.md` · `figures/export/fig06_benchmark.svg` | Prototype vs AIC comparison |
| Fig 7 | `figures/fig07_modules.md` · `figures/export/fig07_modules.svg` | Package dependencies |
| Style | `figures/STYLE.md` | Print-safe colour tokens for export |
| T1–T6 | `tables/` | Feature groups, validation, governance, scorecard, personas, modules |
| Appendix | `ctflex_prototype_vs_aic_benchmark.md` | Full benchmark narrative + persona tables |
| Audit | Section 4.2 | Layer consistency questions |
| Walkthrough | Section 4.3 | New Worker quote through the pipeline |
