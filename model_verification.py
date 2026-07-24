"""
Self-contained mathematical verification for engine_model.py.

No external systems or reference platforms: every check is a closed-form identity
that must hold if the implementation matches its documented formulas (Brown-style
P&C chain ladder, ELR, BF, credibility-weighted ratemaking).

Run:
  python engine_model.py verify
  python model_verification.py
"""

from __future__ import annotations

import math
import sys
from typing import Callable, List, Tuple

from engine_model import (
    CredibilityParams,
    ExpenseStructure,
    RatemakingModel,
    ReservingModel,
)


class VerificationError(Exception):
    """Raised when an internal algebraic identity fails."""


def _approx(a: float, b: float, tol: float = 1e-4) -> bool:
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def verify_ldf_chain(res: ReservingModel, tol: float = 1e-6) -> None:
    """Cumulative LDF at column i must equal chain[i]*chain[i+1]*...*chain[-1]."""
    a2a = res.age_to_age_factors()
    chain = a2a + [res.tail_factor]
    cum = res.cumulative_ldfs()
    if len(cum) != len(chain):
        raise VerificationError("cum_ldfs length mismatch vs age-to-age + tail")
    for i in range(len(chain)):
        prod = math.prod(chain[i:])
        if not _approx(cum[i], prod, tol):
            raise VerificationError(
                f"LDF chain mismatch at index {i}: cum={cum[i]} vs prod(chain[{i}:])={prod}"
            )


def verify_chain_ladder_closure(res: ReservingModel, tol: float = 1e-2) -> None:
    """For each AY: ultimate = latest_cumulative * CDF(dev age); IBNR = ultimate - latest."""
    cl = res.chain_ladder()
    cum = res.cumulative_ldfs()
    for i in range(res.tri.n_rows()):
        ci = res._current_age_index(i)
        latest = res.tri.data[i][ci]
        if latest is None or cl["ultimates"][i] is None:
            continue
        cdf = cum[ci]
        exp_ult = latest * cdf
        if not _approx(cl["ultimates"][i], exp_ult, tol):
            raise VerificationError(
                f"CL row {i}: ultimate {cl['ultimates'][i]} != latest*CDF {exp_ult}"
            )
        exp_ibnr = exp_ult - latest
        if not _approx(cl["ibnr"][i], exp_ibnr, tol):
            raise VerificationError(f"CL row {i}: IBNR inconsistent with ultimate-latest")


def verify_elr_closure(res: ReservingModel, tol: float = 1e-2) -> None:
    """ELR ultimate = a_priori_lr * earned_premium; IBNR = ultimate - latest diagonal."""
    if not res.tri.earned_premiums:
        raise VerificationError("ELR verification needs earned_premiums")
    elr = res.expected_loss_ratio()
    diag = res.tri.last_diagonal()
    for i, prem in enumerate(res.tri.earned_premiums):
        ult_exp = res.a_priori_lr * prem
        if not _approx(elr["ultimates"][i], ult_exp, tol):
            raise VerificationError(f"ELR row {i}: ultimate != LR x premium")
        latest = diag[i] if diag[i] is not None else 0.0
        if not _approx(elr["ibnr"][i], ult_exp - latest, tol):
            raise VerificationError(f"ELR row {i}: IBNR != ultimate - latest")


def verify_bf_closure(res: ReservingModel, tol: float = 1e-2) -> None:
    """BF: ultimate = latest + (1 - 1/CDF) * a_priori_lr * premium."""
    if not res.tri.earned_premiums:
        raise VerificationError("BF verification needs earned_premiums")
    bf = res.bornhuetter_ferguson()
    cum = res.cumulative_ldfs()
    for i, prem in enumerate(res.tri.earned_premiums):
        ci = res._current_age_index(i)
        latest = res.tri.data[i][ci]
        if latest is None or bf["ultimates"][i] is None:
            continue
        cdf = cum[ci]
        pct = 1.0 - 1.0 / cdf
        exp_ult = latest + res.a_priori_lr * prem * pct
        if not _approx(bf["ultimates"][i], exp_ult, tol):
            raise VerificationError(f"BF row {i}: ultimate does not match formula")
        if not _approx(bf["ibnr"][i], res.a_priori_lr * prem * pct, tol):
            raise VerificationError(f"BF row {i}: IBNR does not match expected unreported")


