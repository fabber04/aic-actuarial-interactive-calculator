"""
AIC Actuarial Model — Motor & General P&C
==========================================

Covers:

  1. Ratemaking  (Chapter 3 of Brown & Gottlieb)
  2. Loss Reserving (Chapter 4 of Brown & Gottlieb)

Supports:
  - Motor: Liability / Medical / UM-UIM / Collision / OTC
  - General P&C: Property/Fire (short-tail) / Liability (long-tail)

Methods implemented in our code: 


  - Ratemaking   : Pure-premium, Loss-ratio, Credibility-weighted
  - Reserving    : Chain-Ladder (CL), Bornhuetter–Ferguson (BF),
                   Expected Loss Ratio (ELR), Frequency–Severity (FS)

Usage
  python engine_model.py              Full demo output
  python engine_model.py verify       Self-verification (algebraic checks + tests)
  python engine_model.py glm <freq.csv> [--sev sev.csv]  GLM price freMTPL-style CSV
  python fremtpl_glm.py <freq.csv> [--sev sev.csv] [--out-dir archive]
  Or double-click: run_engine.bat (demo) / run_glm.bat (CSV pricing)







"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(val: float, decimals: int = 4) -> str:
    return f"{val:,.{decimals}f}"

def _pct(val: float) -> str:
    return f"{val*100:.2f}%"

def _banner(title: str, width: int = 70) -> None:
    # ASCII only — Windows cp1252 consoles cannot print box-drawing characters.
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)

def _section(title: str, width: int = 70) -> None:
    print("\n" + "-" * width)
    print(f"  {title}")
    print("-" * width)


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ExperienceData:
    """
    One accident-year slice of experience (Ch 3.4).
    Supports Motor (per coverage) and General P&C (per peril).
    """
    year: int
    exposure: float          # car-years / house-years / earned exposure units
    earned_premium: float    # on-level premium (Ch 3.8 on-level adjustment)
    claim_count: float       # reported claim count
    paid_losses: float       # paid losses to date
    incurred_losses: float   # paid + case reserves
    # optional trend & development carry-forwards
    trend_factor: float = 1.0
    on_level_factor: float = 1.0

    @property
    def frequency(self) -> float:
        """Claim frequency per exposure unit (Ch 3.3)."""
        return self.claim_count / self.exposure if self.exposure else 0.0

    @property
    def severity(self) -> float:
        """Average paid severity (Ch 3.3)."""
        return self.paid_losses / self.claim_count if self.claim_count else 0.0

    @property
    def pure_premium(self) -> float:
        """Pure premium = Frequency × Severity (Ch 3.3)."""
        return self.paid_losses / self.exposure if self.exposure else 0.0

    @property
    def loss_ratio(self) -> float:
        """Incurred loss ratio (Ch 3.3)."""
        return self.incurred_losses / self.earned_premium if self.earned_premium else 0.0


@dataclass
class ExpenseStructure:
    """
    Expense and profit parameters (Ch 3.8.3–3.8.4).
    Fixed expenses allocated per exposure; variable as % of premium.
    """
    fixed_expense_per_unit: float = 0.0   # e.g. USD per car-year
    variable_expense_ratio: float = 0.0   # % of premium (commissions, taxes)
    profit_contingency_load: float = 0.05 # default 5 %

    @property
    def total_variable(self) -> float:
        return self.variable_expense_ratio + self.profit_contingency_load


@dataclass
class CredibilityParams:
    """Full-credibility standards and partial credibility (Ch 3.8.5)."""
    full_credibility_claims: int = 1082   # standard classical full-cred. threshold
    # Bühlmann k — alternative; set to None to use square-root rule
    buhlmann_k: Optional[float] = None

    def credibility(self, n_claims: float) -> float:
        """
        Classical square-root partial credibility:
          Z = min(1, sqrt(n / n_full))
        """
        if self.buhlmann_k is not None:
            return n_claims / (n_claims + self.buhlmann_k)
        return min(1.0, math.sqrt(n_claims / self.full_credibility_claims))


# ─────────────────────────────────────────────────────────────────────────────
# 2. RATEMAKING MODULE  (Chapter 3)
# ─────────────────────────────────────────────────────────────────────────────

class RatemakingModel:
    """
    Implements the Brown & Gottlieb ratemaking framework.

    Parameters
    ----------
    name          : label for this model run (e.g. "Motor – Liability")
    experience    : list of ExperienceData, ordered by accident year
    expenses      : ExpenseStructure
    credibility   : CredibilityParams
    freq_trend    : annual frequency trend (e.g. -0.02 for -2 %/yr)
    sev_trend     : annual severity trend  (e.g.  0.05 for +5 %/yr)
    trend_period  : number of years to project (exposure mid-point to future)
    current_rate  : current average rate per exposure unit
    """

    def __init__(
        self,
        name: str,
        experience: List[ExperienceData],
        expenses: ExpenseStructure,
        credibility: CredibilityParams,
        freq_trend: float = 0.0,
        sev_trend: float = 0.05,
        trend_period: float = 2.0,
        current_rate: float = 1.0,
    ):
        self.name = name
        self.experience = sorted(experience, key=lambda x: x.year)
        self.expenses = expenses
        self.credibility = credibility
        self.freq_trend = freq_trend
        self.sev_trend = sev_trend
        self.trend_period = trend_period
        self.current_rate = current_rate

    # ── 2.1  Component summaries ──────────────────────────────────────────────

    def weighted_frequency(self) -> float:
        """Exposure-weighted average frequency across accident years."""
        total_exp = sum(e.exposure for e in self.experience)
        if not total_exp:
            return 0.0
        return sum(e.claim_count for e in self.experience) / total_exp

    def weighted_severity(self) -> float:
        """Count-weighted average severity across accident years."""
        total_claims = sum(e.claim_count for e in self.experience)
        if not total_claims:
            return 0.0
        return sum(e.paid_losses for e in self.experience) / total_claims

    def weighted_loss_ratio(self) -> float:
        """Premium-weighted average incurred loss ratio."""
        total_prem = sum(e.earned_premium for e in self.experience)
        if not total_prem:
            return 0.0
        return sum(e.incurred_losses for e in self.experience) / total_prem

    # ── 2.2  Trend factors (Ch 3.8.2) ────────────────────────────────────────

    def combined_trend_factor(self) -> float:
        """
        Combined trend factor applied to pure premium:
          T = (1 + freq_trend)^t × (1 + sev_trend)^t
        """
        return ((1 + self.freq_trend) ** self.trend_period *
                (1 + self.sev_trend)  ** self.trend_period)

    # ── 2.3  Indicated rates ──────────────────────────────────────────────────

    def pure_premium_rate(self) -> float:
        """
        Pure-premium method (Ch 3.5):
          Indicated Rate = (Trended Developed Pure Premium + Fixed Expense)
                           / (1 - Variable Ratio - Profit Load)
        """
        pp = self.weighted_frequency() * self.weighted_severity()
        trended_pp = pp * self.combined_trend_factor()
        numerator = trended_pp + self.expenses.fixed_expense_per_unit
        denominator = 1 - self.expenses.total_variable
        if denominator <= 0:
            raise ValueError("Variable expense + profit load >= 100%")
        return numerator / denominator

    def loss_ratio_rate(self) -> float:
        """
        Loss-ratio method (Ch 3.6):
          Rate Change = (Trended LR / Permissible LR) - 1
          Permissible LR = 1 - Variable Ratio - Profit Load - Fixed Expense Ratio
        """
        permissible_lr = (1 - self.expenses.total_variable -
                          self.expenses.fixed_expense_per_unit / self.current_rate
                          if self.current_rate else 0.0)
        if permissible_lr <= 0:
            return self.current_rate  # guard
        trended_lr = self.weighted_loss_ratio() * self.combined_trend_factor()
        change = trended_lr / permissible_lr - 1
        return self.current_rate * (1 + change)

    def credibility_rate(self) -> float:
        """
        Credibility-weighted indicated rate (Ch 3.8.5):
          Z × PP_method + (1 - Z) × LR_method
        """
        total_claims = sum(e.claim_count for e in self.experience)
        z = self.credibility.credibility(total_claims)
        pp = self.pure_premium_rate()
        lr = self.loss_ratio_rate()
        return z * pp + (1 - z) * lr

    def rate_change_pct(self) -> float:
        """Percentage change from current to credibility-indicated rate."""
        indicated = self.credibility_rate()
        return (indicated / self.current_rate - 1) if self.current_rate else 0.0

    # ── 2.4  Report ───────────────────────────────────────────────────────────

    def report(self) -> None:
        _banner(f"RATEMAKING - {self.name}")

        total_exp     = sum(e.exposure        for e in self.experience)
        total_prem    = sum(e.earned_premium  for e in self.experience)
        total_claims  = sum(e.claim_count     for e in self.experience)
        total_paid    = sum(e.paid_losses     for e in self.experience)
        total_incurred= sum(e.incurred_losses for e in self.experience)

        _section("Experience Summary")
        print(f"  {'Year':<8} {'Exposure':>12} {'Earned Prem':>14} "
              f"{'Claims':>10} {'Paid Loss':>13} {'Inc. Loss':>13} "
              f"{'Freq':>9} {'Sev':>10} {'LR':>8}")
        print("  " + "-" * 100)
        for e in self.experience:
            print(f"  {e.year:<8} {_fmt(e.exposure,0):>12} {_fmt(e.earned_premium,0):>14} "
                  f"{_fmt(e.claim_count,0):>10} {_fmt(e.paid_losses,0):>13} "
                  f"{_fmt(e.incurred_losses,0):>13} "
                  f"{_fmt(e.frequency,4):>9} {_fmt(e.severity,0):>10} {_pct(e.loss_ratio):>8}")
        print("  " + "-" * 100)
        print(f"  {'TOTAL':<8} {_fmt(total_exp,0):>12} {_fmt(total_prem,0):>14} "
              f"{_fmt(total_claims,0):>10} {_fmt(total_paid,0):>13} {_fmt(total_incurred,0):>13}")

        _section("Trend & Development")
        print(f"  Frequency trend  : {_pct(self.freq_trend)}/yr  x  {self.trend_period} yrs")
        print(f"  Severity trend   : {_pct(self.sev_trend)}/yr  x  {self.trend_period} yrs")
        print(f"  Combined trend   : {_fmt(self.combined_trend_factor(),4)}")

        _section("Expense Structure")
        print(f"  Fixed expense / unit    : {_fmt(self.expenses.fixed_expense_per_unit)}")
        print(f"  Variable expense ratio  : {_pct(self.expenses.variable_expense_ratio)}")
        print(f"  Profit & contingency    : {_pct(self.expenses.profit_contingency_load)}")
        print(f"  Total variable + profit : {_pct(self.expenses.total_variable)}")

        _section("Credibility")
        total_claims_float = float(total_claims)
        z = self.credibility.credibility(total_claims_float)
        print(f"  Total claims in period  : {_fmt(total_claims_float,0)}")
        print(f"  Full-cred. standard     : {self.credibility.full_credibility_claims:,} claims")
        print(f"  Credibility Z           : {_fmt(z,4)}")

        _section("Indicated Rates")
        print(f"  Weighted frequency (trended) : {_fmt(self.weighted_frequency()*self.combined_trend_factor(),5)}")
        print(f"  Weighted severity  (trended) : {_fmt(self.weighted_severity()*(1+self.sev_trend)**self.trend_period,2)}")
        pp = self.pure_premium_rate()
        lr = self.loss_ratio_rate()
        cr = self.credibility_rate()
        print(f"\n  Pure-premium method rate     : {_fmt(pp,2)}")
        print(f"  Loss-ratio method rate       : {_fmt(lr,2)}")
        print(f"  Credibility-weighted rate    : {_fmt(cr,2)}")
        print(f"\n  Current rate                 : {_fmt(self.current_rate,2)}")
        chg = self.rate_change_pct()
        arrow = "+" if chg > 0 else "-"
        print(f"  Indicated rate change        : {arrow} {_pct(abs(chg))}  ({'+' if chg>=0 else ''}{_pct(chg)})")


# ─────────────────────────────────────────────────────────────────────────────
# 3. LOSS RESERVING MODULE  (Chapter 4)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Triangle:
    """
    Development triangle (Ch 4.5).
    rows    = accident years (earliest first)
    columns = development ages in months (12, 24, 36, …)
    None    = future cell
    """
    name: str
    accident_years: List[int]
    dev_ages: List[int]                        # e.g. [12, 24, 36, 48]
    data: List[List[Optional[float]]]          # cumulative losses
    earned_premiums: Optional[List[float]] = None  # per AY — for BF/ELR

    def __post_init__(self):
        assert len(self.data) == len(self.accident_years)
        for row in self.data:
            assert len(row) == len(self.dev_ages)

    def n_rows(self) -> int:
        return len(self.accident_years)

    def n_cols(self) -> int:
        return len(self.dev_ages)

    def last_diagonal(self) -> List[Optional[float]]:
        """Latest known value for each accident year."""
        diag = []
        for i, row in enumerate(self.data):
            # latest non-None in row
            val = None
            for v in reversed(row):
                if v is not None:
                    val = v
                    break
            diag.append(val)
        return diag

    def col_data(self, col: int) -> List[Optional[float]]:
        return [self.data[r][col] for r in range(self.n_rows())]


class ReservingModel:
    """
    Implements four reserving methods from Brown & Gottlieb Ch 4.

    Parameters
    ----------
    triangle   : Triangle object
    a_priori_lr: a priori loss ratio used in BF and ELR methods
    tail_factor: LDF beyond last development age (default 1.0 = fully developed)
    """

    def __init__(
        self,
        triangle: Triangle,
        a_priori_lr: float = 0.70,
        tail_factor: float = 1.0,
    ):
        self.tri = triangle
        self.a_priori_lr = a_priori_lr
        self.tail_factor = tail_factor

    # ── 3.1  Age-to-age factors (Ch 4.6.3) ───────────────────────────────────

    def age_to_age_factors(self) -> List[float]:
        """
        Volume-weighted LDFs for each consecutive age pair.
        Uses only cells where both the current and next age are known (upper-left).
        """
        ldfs = []
        for c in range(self.tri.n_cols() - 1):
            num = den = 0.0
            for r in range(self.tri.n_rows()):
                curr = self.tri.data[r][c]
                nxt  = self.tri.data[r][c + 1]
                if curr is not None and nxt is not None:
                    den += curr
                    num += nxt
            ldfs.append(num / den if den else 1.0)
        return ldfs

    def cumulative_ldfs(self) -> List[float]:
        """
        CDF to ultimate for each development age (incl. tail factor).
        ldfs[-1] is the tail applied to the last age.
        """
        a2a = self.age_to_age_factors()
        # append tail
        a2a_with_tail = a2a + [self.tail_factor]
        n = len(a2a_with_tail)
        cum = [1.0] * n
        cum[-1] = a2a_with_tail[-1]
        for i in range(n - 2, -1, -1):
            cum[i] = cum[i + 1] * a2a_with_tail[i]
        return cum  # cum[0] = LDF from age 12 to ultimate, etc.

    def _current_age_index(self, ay_index: int) -> int:
        """Index of latest known column for this accident-year row."""
        row = self.tri.data[ay_index]
        for c in range(len(row) - 1, -1, -1):
            if row[c] is not None:
                return c
        return 0

    # ── 3.2  Chain-Ladder (Ch 4.6.3) ─────────────────────────────────────────

    def chain_ladder(self) -> Dict:
        """
        Project each AY to ultimate using its age-specific CDF.
        Returns dict with 'ultimates', 'ibnr', 'ldfs'.
        """
        cum_ldfs = self.cumulative_ldfs()
        ultimates = []
        ibnr_list = []
        for i in range(self.tri.n_rows()):
            ci = self._current_age_index(i)
            latest = self.tri.data[i][ci]
            if latest is None:
                ultimates.append(None)
                ibnr_list.append(None)
                continue
            cdf = cum_ldfs[ci]
            ult = latest * cdf
            ultimates.append(ult)
            ibnr_list.append(ult - latest)
        return {
            "method": "Chain Ladder",
            "ldfs_a2a": self.age_to_age_factors(),
            "cum_ldfs": cum_ldfs,
            "ultimates": ultimates,
            "ibnr": ibnr_list,
            "total_ibnr": sum(x for x in ibnr_list if x is not None),
            "total_ultimate": sum(x for x in ultimates if x is not None),
        }

    # ── 3.3  Expected Loss Ratio (Ch 4.6.2) ──────────────────────────────────

    def expected_loss_ratio(self) -> Dict:
        """
        ELR method: ultimate = ELR × earned premium.
        Requires earned_premiums on the triangle.
        """
        if self.tri.earned_premiums is None:
            raise ValueError("ELR method requires earned_premiums on Triangle.")
        ultimates, ibnr_list = [], []
        diag = self.tri.last_diagonal()
        for i, prem in enumerate(self.tri.earned_premiums):
            ult = self.a_priori_lr * prem
            latest = diag[i] if diag[i] is not None else 0.0
            ultimates.append(ult)
            ibnr_list.append(ult - latest)
        return {
            "method": "Expected Loss Ratio",
            "a_priori_lr": self.a_priori_lr,
            "ultimates": ultimates,
            "ibnr": ibnr_list,
            "total_ibnr": sum(ibnr_list),
            "total_ultimate": sum(ultimates),
        }

    # ── 3.4  Bornhuetter–Ferguson (Ch 4.6.4) ─────────────────────────────────

    def bornhuetter_ferguson(self) -> Dict:
        """
        BF ultimate = Actual paid + % unreported × ELR × premium
        % unreported for age i = 1 - 1/CDF_i
        """
        if self.tri.earned_premiums is None:
            raise ValueError("BF method requires earned_premiums on Triangle.")
        cum_ldfs = self.cumulative_ldfs()
        ultimates, ibnr_list = [], []
        for i, prem in enumerate(self.tri.earned_premiums):
            ci = self._current_age_index(i)
            latest = self.tri.data[i][ci]
            if latest is None:
                ultimates.append(None); ibnr_list.append(None); continue
            cdf = cum_ldfs[ci]
            pct_unreported = 1 - 1 / cdf
            expected_unreported = self.a_priori_lr * prem * pct_unreported
            ult = latest + expected_unreported
            ultimates.append(ult)
            ibnr_list.append(expected_unreported)
        return {
            "method": "Bornhuetter–Ferguson",
            "a_priori_lr": self.a_priori_lr,
            "ultimates": ultimates,
            "ibnr": ibnr_list,
            "total_ibnr": sum(x for x in ibnr_list if x is not None),
            "total_ultimate": sum(x for x in ultimates if x is not None),
        }

    # ── 3.5  Frequency–Severity (Ch 4.6.5) ───────────────────────────────────

    def frequency_severity(
        self,
        count_triangle: Triangle,
        a_priori_severity: Optional[float] = None,
    ) -> Dict:
        """
        Separate development of claim counts and severity.
        ult_losses_i = ult_counts_i × ult_severity_i
        a_priori_severity: fallback if count data is thin.
        """
        count_model = ReservingModel(count_triangle, tail_factor=self.tail_factor)
        cl_counts = count_model.chain_ladder()

        # develop severity for each AY
        diag_losses = self.tri.last_diagonal()
        diag_counts = count_triangle.last_diagonal()

        ult_counts   = cl_counts["ultimates"]
        ultimates, ibnr_list = [], []

        for i in range(self.tri.n_rows()):
            dc = diag_counts[i]
            dl = diag_losses[i]
            uc = ult_counts[i]
            if dc is None or dc == 0 or uc is None:
                ultimates.append(None); ibnr_list.append(None); continue
            current_sev = dl / dc if dl is not None else (a_priori_severity or 0.0)
            ult_sev = a_priori_severity if a_priori_severity else current_sev
            ult = uc * ult_sev
            latest = dl if dl is not None else 0.0
            ultimates.append(ult)
            ibnr_list.append(ult - latest)

        return {
            "method": "Frequency–Severity",
            "ult_counts": ult_counts,
            "ultimates": ultimates,
            "ibnr": ibnr_list,
            "total_ibnr": sum(x for x in ibnr_list if x is not None),
            "total_ultimate": sum(x for x in ultimates if x is not None),
        }

    # ── 3.6  Comparison of methods ────────────────────────────────────────────

    def compare_methods(self, include_fs: bool = False,
                        count_triangle: Optional[Triangle] = None,
                        a_priori_severity: Optional[float] = None) -> Dict:
        results = {}
        results["Chain Ladder"] = self.chain_ladder()
        if self.tri.earned_premiums:
            results["ELR"]   = self.expected_loss_ratio()
            results["BF"]    = self.bornhuetter_ferguson()
        if include_fs and count_triangle:
            results["F*S"]   = self.frequency_severity(count_triangle, a_priori_severity)
        return results

    # ── 3.7  Report ───────────────────────────────────────────────────────────

    def report(self, include_fs: bool = False,
               count_triangle: Optional[Triangle] = None,
               a_priori_severity: Optional[float] = None) -> None:

        _banner(f"LOSS RESERVING - {self.tri.name}")

        # Print triangle
        _section("Loss Development Triangle (Cumulative Paid/Incurred)")
        ages_hdr = "  ".join(f"{a:>8}" for a in self.tri.dev_ages)
        print(f"  {'AY':<6}  {ages_hdr}")
        print("  " + "-" * (8 + 10 * self.tri.n_cols()))
        for i, ay in enumerate(self.tri.accident_years):
            row_vals = "  ".join(
                f"{_fmt(v,0):>8}" if v is not None else f"{'---':>8}"
                for v in self.tri.data[i]
            )
            print(f"  {ay:<6}  {row_vals}")

        # Age-to-age LDFs
        _section("Age-to-Age Development Factors (Volume-Weighted)")
        a2a = self.age_to_age_factors()
        cum = self.cumulative_ldfs()
        age_pairs = [f"{self.tri.dev_ages[i]}->{self.tri.dev_ages[i+1]}"
                     for i in range(len(self.tri.dev_ages) - 1)]
        print("  " + "  ".join(f"{p:>10}" for p in age_pairs) + f"  {'->Ult (tail)':>12}")
        print("  " + "  ".join(f"{_fmt(f,4):>10}" for f in a2a) + f"  {_fmt(self.tail_factor,4):>12}")
        print()
        print("  Cumulative LDFs to Ultimate:")
        for i, (age, cdf) in enumerate(zip(self.tri.dev_ages, cum)):
            print(f"    Age {age:>4}  ->  {_fmt(cdf,4)}")

        # Method results
        results = self.compare_methods(include_fs, count_triangle, a_priori_severity)

        _section("Reserve Estimates by Method")
        methods = list(results.keys())
        col_w = 16

        # Header
        hdr = f"  {'AY':<6}  " + "  ".join(f"{'IBNR '+m:>{col_w}}" for m in methods)
        print(hdr)
        print("  " + "-" * (8 + (col_w + 2) * len(methods)))

        # Per AY
        for i, ay in enumerate(self.tri.accident_years):
            row = f"  {ay:<6}  "
            for m in methods:
                ibnr = results[m]["ibnr"][i]
                row += f"{(_fmt(ibnr,0) if ibnr is not None else '---'):>{col_w}}  "
            print(row)

        # Totals
        print("  " + "-" * (8 + (col_w + 2) * len(methods)))
        tot_row = f"  {'TOTAL':<6}  "
        for m in methods:
            tot_row += f"{_fmt(results[m]['total_ibnr'],0):>{col_w}}  "
        print(tot_row)
        tot_ult = f"  {'ULT':<6}  "
        for m in methods:
            tot_ult += f"{_fmt(results[m]['total_ultimate'],0):>{col_w}}  "
        print(tot_ult)

        # Paid to date
        diag = self.tri.last_diagonal()
        paid_to_date = sum(v for v in diag if v is not None)
        print(f"\n  Paid / incurred to date : {_fmt(paid_to_date,0)}")
        print(f"  A priori loss ratio     : {_pct(self.a_priori_lr)}")
        print(f"  Tail factor             : {_fmt(self.tail_factor,4)}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. COVERAGE SPLIT MATRIX  (Ch 2.2, Ch 2.3 / 2.6 / 2.8)
# ─────────────────────────────────────────────────────────────────────────────

COVERAGE_MATRIX = {
    "Motor": {
        "Liability (BI/PD)": {
            "tail": "long",
            "reserving_methods": ["CL", "BF"],
            "exposure_unit": "car-years",
            "trend_area": "freq + sev separate",
        },
        "Medical (PIP)": {
            "tail": "medium",
            "reserving_methods": ["CL", "BF"],
            "exposure_unit": "car-years",
            "trend_area": "severity primary",
        },
        "UM / UIM": {
            "tail": "long",
            "reserving_methods": ["CL", "BF"],
            "exposure_unit": "car-years",
            "trend_area": "freq + sev separate",
        },
        "Collision / OTC": {
            "tail": "short",
            "reserving_methods": ["CL", "F*S"],
            "exposure_unit": "car-years",
            "trend_area": "severity primary",
        },
    },
    "General P&C": {
        "Property / Fire (Ch 2.3/2.6)": {
            "tail": "short",
            "reserving_methods": ["CL", "F*S"],
            "exposure_unit": "house-years / sum-insured",
            "trend_area": "severity + cat adjustment",
        },
        "Liability (Ch 2.8)": {
            "tail": "long",
            "reserving_methods": ["CL", "BF"],
            "exposure_unit": "policy count / payroll",
            "trend_area": "freq + sev separate + ILF",
        },
        "Theft / All Risks": {
            "tail": "short-medium",
            "reserving_methods": ["CL", "ELR"],
            "exposure_unit": "house-years",
            "trend_area": "severity primary",
        },
    },
}

def print_coverage_matrix() -> None:
    _banner("COVERAGE SPLIT MATRIX  (Brown & Gottlieb Ch 2)")
    for sector, coverages in COVERAGE_MATRIX.items():
        _section(sector)
        print(f"  {'Coverage':<32} {'Tail':<14} {'Methods':<22} {'Exposure Unit':<28} {'Trend'}")
        print("  " + "-" * 120)
        for cov, meta in coverages.items():
            methods = ", ".join(meta["reserving_methods"])
            print(f"  {cov:<32} {meta['tail']:<14} {methods:<22} {meta['exposure_unit']:<28} {meta['trend_area']}")


# ─────────────────────────────────────────────────────────────────────────────
# 5. SAMPLE DATA  (illustrative — replace with real data from OCR'd booklet)
# ─────────────────────────────────────────────────────────────────────────────

def build_motor_liability_data() -> Tuple[List[ExperienceData], Triangle]:
    """Motor — Bodily Injury Liability illustrative data."""
    exp_data = [
        ExperienceData(2020, 45_000, 3_600_000, 1_080, 2_430_000, 2_700_000),
        ExperienceData(2021, 47_200, 3_820_000, 1_132, 2_603_600, 2_848_000),
        ExperienceData(2022, 48_500, 3_960_000, 1_165, 2_682_500, 2_970_000),
        ExperienceData(2023, 50_100, 4_160_000, 1_202, 2_855_700, 3_120_000),
    ]
    # Incurred loss triangle (AY × Dev ages 12/24/36/48 months)
    triangle = Triangle(
        name="Motor - Bodily Injury Liability",
        accident_years=[2020, 2021, 2022, 2023],
        dev_ages=[12, 24, 36, 48],
        data=[
            [1_890_000, 2_380_000, 2_620_000, 2_700_000],
            [1_970_000, 2_490_000, 2_750_000,        None],
            [2_050_000, 2_570_000,        None,       None],
            [2_150_000,        None,       None,       None],
        ],
        earned_premiums=[3_600_000, 3_820_000, 3_960_000, 4_160_000],
    )
    return exp_data, triangle


def build_property_fire_data() -> Tuple[List[ExperienceData], Triangle]:
    """General P&C — Property/Fire illustrative data."""
    exp_data = [
        ExperienceData(2020, 12_000, 1_800_000, 540, 1_188_000, 1_260_000),
        ExperienceData(2021, 12_400, 1_870_000, 558, 1_235_300, 1_309_000),
        ExperienceData(2022, 12_800, 1_950_000, 576, 1_286_400, 1_365_000),
        ExperienceData(2023, 13_200, 2_040_000, 594, 1_340_800, 1_428_000),
    ]
    triangle = Triangle(
        name="General P&C - Property / Fire (Short-tail)",
        accident_years=[2020, 2021, 2022, 2023],
        dev_ages=[12, 24, 36, 48],
        data=[
            [1_120_000, 1_220_000, 1_248_000, 1_260_000],
            [1_158_000, 1_268_000, 1_299_000,        None],
            [1_200_000, 1_320_000,        None,       None],
            [1_242_000,        None,       None,       None],
        ],
        earned_premiums=[1_800_000, 1_870_000, 1_950_000, 2_040_000],
    )
    return exp_data, triangle


def build_liability_data() -> Tuple[List[ExperienceData], Triangle]:
    """General P&C — Liability (long-tail) illustrative data."""
    exp_data = [
        ExperienceData(2020, 8_000, 2_000_000, 240, 1_360_000, 1_500_000),
        ExperienceData(2021, 8_400, 2_120_000, 252, 1_449_000, 1_590_000),
        ExperienceData(2022, 8_800, 2_250_000, 264, 1_518_000, 1_687_500),
        ExperienceData(2023, 9_200, 2_390_000, 277, 1_593_000, 1_792_500),
    ]
    triangle = Triangle(
        name="General P&C - Liability (Long-tail)",
        accident_years=[2020, 2021, 2022, 2023],
        dev_ages=[12, 24, 36, 48],
        data=[
            [  900_000, 1_200_000, 1_400_000, 1_500_000],
            [  945_000, 1_260_000, 1_470_000,        None],
            [  990_000, 1_330_000,        None,       None],
            [1_040_000,        None,       None,       None],
        ],
        earned_premiums=[2_000_000, 2_120_000, 2_250_000, 2_390_000],
    )
    return exp_data, triangle


# ─────────────────────────────────────────────────────────────────────────────
# 6. MAIN  — run all modules
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print_coverage_matrix()

    # ── Motor: Ratemaking ──────────────────────────────────────────────────────
    motor_exp, motor_tri = build_motor_liability_data()

    motor_rm = RatemakingModel(
        name="Motor - Bodily Injury Liability",
        experience=motor_exp,
        expenses=ExpenseStructure(
            fixed_expense_per_unit=12.0,
            variable_expense_ratio=0.18,
            profit_contingency_load=0.05,
        ),
        credibility=CredibilityParams(full_credibility_claims=1082),
        freq_trend=-0.01,   # -1%/yr improvement in claim frequency
        sev_trend=0.07,     # +7%/yr severity inflation
        trend_period=2.5,
        current_rate=85.00,
    )
    motor_rm.report()

    # ── Motor: Reserving ──────────────────────────────────────────────────────
    motor_res = ReservingModel(motor_tri, a_priori_lr=0.72, tail_factor=1.050)
    motor_res.report()

    # ── Property/Fire: Ratemaking ─────────────────────────────────────────────
    prop_exp, prop_tri = build_property_fire_data()

    prop_rm = RatemakingModel(
        name="General P&C - Property / Fire",
        experience=prop_exp,
        expenses=ExpenseStructure(
            fixed_expense_per_unit=5.0,
            variable_expense_ratio=0.20,
            profit_contingency_load=0.05,
        ),
        credibility=CredibilityParams(full_credibility_claims=1082),
        freq_trend=0.00,
        sev_trend=0.06,
        trend_period=2.0,
        current_rate=155.00,
    )
    prop_rm.report()

    # ── Property/Fire: Reserving (short-tail — tail factor near 1) ────────────
    prop_res = ReservingModel(prop_tri, a_priori_lr=0.68, tail_factor=1.010)
    prop_res.report()

    # ── Liability: Ratemaking ─────────────────────────────────────────────────
    liab_exp, liab_tri = build_liability_data()

    liab_rm = RatemakingModel(
        name="General P&C - Liability (Long-tail)",
        experience=liab_exp,
        expenses=ExpenseStructure(
            fixed_expense_per_unit=8.0,
            variable_expense_ratio=0.22,
            profit_contingency_load=0.07,
        ),
        credibility=CredibilityParams(full_credibility_claims=1082),
        freq_trend=-0.02,
        sev_trend=0.08,
        trend_period=3.0,
        current_rate=265.00,
    )
    liab_rm.report()

    # ── Liability: Reserving (long-tail — higher tail factor) ─────────────────
    liab_res = ReservingModel(liab_tri, a_priori_lr=0.75, tail_factor=1.150)
    liab_res.report()

    _banner("END OF AIC ACTUARIAL MODEL OUTPUT")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1].lower() in ("verify", "--verify"):
        from model_verification import main as verify_main

        sys.exit(verify_main())
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("glm", "price"):
        from fremtpl_glm import main as glm_main

        sys.exit(glm_main(sys.argv[2:]))
    main()