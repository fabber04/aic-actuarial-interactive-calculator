# AIC — Actuarial Interactive Calculator

Python toolkit for **property & casualty ratemaking**, **loss reserving**, and **GLM-based motor pricing**. Built around methods from *Introduction to Ratemaking and Loss Reserving for Property and Casualty Insurance* (Brown & Gottlieb), with extensions for live Gamma GLM pricing and real portfolio datasets.

**AIC Platform v1.0 · Release Candidate 1 — submission mode.**  
Allowed changes: bug fixes · presentation · reviewer wording. No new layers/products.  
Changelog: [`CHANGELOG.md`](CHANGELOG.md) · Evolution: [`docs/EVOLUTION.md`](docs/EVOLUTION.md) · Roadmap: [`docs/ROADMAP.md`](docs/ROADMAP.md)  
Judge pack: [`docs/submission/`](docs/submission/) · Paper: [`docs/research/paper.md`](docs/research/paper.md)  
Evidence: `python -m aic.validation` · `python -m aic.benchmark --write-report` · [`docs/governance/`](docs/governance/). CT Flex quotes:

```bash
python -c "from aic.orchestrator import AICPlatform; import json; print(json.dumps(AICPlatform().quote_ctflex({'occupation':'Courier','transaction_count':8,'transactions':[10,12,8,15,14,11,9,13]}), indent=2))"
```

---

## Features

| Area | What it does |
|------|----------------|
| **Ratemaking** | Pure-premium, loss-ratio, and credibility-weighted indicated rates |
| **Reserving** | Chain-Ladder, Bornhuetter–Ferguson, ELR, frequency–severity |
| **Batch GLM** | Poisson frequency × Gamma severity on freMTPL-style CSVs |
| **Live pricing engine** | Gamma GLM (log link), append-only store, joblib versioning, hot-swap, REST API |
| **Motor portfolio** | Clean EU motor data, temporal splits, grouped CV, deploy to API |
| **US claims** | Separate Gamma model for `insurance_claims.csv` |

---

## Requirements

- Python 3.10+ (tested on 3.14)
- See `requirements.txt`

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `statsmodels`, `patsy`, `joblib`, `fastapi`, `uvicorn`.

---

## Quick start

### 1. Actuarial engine demo (ratemaking + reserving)

```bash
python engine_model.py
```

Or double-click: `scripts\run_engine.bat`.

Self-check:

```bash
python engine_model.py verify
# or
scripts\verify.bat
```

### 2. freMTPL batch GLM pricing

```bash
python fremtpl_glm.py archive/freMTPL2freq.csv --out-dir archive
python fremtpl_glm.py archive/freMTPL2freq.csv --sev archive/freMTPL2sev.csv --out-dir archive
```

Or: `scripts\run_glm.bat archive\freMTPL2freq.csv`

Outputs in `archive/`: `*_glm_priced.csv`, `*_glm_coefficients.csv`, `*_glm_summary.csv`.

### 3. Motor portfolio (recommended real-data workflow)

```bash
python fremtpl_glm.py portfolio-prep
python fremtpl_glm.py portfolio-cv --folds 5
python fremtpl_glm.py portfolio-fit
python fremtpl_glm.py portfolio-deploy
python fremtpl_glm.py serve --profile portfolio --port 8000
```

See `Datasets/Dataset of an actual motor vehicle insurance portfolio/README.md`.

### 4. US claims file (`insurance_claims.csv`)

```bash
python fremtpl_glm.py claims-prep
python fremtpl_glm.py claims-fit
python fremtpl_glm.py claims-deploy
python fremtpl_glm.py claims-score
python fremtpl_glm.py serve --profile claims --port 8001
```

See `Datasets/insurance_claims_README.md`.

### 5. Run tests

```bash
python -m pytest tests -v
```

Or: `scripts\run_tests.bat`

### 6. CT Flex product slice (gig / microinsurance)

AIC covers the full actuarial toolkit. **CT Flex only consumes this slice** — credibility underwriting, Income/Health/Life class rates, trip PAYE, and portfolio KPIs — via `aic/ct_flex_product.py` on top of `aic.engine_model.CredibilityParams`.

```bash
python ct_flex_api.py --port 8000
# or
scripts\serve_ct_flex.bat
```

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness |
| `GET /ct-flex/capabilities` | Products + class rates |
| `POST /ct-flex/underwrite` | **Platform v2** Income quote (camelCase); Health/Life → v1 |
| `POST /ct-flex/underwrite/v1` | Legacy product-slice dual-run |
| `POST /ct-flex/quote` | Raw orchestrator JSON |
| `POST /ct-flex/trip-premium` | Pay-as-you-earn split |
| `POST /ct-flex/portfolio` | Admin portfolio KPIs |

Add `?dual=1` on underwrite to attach `legacyCompare`. CT Flex Vite proxies `/api/aic` → this service.

---

## Project structure

```
AIC/
├── README.md
├── requirements.txt
├── engine_model.py          # thin CLI → aic.engine_model
├── fremtpl_glm.py           # thin CLI → aic.fremtpl_glm
├── ct_flex_api.py           # thin CLI → aic.api.ct_flex
├── aic/                     # all library code
│   ├── engine_model.py      # classical ratemaking & reserving
│   ├── fremtpl_glm.py       # GLM + live pricing engine
│   ├── portfolio_motor.py   # EU motor portfolio workflow
│   ├── claims_us.py         # US claims workflow
│   ├── ct_flex_product.py   # CT Flex product slice
│   ├── model_verification.py
│   ├── orchestrator.py      # Platform v2 quote pipeline
│   ├── api/                 # FastAPI apps
│   ├── contracts/           # shared data objects
│   ├── core/                # credibility, risk, explainability
│   ├── products/ctflex/     # adapters & rules
│   └── decision/
├── tests/
├── docs/
├── scripts/                 # .bat helpers
├── archive/                 # freMTPL sample data
└── Datasets/                # portfolio & claims CSVs
```

