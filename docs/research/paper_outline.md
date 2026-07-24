# AIC Research Paper — Outline

**Status:** AIC Core **v1.0 Freeze** — architecture locked for the research write-up.  
**Title:** AIC: A Modular Actuarial Intelligence Platform for Explainable Insurance Decision Support Using Classical Actuarial Methods and Alternative Data

## Deliverables

| Path | Role |
|------|------|
| `paper_outline.md` | This outline |
| `paper.md` | Full manuscript draft |
| `figures/` | Architecture / pipeline figure captions (Mermaid sources) |
| `tables/` | Standalone tables for submission |
| `references.bib` | BibTeX bibliography |
| `ctflex_prototype_vs_aic_benchmark.md` | Empirical/architectural benchmark appendix |

## Section map

1. Abstract  
2. Introduction  
3. Problem Statement  
4. Related Work  
5. AIC Architecture  
6. Actuarial Knowledge Layer  
7. Credibility Framework  
8. Risk and Pricing Framework  
9. Validation  
10. Discussion  
11. Future Work  
12. Conclusion  

## Claims allowed / forbidden

**Allowed:** modularity, product–actuarial separation, AKL standardization, governed explainable decisions, extensibility by design, prototype-vs-platform benchmark evidence.

**Forbidden without outcome data:** improved prediction accuracy, reduced losses, outperformance of industry systems.

## Freeze rule

Do not add new platform layers before the paper draft is stable. Product adapters (motor, health) are **future work**, not v1.0 scope.
