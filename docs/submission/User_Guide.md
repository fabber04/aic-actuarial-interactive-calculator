# User Guide — AIC Platform v1.0 (RC1)

## What AIC is

A modular Python platform that turns product observations into explainable actuarial decisions:

**Adapter → AKL → Credibility → Risk → Pricing → Decision → Explain**

CT Flex Income is the first product path. Core layers are product-independent.

## Install

```bash
pip install -r requirements.txt
```

Python 3.10+ recommended.

## Quote a CT Flex applicant (library)

```bash
python -c "from aic.orchestrator import AICPlatform; import json; print(json.dumps(AICPlatform().quote_ctflex({'occupation':'Courier','transaction_count':8,'transactions':[10,12,8,15,14,11,9,13]}), indent=2))"
```

## Run evidence suites

```bash
python -m aic.validation
python -m aic.benchmark --write-report
python -m pytest tests -q
```

## REST API (optional)

```bash
python -m aic.api  # or project serve entrypoint documented in README
```

See `API_Documentation.md` for endpoint contracts. CT Flex MVP front-ends typically call `POST /ct-flex/underwrite`.

## Reading the response

| Field / object | Meaning |
|----------------|---------|
| Credibility \(Z\) / class | Weight on individual vs collective |
| Expected loss | Risk engine output |
| Technical / indicated commercial premium | Pricing engine outputs |
| Decision (Approve / Refer) | Product Decision Engine |
| Explanation factors | Structural explainability trail |
| `*metadata` | Method names, versions, audit inputs |

## Important limitations

Parameters and occupation tables are **illustrative**. Do not treat demo premiums as filed rates. See `docs/governance/limitations.md`.

## Where to go next

- Judges: start with `HOW_TO_READ_THIS_SUBMISSION.md`  
- Architecture: `docs/architecture.md` and research paper  
- Roadmap: `docs/ROADMAP.md`  
