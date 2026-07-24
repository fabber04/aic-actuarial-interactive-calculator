# How to Read This Submission

**AIC Platform v1.0 · Release Candidate 1**

This package presents a modular actuarial platform for explainable insurance decision support. It is an **architecture and governance** contribution grounded in classical actuarial methods—not a claim of predictive superiority over production insurer systems.

## Recommended reading order

| Step | Document | Time | Why |
|------|----------|------|-----|
| 1 | **Executive Summary** | ~5 min | Scope, contributions, and non-claims |
| 2 | **Paper** | 20–30 min | Full technical and actuarial narrative |
| 3 | **Architecture Diagram** | ~5 min | End-to-end layer map (Figure 1) |
| 4 | **Benchmark Report** | ~10 min | CT Flex prototype → AIC capability story |
| 5 | **Validation Report** | ~5 min | What was verified—and what was not |
| 6 | **Governance/** | as needed | Assumptions, limitations, versioning |
| 7 | **Source Code** | optional | Reproduce validation and benchmark |

API documentation and the user guide support implementation review; they are secondary to the paper and evidence pack.

## What to look for

1. **Claim discipline** — Does every claim stay within validation and benchmark evidence?  
2. **Layer contracts** — Are product logic and actuarial reasoning separated?  
3. **Income reliability vs amount** — Does the AKL distinguish concepts that a count-only calculator conflates?  
4. **Governance** — Are assumptions, versions, and limitations first-class?

## What this submission does *not* claim

- Improved empirical loss prediction or reduced claims cost  
- Regulatory model validation or multi-year portfolio experience studies  
- Multiple production credibility strategies (only Bühlmann–Straub is wired in v1.0)  
- Product breadth beyond the CT Flex Income case study

Those items appear on the roadmap as **future work**, not unfinished v1.0 deliverables.

## Reproduce the evidence

```bash
python -m aic.validation
python -m aic.benchmark --write-report
python -m pytest tests -q
```

## Contact path for reviewers

Start with the Executive Summary and Paper. Use the Benchmark and Validation reports only if you need to verify the evidence behind §§8–9 of the paper.
