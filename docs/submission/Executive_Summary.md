# AIC Platform v1.0 — Executive Summary

**Release:** AIC Platform v1.0 · Release Candidate 1 (RC1)  
**Audience:** Actuarial judges, InsurTech reviewers, technical examiners  
**Reading time:** ~5 minutes

## Problem

Digital insurance products that serve informal and platform-mediated workers often embed credibility, pricing, and product rules in a single calculator. That pattern can demonstrate feasibility, but it limits reuse, governance, and actuarial review.

## Solution

**AIC** (Actuarial Interactive Calculator / actuarial intelligence platform) organizes classical actuarial methods behind a modular architecture:

**Adapter → Actuarial Knowledge Layer → Credibility → Risk → Pricing → Decision → Explainability**

In this work, *actuarial intelligence* means structured integration of classical methods, standardized features, governance, and explainable decision support—not autonomous machine-learning discovery beyond the methods implemented.

## Contributions (v1.0)

1. Modular platform architecture separating product logic from actuarial reasoning  
2. Actuarial Knowledge Layer for standardized actuarial features  
3. Credibility framework designed for multiple strategies (Bühlmann–Straub production-wired)  
4. Reusable pricing pipeline (expected loss → technical → indicated commercial)  
5. Governance and validation framework for explainable decisions  
6. System benchmark: CT Flex prototype → AIC architectural evolution  

## Evidence

| Evidence | What it shows |
|----------|----------------|
| Validation suite (`python -m aic.validation`) | Layer contracts, identities, and decision-rule behaviour |
| Prototype benchmark (`python -m aic.benchmark`) | Capability growth; income *amount* vs *reliability* |
| Unit/integration tests | Engineering quality under the freeze |

## Non-claims

AIC v1.0 does **not** claim improved empirical loss prediction, reduced claims cost, or regulatory model validation. Parameters are illustrative. Product expansion beyond CT Flex Income is intentionally deferred.

## Case study

**CT Flex Income** (PAYG microinsurance for informal earnings) is the first product adapter. The original prototype proved PAYG feasibility with tightly coupled logic; AIC preserves the methodology while separating concerns into reusable, governed layers.

## Roadmap (high level)

| Version | Focus |
|---------|--------|
| **v1.0** | Platform freeze — this submission |
| **v1.1** | Further adapters, credibility strategies, empirical calibration |
| **v2.0** | Deployment hardening and production monitoring |

## Recommended next document

Read the full research paper, then the architecture diagram and benchmark report.
