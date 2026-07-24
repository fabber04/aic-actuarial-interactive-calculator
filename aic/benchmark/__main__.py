"""
Run the CT Flex Prototype vs AIC actuarial-system benchmark.

  python -m aic.benchmark
  python -m aic.benchmark --json
  python -m aic.benchmark --write-report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from aic.benchmark.runner import run_benchmark


def _markdown_report(result: dict) -> str:
    lines: List[str] = []
    lines.append(f"# {result['title']}")
    lines.append("")
    lines.append(f"_Generated: {result['generated_at']}_")
    lines.append("")
    lines.append("## Narrative")
    lines.append("")
    lines.append(
        "The CT Flex prototype demonstrated the **feasibility** of PAYG "
        "microinsurance pricing using classical actuarial concepts (class rates "
        "and a simple Bühlmann Z). However, actuarial logic, pricing "
        "adjustments, and product rules were tightly coupled inside one "
        "calculator."
    )
    lines.append("")
    lines.append(
        "AIC separates those concerns into reusable layers—adapter, Actuarial "
        "Knowledge Layer, credibility, risk, pricing, decision, and "
        "explainability—enabling governance and extensibility while preserving "
        "the underlying actuarial methodology. This report therefore compares "
        "**actuarial systems**, not programming languages, and evaluates "
        "**architectural capability**, not predictive superiority."
    )
    lines.append("")
    lines.append("## Claim (defensible)")
    lines.append("")
    lines.append(result["claim"])
    lines.append("")
    lines.append("## Capability matrix")
    lines.append("")
    lines.append("| Dimension | CT Flex Prototype | AIC Platform |")
    lines.append("|-----------|-------------------|--------------|")
    for row in result["capability_matrix"]:
        lines.append(
            f"| {row['dimension']} | {row['prototype']} | {row['aic']} |"
        )
    lines.append("")
    lines.append("## Architecture scorecard")
    lines.append("")
    lines.append("| Capability | Prototype | AIC |")
    lines.append("|------------|-----------|-----|")
    for row in result["architecture_scorecard"]:
        p = "✅" if row["prototype"] == "yes" else "❌"
        a = "✅" if row["aic"] == "yes" else "❌"
        lines.append(f"| {row['capability']} | {p} | {a} |")
    lines.append("")
    lines.append("## Persona results")
    lines.append("")
    for row in result["personas"]:
        p = row["persona"]
        proto = row["prototype"]
        aic = row["aic"]
        cov = row["explainability_coverage"]
        lines.append(f"### {p['name']} (`{p['id']}`)")
        lines.append("")
        lines.append(p["description"])
        lines.append("")
        lines.append(f"**Expected behaviour:** {p['expected_behaviour']}")
        lines.append("")
        lines.append("| Metric | Prototype | AIC |")
        lines.append("|--------|-----------|-----|")
        lines.append(f"| Transaction count | {p['transaction_count']} | {p['transaction_count']} |")
        lines.append(f"| Credibility Z | {proto['credibility_z']} | {aic['credibility_z']} |")
        lines.append(
            f"| Credibility class | — | {aic.get('credibility_class') or '—'} |"
        )
        lines.append(f"| Decision | {proto['decision']} | {aic['decision']} |")
        lines.append(f"| Premium rate | {proto['premium_rate']} | {aic['premium_rate']} |")
        lines.append(
            f"| Expected loss | — | {aic.get('expected_loss') if aic.get('expected_loss') is not None else '—'} |"
        )
        lines.append(
            f"| Technical premium | — | {aic.get('technical_premium') if aic.get('technical_premium') is not None else '—'} |"
        )
        lines.append(
            f"| Income stability | — | {aic.get('income_stability') if aic.get('income_stability') is not None else '—'} |"
        )
        lines.append(
            f"| Explainability coverage | {cov['prototype']} | {cov['aic']} |"
        )
        lines.append(
            f"| Explanation factors | {proto['explanation_factor_count']} | {aic['explanation_factor_count']} |"
        )
        lines.append("")

    finding = result["income_reliability_finding"]
    lines.append("## Conceptual contribution — income amount vs reliability")
    lines.append("")
    lines.append(finding["claim"])
    lines.append("")
    lines.append(
        f"- Same transaction count for volatile vs high-stable: "
        f"**{finding['same_transaction_count']}**"
    )
    lines.append(
        f"- Prototype premium rates identical: "
        f"**{finding['prototype_premium_rate_identical']}** "
        f"(count-only calculator)"
    )
    lines.append(
        f"- AKL income_stability (volatile → high-stable): "
        f"**{finding['aic_income_stability']['volatile']} → "
        f"{finding['aic_income_stability']['high_stable']}**"
    )
    lines.append(
        f"- AKL distinguishes reliability: "
        f"**{finding['aic_distinguishes_reliability']}**"
    )
    lines.append("")
    lines.append("## Pipeline metrics (capability growth)")
    lines.append("")
    lines.append("| Metric | Prototype | AIC |")
    lines.append("|--------|-----------|-----|")
    pm = result["pipeline_metrics"]
    keys = [
        ("engineered_features", "Engineered features"),
        ("credibility_output", "Credibility output"),
        ("risk_estimate", "Risk estimate E[loss]"),
        ("technical_premium", "Technical premium"),
        ("decision_confidence_object", "Decision confidence object"),
        ("explainability", "Explainability"),
        ("governance_metadata", "Governance metadata"),
    ]
    for key, label in keys:
        lines.append(f"| {label} | {pm['prototype'][key]} | {pm['aic'][key]} |")
    lines.append("")
    lines.append("## Conclusion")
    lines.append("")
    lines.append(
        "The prototype remains a coherent product demo. AIC is the platform "
        "evolution of that methodology: the same classical building blocks, "
        "reorganized so that income **amount** and income **reliability** can "
        "differ when transaction counts do not; so that expected loss and "
        "technical premium are first-class objects; and so that thin history can "
        "trigger Refer rather than unconditional Approve. We do **not** claim "
        "better empirical loss prediction, improved loss ratios, or outperformance "
        "of production insurer systems without portfolio outcome data."
    )
    lines.append("")
    lines.append("See also: `docs/research/paper.md` §8.3 · `figures/fig06_benchmark.md`.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark CT Flex prototype vs AIC actuarial platform"
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write docs/research/ctflex_prototype_vs_aic_benchmark.md",
    )
    ns = parser.parse_args(argv)
    result = run_benchmark()

    if ns.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(result["title"])
        print("-" * 60)
        print(result["claim"])
        print()
        for row in result["personas"]:
            p = row["persona"]
            print(
                f"{p['name']}: proto Z={row['prototype']['credibility_z']} "
                f"rate={row['prototype']['premium_rate']} | "
                f"AIC Z={row['aic']['credibility_z']} "
                f"decision={row['aic']['decision']} "
                f"stability={row['aic']['income_stability']}"
            )
        finding = result["income_reliability_finding"]
        print()
        print(
            "Income reliability finding: AKL distinguishes "
            f"{finding['aic_distinguishes_reliability']} "
            f"(proto rates identical={finding['prototype_premium_rate_identical']})"
        )

    if ns.write_report:
        root = Path(__file__).resolve().parents[2]
        out = root / "docs" / "research" / "ctflex_prototype_vs_aic_benchmark.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_markdown_report(result), encoding="utf-8")
        print(f"Wrote {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
