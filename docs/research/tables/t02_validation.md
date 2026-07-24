# Table T2 — Validation Suite (layer checks)

Run: `python -m aic.validation`

| Layer | Checks (examples) | Pass criterion |
|-------|-------------------|----------------|
| AKL | Feature ranges; stability orders volatile vs stable; metadata present | All checks pass |
| Credibility | \(Z=n/(n+k)\); monotone in exposure; class bands; blend identity | All checks pass |
| Risk | Class-rate E[loss] identity; positivity; Z propagation | All checks pass |
| Pricing | Technical ≥ pure; loading identity; commercial floor | All checks pass |
| Decision / Explain | Thin → Refer; rich → Approved; explanations cite credibility & pricing | All checks pass |

**Overall:** suite reports `OVERALL: PASS` under AIC v1.0 freeze.
