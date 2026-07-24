# Motor vehicle insurance portfolio

## Source files

| File | Role |
|------|------|
| `Motor vehicle insurance data.csv` | Raw term-level history (`;` separated, European dates) |
| `Descriptive of the variables.xlsx` | Data dictionary — check codes before modeling |

## Workflow

```bash
# 1. Clean, engineer features, temporal splits
python fremtpl_glm.py portfolio-prep

# 2. Grouped 5-fold CV on train (by policy ID)
python fremtpl_glm.py portfolio-cv --folds 5

# 3. Fit premium Gamma + freq×sev GLM; score holdout
python fremtpl_glm.py portfolio-fit

# 4. Deploy train+valid to live engine
python fremtpl_glm.py portfolio-deploy

# 5. API (portfolio profile)
python fremtpl_glm.py serve --profile portfolio --port 8000
```

## Outputs

| Path | Description |
|------|-------------|
| `motor_clean.csv` | Cleaned full book |
| `splits/motor_train.csv` | `term_year <= 2016` |
| `splits/motor_valid.csv` | `term_year == 2017` |
| `splits/motor_holdout.csv` | `term_year == 2018` |
| `splits/split_meta.json` | Row counts and year boundaries |
| `portfolio_cv_results.json` | CV mean deviance per fold |
| `portfolio_fit_summary.json` | Holdout metrics |
| `motor_holdout_scored.csv` | Holdout with `predicted_price` |

Live artifacts: `pricing_data/portfolio_pricing_store.csv`, `pricing_models/portfolio/`.

## Modeling notes

- **Target (premium model):** `price` = `Premium` (strictly positive).
- **Predictors:** lagged history (`R_Claims_history`), vehicle, driver age, geo/product — **not** same-term `N_claims_year` / `Cost_claims_year`.
- **Batch GLM:** Poisson on `claim_count` with exposure 1; Gamma severity on positive `claim_cost`.
- Adjust split years with `portfolio-prep --train-end 2016 --valid-end 2017 --holdout-year 2018` if needed.

## API predict example

See `/docs` at http://127.0.0.1:8000 after `serve`. Body uses portfolio feature names (`Type_risk`, `Area`, `Power`, `driver_age`, …).
