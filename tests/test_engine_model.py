"""
Peer verification for engine_model.py — closed-form identities only (Brown / CAS-style P&C).

Each assertion recomputes quantities from definitions on the same inputs; no external
reference systems or golden files are required.

Includes:
- Classical square-root partial credibility (full-cred std 1082)
- Volume-weighted age-to-age factors (chain-ladder development)
- Chain Ladder, Expected Loss Ratio, Bornhuetter-Ferguson
- Ratemaking: pure premium with expense load

Run:  python engine_model.py verify
  or:  python -m pytest tests/test_engine_model.py -v
  or:  python -m unittest tests.test_engine_model
"""

from __future__ import annotations

import unittest

from aic.engine_model import (
    CredibilityParams,
    ExpenseStructure,
    ExperienceData,
    RatemakingModel,
    ReservingModel,
    Triangle,
)
from aic.core.reserving import ReservingModel as CoreReservingModel
from aic.core.reserving import Triangle as CoreTriangle



class TestCredibilityClassical(unittest.TestCase):
    """Classical (US P&C) square-root rule: Z = min(1, sqrt(n / n_full))."""

    def setUp(self) -> None:
        self.p = CredibilityParams(full_credibility_claims=1082)

    def test_full_credibility(self) -> None:
        self.assertAlmostEqual(self.p.credibility(1082.0), 1.0, places=6)
        self.assertEqual(self.p.credibility(2000.0), 1.0)

    def test_zero(self) -> None:
        self.assertEqual(self.p.credibility(0.0), 0.0)

    def test_half(self) -> None:
        n = 0.25 * 1082
        self.assertAlmostEqual(self.p.credibility(n), 0.5, places=6)

    def test_buhlmann_alternate(self) -> None:
        p2 = CredibilityParams(full_credibility_claims=1082, buhlmann_k=100.0)
        self.assertAlmostEqual(p2.credibility(100.0), 0.5, places=6)


class TestChainLadderHandBenchmark(unittest.TestCase):
    """
    3x3 run-off triangle (cumulative). Hand volume-weighted LDFs:
      12->24: (150+170)/(100+110) = 320/210
      24->36: 200/150
    CDF from dev 12: f12 * f24 * tail(1) = (320/210)*(200/150)
    """

    def test_reserving_reexported_from_core(self) -> None:
        self.assertIs(ReservingModel, CoreReservingModel)
        self.assertIs(Triangle, CoreTriangle)

    @staticmethod
    def _triangle() -> Triangle:
        f12_24 = (150.0 + 170.0) / (100.0 + 110.0)
        f24_36 = 200.0 / 150.0
        return Triangle(
            name="Test 3x3",
            accident_years=[0, 1, 2],
            dev_ages=[12, 24, 36],
            data=[
                [100.0, 150.0, 200.0],
                [110.0, 170.0, None],
                [120.0, None, None],
            ],
            earned_premiums=[1000.0, 1000.0, 1000.0],
        ), f12_24, f24_36

    def test_age_to_age(self) -> None:
        tri, f12_24, f24_36 = self._triangle()
        m = ReservingModel(tri, a_priori_lr=0.6, tail_factor=1.0)
        a2a = m.age_to_age_factors()
        self.assertAlmostEqual(a2a[0], f12_24, places=5)
        self.assertAlmostEqual(a2a[1], f24_36, places=5)

    def test_chain_ladder_ultimates(self) -> None:
        tri, f12_24, f24_36 = self._triangle()
        m = ReservingModel(tri, a_priori_lr=0.6, tail_factor=1.0)
        cl = m.chain_ladder()
        cdf_12 = f12_24 * f24_36
        self.assertAlmostEqual(cl["ultimates"][0], 200.0, places=2)
        self.assertAlmostEqual(cl["ultimates"][1], 170.0 * f24_36, places=2)
        self.assertAlmostEqual(cl["ultimates"][2], 120.0 * cdf_12, places=2)
        # IBNR = ult - latest known
        self.assertAlmostEqual(cl["ibnr"][0], 0.0, places=2)
        self.assertAlmostEqual(cl["ibnr"][1], 170.0 * f24_36 - 170.0, places=2)
        self.assertAlmostEqual(cl["ibnr"][2], 120.0 * cdf_12 - 120.0, places=2)

    def test_cumulative_ldfs_product(self) -> None:
        tri, f12_24, f24_36 = self._triangle()
        m = ReservingModel(tri, a_priori_lr=0.6, tail_factor=1.0)
        cum = m.cumulative_ldfs()
        self.assertAlmostEqual(cum[0], f12_24 * f24_36, places=5)
        self.assertAlmostEqual(cum[1], f24_36, places=5)
        self.assertAlmostEqual(cum[2], 1.0, places=5)


