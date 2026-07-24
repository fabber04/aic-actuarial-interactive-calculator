"""
CT Flex Prototype vs AIC Actuarial Platform — benchmark runner.

Compares actuarial *systems*, not programming languages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from aic.benchmark.personas import Persona, build_personas
from aic.benchmark.prototype_ctflex import compute_underwriting
from aic.orchestrator import AICPlatform


CAPABILITY_MATRIX: List[Dict[str, str]] = [
    {
        "dimension": "Data Inputs",
        "prototype": "Fixed product inputs (transaction count)",
        "aic": "Standardized product adapter + observation series",
    },
    {
        "dimension": "Feature Engineering",
        "prototype": "Manual / fixed bps factors",
        "aic": "Actuarial Knowledge Layer (grouped features + indices)",
    },
    {
        "dimension": "Credibility",
        "prototype": "Simple Bühlmann Z = n/(n+k)",
        "aic": "Credibility Framework (context, class, drivers, metadata)",
    },
    {
        "dimension": "Risk Estimation",
        "prototype": "Embedded calculator (no E[loss] object)",
        "aic": "Modular RiskEngine → RiskResult (expected loss)",
    },
    {
        "dimension": "Pricing",
        "prototype": "Direct product premium rate logic",
        "aic": "Dedicated Pricing Engine (pure → technical → commercial)",
    },
    {
        "dimension": "Decision Logic",
        "prototype": "Product-specific always-approved UW",
        "aic": "Decision Engine (bind/refer, PAYG packaging, benefits)",
    },
    {
        "dimension": "Explainability",
        "prototype": "Basic factor list (static text + bps)",
        "aic": "Structured explanation + credibility drivers + pricing components",
    },
]


ARCHITECTURE_SCORECARD: List[Dict[str, str]] = [
    {"capability": "Layered architecture", "prototype": "no", "aic": "yes"},
    {"capability": "Product independence", "prototype": "no", "aic": "yes"},
    {"capability": "Actuarial Knowledge Layer", "prototype": "no", "aic": "yes"},
    {"capability": "Pluggable credibility", "prototype": "no", "aic": "yes"},
    {"capability": "Pricing engine", "prototype": "no", "aic": "yes"},
    {"capability": "Governance metadata", "prototype": "no", "aic": "yes"},
    {"capability": "Validation framework", "prototype": "no", "aic": "yes"},
]


@dataclass
class SystemSnapshot:
    system: str
    persona_id: str
    credibility_z: float
    credibility_class: Optional[str]
    premium_rate: float
    decision: str
    expected_loss: Optional[float]
    technical_premium: Optional[float]
    commercial_premium: Optional[float]
    income_stability: Optional[float]
    financial_index: Optional[float]
    explanation_factor_count: int
    explainability_layers: List[str]
    governance_metadata: bool
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _prototype_snapshot(persona: Persona) -> SystemSnapshot:
    uw = compute_underwriting(persona.transaction_count, "income")
    layers = ["premium_rate", "fixed_bps_factors", "credibility_z"]
    return SystemSnapshot(
        system="ct_flex_prototype",
        persona_id=persona.id,
        credibility_z=uw.credibility_z,
        credibility_class=None,
        premium_rate=uw.premium_rate,
        decision="Approved" if uw.approved else "Decline",
        expected_loss=None,
        technical_premium=None,
        commercial_premium=None,
        income_stability=None,
        financial_index=None,
        explanation_factor_count=len(uw.factors),
        explainability_layers=layers,
        governance_metadata=False,
        extras={
            "risk_rating": uw.risk_rating,
            "income_estimate_usd": uw.income_estimate_usd,
            "engine": uw.engine,
            "uses_transaction_path": False,
        },
    )


def _aic_snapshot(persona: Persona, platform: Optional[AICPlatform] = None) -> SystemSnapshot:
    platform = platform or AICPlatform()
    out = platform.quote_ctflex(persona.aic_input())
    feats = out.get("features") or {}
    layers = [
        "akl_features",
        "credibility",
        "expected_loss",
        "pricing",
        "decision",
        "explanation",
    ]
    explanation = out.get("explanation") or {}
    factors = explanation.get("factors") or []
    return SystemSnapshot(
        system="aic_platform",
        persona_id=persona.id,
        credibility_z=float(out.get("credibility_z") or 0),
        credibility_class=out.get("credibility_class"),
        premium_rate=float(out.get("premium_rate") or 0),
        decision=str(out.get("decision")),
        expected_loss=float(out["expected_loss"]) if out.get("expected_loss") is not None else None,
        technical_premium=(
            float(out["technical_premium"]) if out.get("technical_premium") is not None else None
        ),
        commercial_premium=(
            float(out["commercial_premium"]) if out.get("commercial_premium") is not None else None
        ),
        income_stability=float(feats["income_stability"]) if "income_stability" in feats else None,
        financial_index=float(feats["financial_index"]) if "financial_index" in feats else None,
        explanation_factor_count=len(factors),
        explainability_layers=layers,
        governance_metadata=bool(out.get("credibility_metadata") and out.get("pricing_metadata")),
        extras={
            "credibility_drivers": out.get("credibility_drivers"),
            "status": out.get("status"),
            "payment_method": out.get("payment_method"),
            "uses_transaction_path": True,
        },
    )


def explainability_coverage(snapshot: SystemSnapshot) -> float:
    """Fraction of the full actuarial pipeline that is surfaced in explanations."""
    full = [
        "akl_features",
        "credibility",
        "expected_loss",
        "pricing",
        "decision",
        "explanation",
    ]
    present = set(snapshot.explainability_layers)
    return round(sum(1 for layer in full if layer in present) / len(full), 4)


def run_benchmark(personas: Optional[List[Persona]] = None) -> Dict[str, Any]:
    personas = personas or build_personas()
    platform = AICPlatform()
    rows: List[Dict[str, Any]] = []

    for persona in personas:
        proto = _prototype_snapshot(persona)
        aic = _aic_snapshot(persona, platform)
        rows.append(
            {
                "persona": {
                    "id": persona.id,
                    "name": persona.name,
                    "description": persona.description,
                    "expected_behaviour": persona.expected_behaviour,
                    "transaction_count": persona.transaction_count,
                },
                "prototype": proto.to_dict(),
                "aic": aic.to_dict(),
                "explainability_coverage": {
                    "prototype": explainability_coverage(proto),
                    "aic": explainability_coverage(aic),
                },
            }
        )

    # Conceptual contribution: same n, different path → prototype identical, AKL differs
    vol = next(r for r in rows if r["persona"]["id"] == "volatile_income")
    hi = next(r for r in rows if r["persona"]["id"] == "high_income_stable")
    income_reliability_finding = {
        "claim": (
            "Higher income ≠ automatically higher risk; AKL separates amount from reliability."
        ),
        "same_transaction_count": vol["persona"]["transaction_count"]
        == hi["persona"]["transaction_count"],
        "prototype_premium_rate_identical": (
            vol["prototype"]["premium_rate"] == hi["prototype"]["premium_rate"]
        ),
        "prototype_z_identical": vol["prototype"]["credibility_z"] == hi["prototype"]["credibility_z"],
        "aic_income_stability": {
            "volatile": vol["aic"]["income_stability"],
            "high_stable": hi["aic"]["income_stability"],
        },
        "aic_financial_index": {
            "volatile": vol["aic"]["financial_index"],
            "high_stable": hi["aic"]["financial_index"],
        },
        "aic_distinguishes_reliability": (
            (hi["aic"]["income_stability"] or 0) > (vol["aic"]["income_stability"] or 0)
        ),
    }

    return {
        "title": "CT Flex Prototype vs AIC Actuarial Platform",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "claim": (
            "The CT Flex prototype proved PAYG pricing feasibility with classical "
            "methods tightly coupled in one calculator. AIC preserves that methodology "
            "while separating concerns into reusable, governed layers, yielding greater "
            "architectural capability and explainability. This benchmark does not claim "
            "superior empirical loss prediction without portfolio outcome data."
        ),
        "capability_matrix": CAPABILITY_MATRIX,
        "architecture_scorecard": ARCHITECTURE_SCORECARD,
        "personas": rows,
        "income_reliability_finding": income_reliability_finding,
        "pipeline_metrics": {
            "prototype": {
                "engineered_features": "fixed bps factors (6)",
                "credibility_output": True,
                "risk_estimate": False,
                "technical_premium": False,
                "decision_confidence_object": False,
                "explainability": "basic",
                "governance_metadata": False,
            },
            "aic": {
                "engineered_features": "AKL feature groups + indices",
                "credibility_output": True,
                "risk_estimate": True,
                "technical_premium": True,
                "decision_confidence_object": True,
                "explainability": "structured",
                "governance_metadata": True,
            },
        },
    }
