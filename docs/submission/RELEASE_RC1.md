# AIC Platform v1.0 — Release Candidate 1 (RC1)

**Status:** Submission mode · repository freeze  
**Package version:** `aic.__version__ = 1.0.0`  
**Platform model:** `aic-platform-1.0.0`  
**Effective:** 2026-07-25

## Freeze policy

From RC1 forward, every change on the submission branch must fall into **exactly one** of:

1. **Bug fixes** — correctness defects that break documented behaviour  
2. **Presentation improvements** — figures, PDFs, typography, packaging  
3. **Reviewer-requested wording changes** — paper, governance, or summary text  

**Out of scope for v1.0 / RC1**

- New actuarial layers  
- New insurance products or adapters  
- Architectural redesign  
- New credibility strategies beyond Bühlmann–Straub production wiring  
- Empirical calibration campaigns  

Ideas that arise during review belong on the **v1.1 / v2.0 roadmap** (`docs/ROADMAP.md`), not in this freeze.

## Source of truth

| Artifact | Role |
|----------|------|
| [`docs/research/paper.md`](../research/paper.md) | Research claims and architecture narrative |
| [`docs/governance/`](../governance/) | Assumptions, limitations, versioning, validation policy |
| [`docs/ROADMAP.md`](../ROADMAP.md) | v1.0 vs future work |
| [`docs/submission/`](./) | Judge-facing package layout |

## Reproduce (engineering evidence)

```bash
python -m aic.validation
python -m aic.benchmark --write-report
python -m pytest tests -q
```

## Protect the submitted freeze

Once RC1 is submitted, **do not keep tinkering on the freeze tag**.

| Action | Where |
|--------|--------|
| Exact submitted snapshot | Tag / archive `v1.0.0-RC1` (immutable reference) |
| Reviewer-requested edits | Branch `rc2` or release `v1.0.1` |
| New features / adapters | `v1.1` per [`docs/ROADMAP.md`](../ROADMAP.md) |

Release history: [`CHANGELOG.md`](../../CHANGELOG.md) · Lineage: [`docs/EVOLUTION.md`](../EVOLUTION.md)

## Next presentation steps (allowed on the working tree before final zip)

- Export / polish SVG → PDF figures  
- Typeset paper and executive summary to PDF  
- Assemble `AIC_v1.0_Submission/` zip (see [`PACKAGE.md`](PACKAGE.md))  
- Citation / grammar consistency pass  
- Demo rehearsal using the paper narrative  
- Create git tag `v1.0.0-RC1` when the submission zip is finalized