class TestExpectedLossRatio(unittest.TestCase):
    def test_elr_ultimates(self) -> None:
        tri = Triangle(
            name="ELR",
            accident_years=[2020, 2021],
            dev_ages=[12, 24],
            data=[[100.0, 120.0], [90.0, None]],
            earned_premiums=[1000.0, 2000.0],
        )
        m = ReservingModel(tri, a_priori_lr=0.65, tail_factor=1.0)
        elr = m.expected_loss_ratio()
        self.assertAlmostEqual(elr["ultimates"][0], 650.0, places=2)
        self.assertAlmostEqual(elr["ultimates"][1], 1300.0, places=2)
        # IBNR = ult - latest diagonal
        self.assertAlmostEqual(elr["ibnr"][0], 650.0 - 120.0, places=2)


class TestBornhuetterFerguson(unittest.TestCase):
    def test_bf_matches_formula(self) -> None:
        tri, f12_24, f24_36 = TestChainLadderHandBenchmark._triangle()
        a_priori = 0.6
        prem = 1000.0
        m = ReservingModel(tri, a_priori_lr=a_priori, tail_factor=1.0)
        bf = m.bornhuetter_ferguson()
        cum = m.cumulative_ldfs()
        # Most recent AY: row 2, latest 120 at col 0
        cdf = cum[0]
        pct = 1.0 - 1.0 / cdf
        expected_unrep = a_priori * prem * pct
        self.assertAlmostEqual(bf["ultimates"][2], 120.0 + expected_unrep, places=1)
        self.assertAlmostEqual(bf["ibnr"][2], expected_unrep, places=1)


class TestRatemakingPurePremium(unittest.TestCase):
    def test_pure_premium_and_load(self) -> None:
        exp = [
            ExperienceData(
                year=2022,
                exposure=10_000.0,
                earned_premium=5_000_000.0,
                claim_count=500.0,
                paid_losses=2_000_000.0,
                incurred_losses=2_200_000.0,
            )
        ]
        # freq 0.05, sev 4000, pp = 200 (from paid)
        rm = RatemakingModel(
            name="Test",
            experience=exp,
            expenses=ExpenseStructure(
                fixed_expense_per_unit=0.0,
                variable_expense_ratio=0.20,
                profit_contingency_load=0.05,
            ),
            credibility=CredibilityParams(full_credibility_claims=100),
            freq_trend=0.0,
            sev_trend=0.0,
            trend_period=0.0,
            current_rate=250.0,
        )
        # trend_period 0 => (1+0)^0 * (1+0)^0 = 1
        self.assertAlmostEqual(rm.combined_trend_factor(), 1.0, places=6)
        self.assertAlmostEqual(rm.weighted_frequency(), 0.05, places=6)
        self.assertAlmostEqual(rm.weighted_severity(), 4_000.0, places=6)
        # Indicated = 200 / (1 - 0.25) = 266.67
        self.assertAlmostEqual(rm.pure_premium_rate(), 200.0 / 0.75, places=2)

    def test_credibility_blends(self) -> None:
        exp = [
            ExperienceData(2020, 100.0, 10_000.0, 5.0, 2_000.0, 2_500.0),
        ]
        z = 0.3
        n = (z ** 2) * 1082
        rm = RatemakingModel(
            name="Z",
            experience=[ExperienceData(2020, 100.0, 10_000.0, n, 2_000.0, 2_500.0)],
            expenses=ExpenseStructure(0.0, 0.0, 0.0),
            credibility=CredibilityParams(full_credibility_claims=1082),
            freq_trend=0.0,
            sev_trend=0.0,
            trend_period=0.0,
            current_rate=100.0,
        )
        self.assertAlmostEqual(rm.credibility.credibility(n), z, places=2)
        pp = rm.pure_premium_rate()
        lr = rm.loss_ratio_rate()
        self.assertAlmostEqual(rm.credibility_rate(), z * pp + (1 - z) * lr, places=2)


class TestReservingInvariants(unittest.TestCase):
    def test_cl_ultimate_ge_latest(self) -> None:
        tri = Triangle(
            name="Inv",
            accident_years=[1, 2, 3],
            dev_ages=[12, 24],
            data=[[100.0, 130.0], [200.0, None], [50.0, None]],
            earned_premiums=[1.0, 1.0, 1.0],
        )
        m = ReservingModel(tri, a_priori_lr=0.5, tail_factor=1.02)
        cl = m.chain_ladder()
        for i, u in enumerate(cl["ultimates"]):
            if u is None:
                continue
            latest = tri.data[i][m._current_age_index(i)]
            assert latest is not None
            self.assertGreaterEqual(u, latest * 0.9999)


if __name__ == "__main__":
    unittest.main()
