# API Documentation — AIC Platform v1.0 (RC1)

**Primary service:** CT Flex FastAPI app (`python ct_flex_api.py` or `scripts/serve_ct_flex.bat`)  
**Platform model version:** `aic-platform-1.0.0`

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/ct-flex/capabilities` | Products + class rates |
| `POST` | `/ct-flex/underwrite` | Platform orchestrator quote for **Income** (camelCase CT Flex contract); Health/Life fall back to v1 |
| `POST` | `/ct-flex/underwrite/v1` | Legacy product-slice dual-run path |
| `POST` | `/ct-flex/quote` | Raw orchestrator JSON |
| `POST` | `/ct-flex/trip-premium` | Pay-as-you-earn split |
| `POST` | `/ct-flex/portfolio` | Admin portfolio KPIs |

Add `?dual=1` on underwrite to attach `legacyCompare` for migration checks.

## Income underwrite (conceptual body)

Minimum fields used by the v1.0 Income path (illustrative):

```json
{
  "occupation": "Courier",
  "transaction_count": 8,
  "transactions": [10, 12, 8, 15, 14, 11, 9, 13]
}
```

Responses include decision fields plus governance metadata (`modelVersion`, feature / credibility / pricing metadata) for audit.

## Library equivalent

```python
from aic.orchestrator import AICPlatform

result = AICPlatform().quote_ctflex({
    "occupation": "Courier",
    "transaction_count": 8,
    "transactions": [10, 12, 8, 15, 14, 11, 9, 13],
})
```

## Design rule

Products never call actuarial engines directly. HTTP handlers invoke the orchestrator (or the dual-run legacy slice), which composes Adapter → AKL → Credibility → Risk → Pricing → Decision → Explain.

## Separate GLM pricing API

Motor / claims live GLM servers (`fremtpl_glm.py serve`) are part of the broader toolkit and are **not** required for the CT Flex Income v1.0 research path. See the root `README.md` for those endpoints.