def verify_ratemaking_credibility_blend(rm: RatemakingModel, tol: float = 1e-4) -> None:
    """Indicated rate must equal Z * pure_premium_rate + (1-Z) * loss_ratio_rate."""
    z = rm.credibility.credibility(float(sum(e.claim_count for e in rm.experience)))
    pp = rm.pure_premium_rate()
    lr = rm.loss_ratio_rate()
    blended = z * pp + (1.0 - z) * lr
    cr = rm.credibility_rate()
    if not _approx(cr, blended, tol):
        raise VerificationError("Credibility-weighted rate != Z*PP + (1-Z)*LR")


def verify_credibility_monotone(cp, ns: List[float]) -> None:
    """Z(n) non-decreasing for square-root rule."""
    prev = -1.0
    for n in ns:
        z = cp.credibility(n)
        if z < prev - 1e-9:
            raise VerificationError("Credibility should be monotone in n")
        if z < 0 or z > 1 + 1e-9:
            raise VerificationError("Credibility outside [0,1]")
        prev = z


def verify_triangle(res: ReservingModel) -> None:
    verify_ldf_chain(res)
    verify_chain_ladder_closure(res)
    if res.tri.earned_premiums:
        verify_elr_closure(res)
        verify_bf_closure(res)


def verify_all_demo_models() -> Tuple[int, int]:
    """Run algebraic checks on every built-in triangle in engine_model."""
    from engine_model import (
        build_liability_data,
        build_motor_liability_data,
        build_property_fire_data,
    )

    checks: List[Tuple[str, Callable[[], None]]] = []

    motor_exp, motor_tri = build_motor_liability_data()
    checks.append(
        (
            "Motor BI triangle",
            lambda: verify_triangle(
                ReservingModel(motor_tri, a_priori_lr=0.72, tail_factor=1.050)
            ),
        )
    )

    _, prop_tri = build_property_fire_data()
    checks.append(
        (
            "Property/Fire triangle",
            lambda: verify_triangle(
                ReservingModel(prop_tri, a_priori_lr=0.68, tail_factor=1.010)
            ),
        )
    )

    _, liab_tri = build_liability_data()
    checks.append(
        (
            "Liability triangle",
            lambda: verify_triangle(
                ReservingModel(liab_tri, a_priori_lr=0.75, tail_factor=1.150)
            ),
        )
    )

    motor_rm = RatemakingModel(
        name="Motor - Bodily Injury Liability",
        experience=motor_exp,
        expenses=ExpenseStructure(
            fixed_expense_per_unit=12.0,
            variable_expense_ratio=0.18,
            profit_contingency_load=0.05,
        ),
        credibility=CredibilityParams(
            full_credibility_claims=1082
        ),
        freq_trend=-0.01,
        sev_trend=0.07,
        trend_period=2.5,
        current_rate=85.00,
    )
    checks.append(("Motor ratemaking credibility blend", lambda: verify_ratemaking_credibility_blend(motor_rm)))

    passed = 0
    for name, fn in checks:
        fn()
        passed += 1

    return passed, len(checks)


def main() -> int:
    """Run identity checks + classical credibility sanity + unit tests."""
    print(
        "AIC self-verification (algebraic closure, no external gold standards)\n",
        flush=True,
    )

    cp = CredibilityParams(full_credibility_claims=1082)
    verify_credibility_monotone(cp, [0.0, 100.0, 271.0, 1082.0, 5000.0])

    n_ok, n_tot = verify_all_demo_models()
    print(
        f"  Demo triangles + ratemaking: {n_ok}/{n_tot} verification groups passed.",
        flush=True,
    )

    print("\n  Running mathematical unit tests ...\n", flush=True)
    try:
        import test_engine_model as te

        loader = __import__("unittest").TestLoader()
        suite = loader.loadTestsFromModule(te)
        runner = __import__("unittest").TextTestRunner(verbosity=0)
        result = runner.run(suite)
        if not result.wasSuccessful():
            return 1
    except Exception as e:
        print(f"  Unit tests skipped or failed to load: {e}")
        return 1

    print("\n  All self-verification steps completed successfully.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
