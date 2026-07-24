"""Development triangle data structure (Brown & Gottlieb Ch 4.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


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
    dev_ages: List[int]  # e.g. [12, 24, 36, 48]
    data: List[List[Optional[float]]]  # cumulative losses
    earned_premiums: Optional[List[float]] = None  # per AY — for BF/ELR

    def __post_init__(self) -> None:
        assert len(self.data) == len(self.accident_years)
        for row in self.data:
            assert len(row) == len(self.dev_ages)

    def n_rows(self) -> int:
        return len(self.accident_years)

    def n_cols(self) -> int:
        return len(self.dev_ages)

    def last_diagonal(self) -> List[Optional[float]]:
        """Latest known value for each accident year."""
        diag: List[Optional[float]] = []
        for row in self.data:
            val = None
            for v in reversed(row):
                if v is not None:
                    val = v
                    break
            diag.append(val)
        return diag

    def col_data(self, col: int) -> List[Optional[float]]:
        return [self.data[r][col] for r in range(self.n_rows())]
