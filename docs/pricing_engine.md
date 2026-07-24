# AIC Pricing Engine

Separates **expected loss** from **premium**.

```text
RiskResult.expected_loss
        │
        ▼
   Pricing Engine
        │
        ├─ Pure Premium
        ├─ Expense Loading
        ├─ Profit Loading
        ├─ Risk Margin
        ├─ Taxes / Fees
        ▼
   Technical Premium
        │
        ├─ Discounts / floors
        ▼
   Indicated Commercial Premium
        │
        ▼
   Decision Engine  (PAYG %, annual bill, bind/refer)
```

## Modules

| File | Role |
|------|------|
| `base.py` | `PricingAssumptions`, `PricingResult`, `PricingEngine` |
| `pure_premium.py` | E(Loss) → pure premium |
| `expense_loading.py` | Expense helpers |
| `profit_loading.py` | Profit helpers |
| `technical_rate.py` | Classical loaded technical premium |
| `discounts.py` | Post-technical discounts |
| `commercial_rate.py` | Indicated commercial + minimum premium |
| `engine.py` | `StandardPricingEngine` |

## Formula (technical)

\[
\text{technical} = \frac{\text{pure} + \text{fixed expense}}{1 - v - p - r - t}
\]

where \(v,p,r,t\) are variable expense, profit, risk margin, and tax ratios.

## What pricing does *not* do

- PAYG trip splits
- Bind / refer / decline
- Benefit design

Those remain in the **Decision Engine**.

## CT Flex

`AICPlatform` maps `CTFlexRules` expense/profit loads into `PricingAssumptions`, then Decision Engine converts indicated commercial premium into a PAYG `% of earnings` rate for trip collection.
