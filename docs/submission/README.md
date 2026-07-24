# Submission pack (v1.0 RC1)

Judge-facing materials for **AIC Platform v1.0 · Release Candidate 1**.

| Document | Purpose |
|----------|---------|
| [`HOW_TO_READ_THIS_SUBMISSION.md`](HOW_TO_READ_THIS_SUBMISSION.md) | Recommended reading order |
| [`Executive_Summary.md`](Executive_Summary.md) | Five-minute overview |
| [`Validation_Report.md`](Validation_Report.md) | What validation claims—and does not |
| [`User_Guide.md`](User_Guide.md) | How to run quotes and evidence |
| [`API_Documentation.md`](API_Documentation.md) | HTTP contracts |
| [`PACKAGE.md`](PACKAGE.md) | Folder layout + PDF checklist |
| [`RELEASE_RC1.md`](RELEASE_RC1.md) | Freeze policy |

Research manuscript: [`../research/paper.md`](../research/paper.md)  
Roadmap: [`../ROADMAP.md`](../ROADMAP.md) · Evolution: [`../EVOLUTION.md`](../EVOLUTION.md) · Changelog: [`../../CHANGELOG.md`](../../CHANGELOG.md)

```bash
python scripts/build_submission_package.py
```

Assembles `dist/AIC_v1.0_Submission/` (markdown/SVG + source zip). Convert key files to PDF before final delivery.
