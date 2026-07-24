# Changelog

All notable changes to the AIC Platform are documented in this file.

The format follows a lightweight Keep a Changelog style. Versions after RC1 should use dedicated release trains (`v1.0.0-RC2`, `v1.0.1`, `v1.1.0`, …). **Do not rewrite history on a submitted freeze tag.**

---

## [1.0.0-RC1] — 2026-07-25

**AIC Platform v1.0 · Release Candidate 1 — submission freeze**

### Added

- Modular platform pipeline: Adapter → Actuarial Knowledge Layer → Credibility → Risk → Pricing → Decision → Explainability
- Actuarial Knowledge Layer (`aic.features`) with financial, behavioural, occupational, and environmental feature groups
- Credibility Framework (`aic.core.credibility`) with Bühlmann–Straub as the first production strategy
- Pricing Engine (`aic.core.pricing`) separating pure / technical / indicated commercial premium from product payment mechanics
- Decision Engine and structured explainability with governance metadata on quote responses
- Research validation suite (`python -m aic.validation`)
- CT Flex prototype vs AIC system benchmark (`python -m aic.benchmark`)
- Governance pack (`docs/governance/`: assumptions, limitations, versioning, validation policy, model governance)
- Research manuscript pack (`docs/research/paper.md`, figures, tables, bibliography)
- Submission pack (`docs/submission/`: how-to-read, executive summary, validation/user/API docs, packaging)
- Roadmap distinguishing v1.0 from v1.1 / v2.0 (`docs/ROADMAP.md`)
- Submission assembler (`scripts/build_submission_package.py` → `dist/AIC_v1.0_Submission/`)

### Changed

- CT Flex Income quotes migrated to Product Adapter + orchestrator architecture (`AICPlatform`)
- Platform package version frozen at `1.0.0`; API model version `aic-platform-1.0.0`
- Repository policy set to **submission mode**: bug fixes, presentation, and reviewer wording only

### Deprecated

- Monolithic / tightly coupled CT Flex local calculator path as the *primary* actuarial implementation (prototype retained for benchmark comparison only)
- Treating the legacy dual-run slice (`/ct-flex/underwrite/v1`) as the long-term Income path (kept for migration checks)

### Known limitations

- Bühlmann–Straub is the only production-wired credibility strategy; other strategies are extension points
- Validation verifies architectural integrity, contracts, and decision-rule behaviour—not empirical loss prediction or regulatory model validation
- Product expansion beyond CT Flex Income is intentionally deferred to v1.1+
- Parameters and occupation tables are illustrative, not filed tariffs
- Optional Gamma GLM motor path is toolkit support; not required for the CT Flex Income research case

### Evidence commands

```bash
python -m aic.validation
python -m aic.benchmark --write-report
python -m pytest tests -q
```

---

## Pre-release lineage (summary)

Work before RC1 progressed from the CT Flex prototype calculator through layered architecture, AKL, credibility, risk/pricing separation, validation/governance, and the research manuscript. See `docs/EVOLUTION.md` and the evolution note in the README / paper.
