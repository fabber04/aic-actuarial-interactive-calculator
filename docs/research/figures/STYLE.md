# Figure style guide (publication)

Use a single visual language across all AIC figures:

| Token | Meaning | Suggested colour (print-safe) |
|-------|---------|-------------------------------|
| Input / data | Observations, raw product | `#E8EEF4` fill, `#334155` stroke |
| Actuarial core | AKL, credibility, risk, pricing | `#DCEAF7` fill, `#1E3A5F` stroke |
| Product / decision | Decision, PAYG, UX | `#E7F0E7` fill, `#2F5D3A` stroke |
| Evidence | Validation, benchmark | `#F4EDE0` fill, `#6B4F2A` stroke |

**Typography:** Prefer a single sans family in exported SVG/PDF (e.g. Source Sans / IBM Plex Sans). Avoid decorative gradients and glow.

**Export path for judges:** Render Mermaid → SVG (sources in this folder; rendered files in `export/`) → lightly edit in a vector tool → PDF. Keep node labels short; put detail in captions.

Rendered submission assets (v1.0 freeze):

| Figure | SVG |
|--------|-----|
| Fig 1 | `export/fig01_architecture.svg` |
| Fig 2 | `export/fig02_akl.svg` |
| Fig 3 | `export/fig03_credibility.svg` |
| Fig 4 | `export/fig04_pricing_pipeline.svg` |
| Fig 5 | `export/fig05_validation.svg` |
| Fig 6 | `export/fig06_benchmark.svg` |
| Fig 7 | `export/fig07_modules.svg` |

Regenerate with Mermaid CLI, e.g. `npx @mermaid-js/mermaid-cli -i export/fig01_architecture.mmd -o export/fig01_architecture.svg -b transparent`.

**Do not** use dark-mode neon or purple-gradient “AI” aesthetics in submission figures.
