# insurance_claims.csv

US-style **claim/incident** records (~1,000 rows). This is **not** the same as the motor portfolio dataset.

## Can I use the portfolio model here?

**No.** The deployed **portfolio** model expects European policy fields (`Type_risk`, `Power`, `R_Claims_history`, …). This file has different columns (`policy_state`, `policy_annual_premium`, `total_claim_amount`, …).

## Use the claims model instead

Same Gamma GLM engine, **separate profile** trained on this file (target = `policy_annual_premium`).

```bash
python fremtpl_glm.py claims-prep
python fremtpl_glm.py claims-fit
python fremtpl_glm.py claims-deploy
python fremtpl_glm.py claims-score    # -> Datasets/insurance_claims_scored.csv
python fremtpl_glm.py serve --profile claims --port 8001
```

Splits by `policy_bind_date` year: train ≤2011, valid 2012, holdout 2013.

**Note:** Rows are claims, not policy terms. Premium predictions describe `policy_annual_premium`; `total_claim_amount` is for comparison only and is not a model input.
