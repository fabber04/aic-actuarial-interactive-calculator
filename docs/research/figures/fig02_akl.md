# Figure 2 — Actuarial Knowledge Layer

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"arial","fontSize":"14px","lineColor":"#475569"}}}%%
flowchart TB
  classDef data fill:#E8EEF4,stroke:#334155,color:#0F172A,stroke-width:1.5px
  classDef core fill:#DCEAF7,stroke:#1E3A5F,color:#0F172A,stroke-width:1.5px
  classDef grp fill:#F8FAFC,stroke:#1E3A5F,color:#0F172A,stroke-width:1.2px

  SD[StandardizedData]:::data
  FIN[Financial features]:::grp
  BEH[Behavioural features]:::grp
  OCC[Occupational features]:::grp
  ENV[Environmental features]:::grp
  MERGE[Feature groups + indices]:::core
  FV[FeatureVector + metadata]:::core

  SD --> FIN & BEH & OCC & ENV --> MERGE --> FV
```

**Caption.** Observations become actuarial concepts before credibility or risk estimation. Groups are retained for dashboards; a flattened vector feeds downstream engines. Occupation hazards are table-driven assumptions, not hard-coded business rules.