---

## Core modules

### `engine_model.py`

Classical P&C actuarial engine:

- **RatemakingModel** — experience, expenses, credibility, trends, indicated rate
- **Reserving** — CL, BF, ELR, FS methods
- Demo CLI and `verify` mode

### `fremtpl_glm.py`

**Batch path** (freMTPL):

- Poisson GLM on claim counts with `log(Exposure)` offset
- Gamma GLM on severity (optional)
- Calibration via `RatemakingModel`
- CSV outputs

**Live engine** (Model definition):

- Strictly positive `price` target
- Shared `PricingPreprocessor` (rare levels, log transforms, scaling)
- Full-history retrain, joblib versioning, thread-safe hot-swap
- FastAPI: `/health`, `/metrics`, `/predict`, `/data/append`, `/retrain`

**Pricing profiles** (same engine, different column schemas):

| Profile | `--profile` | Store | Models |
|---------|-------------|-------|--------|
| freMTPL (bootstrap) | `fremtpl` (default) | `pricing_data/pricing_store.csv` | `pricing_models/` |
| Motor portfolio | `portfolio` | `pricing_data/portfolio_pricing_store.csv` | `pricing_models/portfolio/` |
| US claims | `claims` | `pricing_data/claims_pricing_store.csv` | `pricing_models/claims/` |

---

## REST API

Start the server (after `bootstrap`, `portfolio-deploy`, or `claims-deploy`):

```bash
python fremtpl_glm.py serve --profile portfolio --port 8000
```

- **Docs:** http://127.0.0.1:8000/docs  
- **Health:** http://127.0.0.1:8000/health  

Example predict body (portfolio profile):

```json
{
  "features": {
    "Type_risk": "1",
    "Area": "0",
    "Distribution_channel": "0",
    "Type_fuel": "P",
    "Second_driver": "0",
    "Payment": "0",
    "Power": 80,
    "driver_age": 45,
    "vehicle_age": 10,
    "Value_vehicle": 10000,
    "Seniority": 5,
    "R_Claims_history": 0.0
  }
}
```

Response: `{"prices": [312.45], "model_version": "YYYYMMDD_HHMMSS"}`

---

## Datasets

| Dataset | Rows | Use |
|---------|------|-----|
| `archive/freMTPL2freq.csv` | ~678k | Teaching / batch GLM (French motor third-party liability) |
| `Datasets/.../Motor vehicle insurance data.csv` | ~105k terms | Portfolio workflow; `;` separated, renewal-level |
| `Datasets/insurance_claims.csv` | ~1k | US claim records; **claims** profile only |

**Important:** Do not score `insurance_claims.csv` with the **portfolio** model (or vice versa). Each profile has its own features and trained artifact.

---

## CLI reference

### `engine_model.py`

| Command | Description |
|---------|-------------|
| `python engine_model.py` | Full demo |
| `python engine_model.py verify` | Verification |
| `python engine_model.py glm <freq.csv>` | Batch GLM via fremtpl_glm |

### `fremtpl_glm.py` — batch

```bash
python fremtpl_glm.py <freq.csv> [--sev sev.csv] [--out-dir dir] [--sample N]
```

### `fremtpl_glm.py` — live engine

| Command | Description |
|---------|-------------|
| `bootstrap <freq.csv>` | Seed store from freMTPL (synthetic price) |
| `ingest <records.csv>` | Append + retrain |
| `retrain` | Refit on full store |
| `rollback <version.joblib>` | Restore a saved version |
| `serve [--profile X] [--port N]` | REST API |

### `fremtpl_glm.py` — portfolio

| Command | Description |
|---------|-------------|
| `portfolio-prep` | Clean CSV, temporal splits |
| `portfolio-cv [--folds 5]` | GroupKFold CV on train (by policy ID) |
| `portfolio-fit` | Fit premium GLM + batch freq×sev; score holdout |
| `portfolio-deploy` | Load train+valid into live store |

### `fremtpl_glm.py` — claims

| Command | Description |
|---------|-------------|
| `claims-prep` | Clean & split `insurance_claims.csv` |
| `claims-fit` | Fit & score holdout |
| `claims-deploy` | Deploy to live engine |
| `claims-score` | Score full file → `insurance_claims_scored.csv` |

---

## Modeling notes

- **Premium models** use Gamma GLM with **log link**; target must be strictly positive.
- **Portfolio splits** are temporal: train ≤2016, valid 2017, holdout 2018 (by renewal year).
- **Claims splits** by bind year: train ≤2011, valid 2012, holdout 2013.
- **Leakage:** Same-term claim amounts are not used as premium predictors; lagged history (`R_Claims_history`) is used on the portfolio model.
- **Production:** After validation, deploy with `portfolio-deploy` or `claims-deploy`; monitor via `/metrics` (deviance, drift alerts).

---

## References

- Brown, R. & Gottlieb, R. — *Introduction to Ratemaking and Loss Reserving for Property and Casualty Insurance*
- freMTPL2 — French motor third-party liability benchmark data (`archive/`)
- `Model definition.txt` — live Gamma GLM pricing engine specification

---

## License

Educational / internal actuarial calculator project. Check data source terms for bundled datasets.
