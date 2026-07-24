# Figure 5 — Validation Workflow

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"arial","fontSize":"14px","lineColor":"#475569"}}}%%
flowchart TB
  classDef evid fill:#F4EDE0,stroke:#6B4F2A,color:#0F172A,stroke-width:1.5px
  classDef core fill:#DCEAF7,stroke:#1E3A5F,color:#0F172A,stroke-width:1.5px

  S[python -m aic.validation]:::evid
  A[AKL checks]:::core
  C[Credibility checks]:::core
  R[Risk checks]:::core
  P[Pricing checks]:::core
  D[Decision / explain checks]:::core
  G[Governance docs]:::evid
  B[Benchmark suite]:::evid
  REP[PASS / FAIL report]:::evid

  S --> A & C & R & P & D --> REP
  G -.-> REP
  B -.-> REP
```

**Caption.** Research validation verifies layer identities and decision rules. Governance documentation and the prototype benchmark supply complementary evidence; neither substitutes for real-world outcome studies.
