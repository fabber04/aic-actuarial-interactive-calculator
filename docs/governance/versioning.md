# Versioning

## Platform

| Component | Version field | Current |
|-----------|---------------|---------|
| AIC package | `aic.__version__` | `1.0.0` (**v1.0 RC1**) |
| Orchestrator API model | `PLATFORM_MODEL_VERSION` | `aic-platform-1.0.0` |
| Feature layer | `FEATURE_LAYER_VERSION` | `1.0.0` |
| Credibility (Bühlmann–Straub) | `method_version` | `1.0.0` |
| Pricing engine | `method_version` | `1.0.0` |
| Validation suite | `ValidationSuiteReport.version` | `1.0.0` |
| Release train | — | **AIC Platform v1.0 · Release Candidate 1** |

## Freeze

**AIC Platform v1.0 RC1 is in submission mode.** Allowed changes: bug fixes, presentation improvements, reviewer-requested wording. No new actuarial layers, products, or architectural redesign. Deferred work lives in [`docs/ROADMAP.md`](../ROADMAP.md). Release notes: [`docs/submission/RELEASE_RC1.md`](../submission/RELEASE_RC1.md).

## Rules

- Bump **feature_version** when AKL formulae or group definitions change.
- Bump **credibility / pricing method_version** when mathematics or default assumptions change.
- Bump **PLATFORM_MODEL_VERSION** when quote JSON contracts change in a client-visible way.
- Keep dual-run `/ct-flex/underwrite/v1` until CT Flex MVP confirms the new contract.

## Artifacts

- Joblib GLM bundles already carry `version_id` via `fremtpl_glm`.
- Quote responses include `feature_metadata`, `credibility_metadata`, and `pricing_metadata` for audit trails.
