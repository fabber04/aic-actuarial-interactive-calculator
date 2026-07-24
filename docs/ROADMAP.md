# AIC Roadmap

**Current release:** Platform v1.0 · RC1 (frozen for submission)  
**Policy:** New ideas after RC1 go to v1.1+; they do not reopen the v1.0 architecture.

| Version | Focus | Status |
|---------|--------|--------|
| **v1.0** | Modular actuarial platform; CT Flex Income adapter; AKL; Credibility Framework (Bühlmann–Straub); Risk; Pricing; Decision; Explainability; research validation suite; prototype benchmark; governance docs; research manuscript | **Frozen (RC1)** |
| **v1.1** | Motor adapter; Health adapter; additional credibility strategies (e.g. Bayesian / Jewell); empirical calibration on real alternative-data portfolios | Planned |
| **v2.0** | Real-world deployment hardening; additional pricing models; expanded governance; production monitoring | Planned |

## v1.0 in scope (delivered)

- Product-independent layer contracts and orchestrator  
- Actuarial Knowledge Layer (financial, behavioural, occupational, environmental scaffolds)  
- Pluggable credibility *framework* with Bühlmann–Straub production strategy  
- Class-rate risk path + loading-based pricing pipeline  
- Decision Engine (PAYG packaging, bind/refer) and structured explanations  
- Executable validation suite and CT Flex prototype vs AIC benchmark  
- Governance pack (assumptions, limitations, versioning, validation policy)  
- Research paper pack (`docs/research/`)

## Explicitly deferred (not incomplete v1.0)

| Item | Target |
|------|--------|
| New product adapters beyond CT Flex Income | v1.1 |
| Bayesian / Jewell credibility production wiring | v1.1 |
| Portfolio outcome / loss-ratio studies | v1.1+ |
| Stochastic reserving on the quote path | v2.0 research track |
| Production monitoring / model registry at scale | v2.0 |

## Change control after RC1

Only bug fixes, presentation improvements, and reviewer-requested wording changes may land on the submission branch. See [`docs/submission/RELEASE_RC1.md`](submission/RELEASE_RC1.md).
