# Assumptions Register

Explicit assumptions currently embedded in AIC Core v1 (CT Flex Income path).

| ID | Assumption | Value / form | Location |
|----|------------|--------------|----------|
| A1 | Income class rate | 0.0263 | `products/ctflex/rules.py` |
| A2 | Expense ratio | 0.12 | CT Flex rules → PricingAssumptions |
| A3 | Profit load | 0.05 | CT Flex rules → PricingAssumptions |
| A4 | Risk margin (pricing) | 0.03 | `orchestrator.assumptions_from_ctflex_rules` |
| A5 | Bühlmann k (transactions) | 50 | `BuhlmannStraubEngine(k=50)` |
| A6 | Z refer threshold | 0.12 | CT Flex rules |
| A7 | Benefit replacement ratio | 0.60 | CT Flex rules |
| A8 | Weekly benefit cap | 150 | CT Flex rules |
| A9 | Min PAYG premium rate | 0.015 | CT Flex rules |
| A10 | Occupation hazards | table `occupation_table_v1` | `features/occupational.py` |
| A11 | Technical premium formula | \((P+F)/(1-v-p-r-t)\) | `core/pricing/technical_rate.py` |
| A12 | Class-rate E[loss] | \(r_{adj} \times weekly\_income \times 4\) | `core/risk_engine/class_rate.py` |

## Review cadence

Revisit before any public demo, competition submission, or new product adapter.
