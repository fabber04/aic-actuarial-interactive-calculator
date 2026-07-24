# AIC Migration Plan — Repository Audit

**Status date:** 2026-07-24  
**Goal:** Transform the working repository into AIC Platform v2 **incrementally** — keep the system green at every step. Broader than CT Flex alone.

This audit reflects the repo **after** skeleton, reorg, orchestrator wiring, reserving split, and GLM RiskEngine wrapper.

---

## Guiding principle

> Refactor incrementally while keeping the system working.

We do **not** rebuild everything at once. Actuarial capability order beats random file moves.

---

## Capability roadmap (refined)

### Phase 1 — Classical actuarial core

| Capability | Status |
|------------|--------|
| Credibility (Bühlmann–Straub) | ✅ `core/credibility/` (wraps `CredibilityParams`) |
| Reserving (CL, BF, ELR, F×S) | ✅ `core/reserving/` (re-exported from `engine_model`) |
| Markov projection | ⏳ `core/projection/` placeholder |

### Phase 2 — Risk engine

| Capability | Status |
|------------|--------|
| RiskEngine interface + class-rate (CT Flex Income) | ✅ |
| Gamma GLM as platform RiskEngine | ✅ `core/risk_engine/glm.py` + `predictor.py` (wraps `fremtpl_glm`; impl stays there) |
| Model registry | ⏳ later (`models/registry/`) |

### Phase 3 — Feature engineering (Actuarial Intelligence)

| Capability | Status |
|------------|--------|
| `features/` AKL package | ✅ financial / behavioural / occupational / environmental / aggregator |
| Feature groups + flatten + metadata | ✅ |
| `OccupationRiskTable` (data ≠ algorithm) | ✅ |
| CT Flex routed through AKL | ✅ |
| Deeper IRI / composite research | ⏳ ongoing |

### Phase 4 — Decision engine (modular depth)

| Capability | Status |
|------------|--------|
| DecisionEngine + CT Flex rules | ✅ skeleton works on orchestrator |
| Richer premium / benefit / reserve / explanation fusion | ⏳ deepen after AKL usage matures |

### Credibility note

AIC Credibility Framework is in `core/credibility/`: `CredibilityContext` → strategy (`BuhlmannStraubEngine`) → `CredibilityResult` (Z, class, drivers, metadata). See [`credibility_framework.md`](credibility_framework.md).

---

## Target end-state core

```text
core/
├── credibility/
│   └── buhlmann.py          # ✅ (wraps engine_model.CredibilityParams)
├── pricing/                 # ✅ package reserved
│   ├── ratemaking.py        # ⏳ from engine_model.RatemakingModel
│   └── pure_premium.py      # ⏳
├── risk_engine/
│   ├── base.py              # ✅
│   ├── class_rate.py        # ✅ CT Flex Phase 1
│   ├── glm.py               # ✅ GammaGLMRiskEngine
│   ├── predictor.py         # ✅ GlmPredictor
│   └── registry.py          # ⏳
├── projection/
│   └── markov.py            # ⏳
├── reserving/
│   ├── triangle.py          # ✅
│   └── model.py             # ✅ (CL/BF/ELR/FS; optional later file split)
└── explainability/
    └── explainer.py         # ✅
```

`engine_model.py` expands over time into **credibility + reserving + pricing**, not reserving alone.

---

## Completed platform scaffolding

| Item | Status |
|------|--------|
| Repository reorganization | ✅ |
| Contracts layer | ✅ |
| Product architecture (`products/ctflex`) | ✅ |
| Orchestrator | ✅ |
| CT Flex API → orchestrator (Income) | ✅ |
| Migration plan | ✅ |
| Step B — reserving split | ✅ |
| Step C — GLM RiskEngine wrapper | ✅ |

---

## Migration map (remaining fat modules)

| Current | Future | Action |
|---------|--------|--------|
| `engine_model` → `RatemakingModel` / expenses / experience | `core/pricing/ratemaking.py` | Move when pricing is needed as first-class API |
| `fremtpl_glm` implementation | stays; called via `GlmPredictor` | Keep until registry extraction |
| `fremtpl_glm.create_pricing_app` | `api/routes/pricing.py` | Later |
| `pricing_models/` joblibs | `models/registry/` + `deployed/` | Later |
| `portfolio_motor` / `claims_us` | `products/motor/` + training | Later |
| `ct_flex_product` underwrite | deprecate after v1 sunset | Trip/portfolio → `products/ctflex/` |
| `products/ctflex/features.py` | `features/financial.py` etc. | **Phase 3 next** |

---

## Execution order (updated)

| Step | Change | Status |
|------|--------|--------|
| **A** | Audit + migration map | ✅ |
| **B** | Split reserving → `core/reserving/` | ✅ |
| **C** | GLM → `core/risk_engine/{glm,predictor}.py` | ✅ |
| **D** | **Feature engineering layer** (AKL: financial / behavioural / occupational / environmental + aggregator) | ✅ |
| **E** | AIC Credibility Framework (CredibilityContext, classes, drivers; Bühlmann–Straub first strategy) | ✅ |
| **F** | **Pricing Engine** (pure → loads → technical → indicated commercial) | ✅ |
| **G** | Optional: move `RatemakingModel` into `core/pricing/ratemaking.py` | Later |
| **H** | Product adapters (`products/motor/`, health, …) on completed core | Later |
| **I** | `models/registry`; sunset underwrite v1 | Later |

**Platform actuarial core is complete** through Pricing. Further work is products + polish, not redesign.

---

## What we will not do in one go

- Rewrite GLM math
- Delete `engine_model.py` / `fremtpl_glm.py` before call sites use wrappers
- Force Health/Life onto orchestrator before rules + features exist
- Invent ChatGPT example filenames (`serve.py`, `train.py`) that this repo does not use

---

## Immediate next step

**Research evidence track:** benchmarking vs CT Flex TypeScript calculator, then technical report / paper. Motor adapter only after validation evidence is documented.
