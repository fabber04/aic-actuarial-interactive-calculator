# Validation Report — AIC Platform v1.0 (RC1)

**Suite:** `python -m aic.validation`  
**Version:** `1.0.0`  
**Freeze status:** OVERALL PASS under v1.0 RC1

## Scope

The validation framework verifies:

- Architectural integrity of layer contracts  
- Identity relationships (credibility \(Z\), class-rate expected loss, loading formulae)  
- Decision-rule behaviour (e.g. thin history → Refer; rich history → Approved)  
- Layer interactions consumed by the orchestrator  

## Out of scope

This report is **not**:

- An actuarial experience study  
- Predictive holdout / out-of-sample loss validation  
- Regulatory model validation (e.g. Solvency / ORSA-style sign-off)  
- Evidence of improved loss ratios  

Those remain future work (see `docs/ROADMAP.md`).

## How to reproduce

```bash
python -m aic.validation
```

Optional: capture console output into this package as `Validation_Suite_Output.txt` before typesetting the PDF.

## Related evidence

| Artifact | Role |
|----------|------|
| `docs/governance/validation_framework.md` | Policy |
| `docs/research/tables/t02_validation.md` | Summary table for the paper |
| `docs/research/paper.md` §8.1 | Narrative in the manuscript |
| Unit/integration tests | `python -m pytest tests -q` |

## Interpretation for judges

A **PASS** means the platform behaves as specified under the frozen contracts. It does **not** mean the illustrative parameters are filed tariffs or that live portfolio outcomes have been proven.
