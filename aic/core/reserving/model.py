"""
Loss reserving methods (Brown & Gottlieb Ch 4).

Chain-Ladder, Expected Loss Ratio, Bornhuetter–Ferguson, Frequency–Severity
live on one model class so shared LDF / triangle state stays consistent.
Further file splits (chain_ladder.py / bornhuetter.py) can extract methods later.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from aic.core.reserving._display import banner, fmt, section
from aic.core.reserving.triangle import Triangle


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
    ) -> None:
        self.tri = triangle
        self.a_priori_lr = a_priori_lr
        self.tail_factor = tail_factor

    # ── Age-to-age factors (Ch 4.6.3) ─────────────────────────────────────────

    def age_to_age_factors(self) -> List[float]:
        """
        Volume-weighted LDFs for each consecutive age pair.
        Uses only cells where both the current and next age are known (upper-left).
        """
        ldfs: List[float] = []
        for c in range(self.tri.n_cols() - 1):
            num = den = 0.0
            for r in range(self.tri.n_rows()):
                curr = self.tri.data[r][c]
                nxt = self.tri.data[r][c + 1]
                if curr is not None and nxt is not None:
                    den += curr
                    num += nxt
            ldfs.append(num / den if den else 1.0)
        return ldfs

    def cumulative_ldfs(self) -> List[float]:
        """
        CDF to ultimate for each development age (incl. tail factor).
        """
        a2a = self.age_to_age_factors()
        a2a_with_tail = a2a + [self.tail_factor]
        n = len(a2a_with_tail)
        cum = [1.0] * n
        cum[-1] = a2a_with_tail[-1]
        for i in range(n - 2, -1, -1):
            cum[i] = cum[i + 1] * a2a_with_tail[i]
        return cum

    def _current_age_index(self, ay_index: int) -> int:
        """Index of latest known column for this accident-year row."""
        row = self.tri.data[ay_index]
        for c in range(len(row) - 1, -1, -1):
            if row[c] is not None:
                return c
        return 0

    # ── Chain-Ladder (Ch 4.6.3) ───────────────────────────────────────────────

    def chain_ladder(self) -> Dict:
        """
        Project each AY to ultimate using its age-specific CDF.
        Returns dict with 'ultimates', 'ibnr', 'ldfs'.
        """
        cum_ldfs = self.cumulative_ldfs()
        ultimates: List[Optional[float]] = []
        ibnr_list: List[Optional[float]] = []
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

    # ── Expected Loss Ratio (Ch 4.6.2) ───────────────────────────────────────

    def expected_loss_ratio(self) -> Dict:
        """
        ELR method: ultimate = ELR × earned premium.
        Requires earned_premiums on the triangle.
        """
        if self.tri.earned_premiums is None:
            raise ValueError("ELR method requires earned_premiums on Triangle.")
        ultimates: List[float] = []
        ibnr_list: List[float] = []
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

    # ── Bornhuetter–Ferguson (Ch 4.6.4) ──────────────────────────────────────

    def bornhuetter_ferguson(self) -> Dict:
        """
        BF ultimate = Actual paid + % unreported × ELR × premium
        % unreported for age i = 1 - 1/CDF_i
        """
        if self.tri.earned_premiums is None:
            raise ValueError("BF method requires earned_premiums on Triangle.")
        cum_ldfs = self.cumulative_ldfs()
        ultimates: List[Optional[float]] = []
        ibnr_list: List[Optional[float]] = []
        for i, prem in enumerate(self.tri.earned_premiums):
            ci = self._current_age_index(i)
            latest = self.tri.data[i][ci]
            if latest is None:
                ultimates.append(None)
                ibnr_list.append(None)
                continue
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

    # ── Frequency–Severity (Ch 4.6.5) ────────────────────────────────────────

    def frequency_severity(
        self,
        count_triangle: Triangle,
        a_priori_severity: Optional[float] = None,
    ) -> Dict:
        """
        Separate development of claim counts and severity.
        ult_losses_i = ult_counts_i × ult_severity_i
        """
        count_model = ReservingModel(count_triangle, tail_factor=self.tail_factor)
        cl_counts = count_model.chain_ladder()

        diag_losses = self.tri.last_diagonal()
        diag_counts = count_triangle.last_diagonal()

        ult_counts = cl_counts["ultimates"]
        ultimates: List[Optional[float]] = []
        ibnr_list: List[Optional[float]] = []

        for i in range(self.tri.n_rows()):
            dc = diag_counts[i]
            dl = diag_losses[i]
            uc = ult_counts[i]
            if dc is None or dc == 0 or uc is None:
                ultimates.append(None)
                ibnr_list.append(None)
                continue
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

    # ── Comparison / report ───────────────────────────────────────────────────

    def compare_methods(
        self,
        include_fs: bool = False,
        count_triangle: Optional[Triangle] = None,
        a_priori_severity: Optional[float] = None,
    ) -> Dict:
        results: Dict = {}
        results["Chain Ladder"] = self.chain_ladder()
        if self.tri.earned_premiums:
            results["ELR"] = self.expected_loss_ratio()
            results["BF"] = self.bornhuetter_ferguson()
        if include_fs and count_triangle:
            results["F*S"] = self.frequency_severity(count_triangle, a_priori_severity)
        return results

    def report(
        self,
        include_fs: bool = False,
        count_triangle: Optional[Triangle] = None,
        a_priori_severity: Optional[float] = None,
    ) -> None:
        banner(f"LOSS RESERVING - {self.tri.name}")

        section("Loss Development Triangle (Cumulative Paid/Incurred)")
        ages_hdr = "  ".join(f"{a:>8}" for a in self.tri.dev_ages)
        print(f"  {'AY':<6}  {ages_hdr}")
        print("  " + "-" * (8 + 10 * self.tri.n_cols()))
        for i, ay in enumerate(self.tri.accident_years):
            row_vals = "  ".join(
                f"{fmt(v, 0):>8}" if v is not None else f"{'---':>8}"
                for v in self.tri.data[i]
            )
            print(f"  {ay:<6}  {row_vals}")

        section("Age-to-Age Development Factors (Volume-Weighted)")
        a2a = self.age_to_age_factors()
        cum = self.cumulative_ldfs()
        age_pairs = [
            f"{self.tri.dev_ages[i]}->{self.tri.dev_ages[i + 1]}"
            for i in range(len(self.tri.dev_ages) - 1)
        ]
        print(
            "  "
            + "  ".join(f"{p:>10}" for p in age_pairs)
            + f"  {'->Ult (tail)':>12}"
        )
        print(
            "  "
            + "  ".join(f"{fmt(f, 4):>10}" for f in a2a)
            + f"  {fmt(self.tail_factor, 4):>12}"
        )
        print()
        print("  Cumulative LDFs to Ultimate:")
        for age, cdf in zip(self.tri.dev_ages, cum):
            print(f"    Age {age:>4}  ->  {fmt(cdf, 4)}")

        results = self.compare_methods(include_fs, count_triangle, a_priori_severity)

        section("Reserve Estimates by Method")
        methods = list(results.keys())
        col_w = 16

        hdr = f"  {'AY':<6}  " + "  ".join(f"{'IBNR ' + m:>{col_w}}" for m in methods)
        print(hdr)
        print("  " + "-" * (8 + (col_w + 2) * len(methods)))

        for i, ay in enumerate(self.tri.accident_years):
            row = f"  {ay:<6}  "
            for m in methods:
                ibnr = results[m]["ibnr"][i]
                row += f"{(fmt(ibnr, 0) if ibnr is not None else '---'):>{col_w}}  "
            print(row)

        print("  " + "-" * (8 + (col_w + 2) * len(methods)))
        tot_row = f"  {'TOTAL':<6}  "
        for m in methods:
            tot_row += f"{fmt(results[m]['total_ibnr'], 0):>{col_w}}  "
        print(tot_row)
        tot_ult = f"  {'ULT':<6}  "
        for m in methods:
            tot_ult += f"{fmt(results[m]['total_ultimate'], 0):>{col_w}}  "
        print(tot_ult)

        diag = self.tri.last_diagonal()
        paid_to_date = sum(v for v in diag if v is not None)
        print(f"\n  Paid / incurred to date : {fmt(paid_to_date, 0)}")
        print(f"  A priori loss ratio     : {self.a_priori_lr * 100:.2f}%")
        print(f"  Tail factor             : {fmt(self.tail_factor, 4)}")
