# Figure 1 — Overall AIC Architecture

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"arial","fontSize":"14px","primaryColor":"#DCEAF7","primaryBorderColor":"#1E3A5F","primaryTextColor":"#0F172A","lineColor":"#475569","secondaryColor":"#E7F0E7","tertiaryColor":"#E8EEF4"}}}%%
flowchart TB
  classDef data fill:#E8EEF4,stroke:#334155,color:#0F172A,stroke-width:1.5px
  classDef core fill:#DCEAF7,stroke:#1E3A5F,color:#0F172A,stroke-width:1.5px
  classDef prod fill:#E7F0E7,stroke:#2F5D3A,color:#0F172A,stroke-width:1.5px

  C[Client / product UX]:::data
  A[Product Adapter]:::prod
  K[Actuarial Knowledge Layer]:::core
  F[FeatureVector + metadata]:::core
  Q[Credibility Framework]:::core
  R[Risk Engine]:::core
  P[Pricing Engine]:::core
  D[Decision Engine]:::prod
  E[Explainability]:::prod
  O[Decision + explanation]:::data

  C --> A --> K --> F --> Q --> R --> P --> D --> E --> O
```

**Caption.** End-to-end AIC v1.0 pipeline. Actuarial core layers (blue) are product-independent; green layers apply product packaging and communication. Products never call actuarial engines directly.
