# Submission package layout

Assemble a judge-facing folder (do **not** hand judges the raw git tree as the primary artifact).

```text
AIC_v1.0_Submission/
├── 00_How_to_Read_This_Submission.pdf    ← from HOW_TO_READ_THIS_SUBMISSION.md
├── 01_Executive_Summary.pdf              ← from Executive_Summary.md
├── 02_Paper.pdf                          ← typeset from docs/research/paper.md
├── 03_Architecture_Diagram.pdf           ← from figures/export/fig01_architecture.svg
├── 04_Benchmark_Report.pdf               ← from docs/research/ctflex_prototype_vs_aic_benchmark.md
├── 05_Validation_Report.pdf              ← from Validation_Report.md (+ suite output)
├── 06_User_Guide.pdf                     ← from User_Guide.md
├── 07_Roadmap.pdf                        ← from docs/ROADMAP.md
├── Governance/                           ← copy of docs/governance/
├── API_Documentation/                    ← from API_Documentation.md (+ OpenAPI if exported)
├── Figures/                              ← SVG/PDF exports from docs/research/figures/export/
├── LICENSE                               ← choose and include before final zip
└── Source_Code.zip                       ← clean source snapshot (no .venv, no secrets)
```

## Assemble checklist

- [ ] Freeze confirmed: [`RELEASE_RC1.md`](RELEASE_RC1.md)  
- [ ] `python -m aic.validation` → OVERALL PASS  
- [ ] `python -m aic.benchmark --write-report` refreshed  
- [ ] `python -m pytest tests -q` green  
- [ ] Paper wording freeze (only reviewer edits thereafter)  
- [ ] Figures exported SVG (done under `docs/research/figures/export/`); PDF polish optional  
- [ ] Typeset markdown → PDF (Pandoc, Word, or LaTeX—venue dependent)  
- [ ] LICENSE selected and added  
- [ ] `CHANGELOG.md` and `docs/EVOLUTION.md` included (via source zip / package copy)  
- [ ] Source zip excludes `.venv/`, `__pycache__/`, `.env`, large raw CSVs if not required  
- [ ] Place `00_How_to_Read_This_Submission.pdf` at the package root  
- [ ] After final zip: tag immutable `v1.0.0-RC1`; further edits → RC2 / v1.0.1

## Source paths (in this repository)

| Package file | Repository source |
|--------------|-------------------|
| How to Read | `docs/submission/HOW_TO_READ_THIS_SUBMISSION.md` |
| Executive Summary | `docs/submission/Executive_Summary.md` |
| Paper | `docs/research/paper.md` |
| Architecture diagram | `docs/research/figures/export/fig01_architecture.svg` |
| Benchmark | `docs/research/ctflex_prototype_vs_aic_benchmark.md` |
| Validation | `docs/submission/Validation_Report.md` |
| User guide | `docs/submission/User_Guide.md` |
| API docs | `docs/submission/API_Documentation.md` |
| Roadmap | `docs/ROADMAP.md` |
| Governance | `docs/governance/` |

## Helper script

```bash
python scripts/build_submission_package.py
```

Creates `dist/AIC_v1.0_Submission/` with markdown/SVG copies and a packaging README. PDF conversion remains a manual/typesetting step.
