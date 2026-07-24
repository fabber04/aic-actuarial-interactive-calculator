"""Representative CT Flex personas for actuarial-system benchmarking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str
    expected_behaviour: str
    transaction_count: int
    transactions: List[float]
    occupation: str = "Courier"
    platform: str = "Bolt"

    def aic_input(self) -> Dict[str, Any]:
        return {
            "occupation": self.occupation,
            "platform": self.platform,
            "transaction_count": self.transaction_count,
            "transactions": self.transactions,
            "ecocash_consent": True,
            "product": "income",
        }


def build_personas() -> List[Persona]:
    # Scenario 1 — New Worker (sparse, low exposure)
    new_worker = Persona(
        id="new_worker",
        name="New Worker",
        description="~2 weeks history, sparse jobs, low exposure.",
        expected_behaviour="Low credibility; lean on collective; conservative / Refer.",
        transaction_count=2,
        transactions=[8.0, 11.0],
        occupation="Courier",
    )

    # Scenario 2 — Established Driver (long, stable)
    established = Persona(
        id="established_driver",
        name="Established Driver",
        description="~18 months proxy via dense stable earnings, high exposure.",
        expected_behaviour="High credibility; pricing reflects individual experience.",
        transaction_count=80,
        transactions=[14.0 + (i % 4) * 0.25 for i in range(80)],
        occupation="Driver",
    )

    # Scenario 3 — Volatile Income (gaps + variance); n=20
    volatile = Persona(
        id="volatile_income",
        name="Volatile Income",
        description="Same volume as high-income-stable, but large gaps and variance.",
        expected_behaviour="Lower income stability; AKL should flag volatility.",
        transaction_count=20,
        transactions=[
            40.0,
            0.0,
            5.0,
            55.0,
            0.0,
            2.0,
            60.0,
            0.0,
            8.0,
            50.0,
            0.0,
            3.0,
            45.0,
            0.0,
            7.0,
            58.0,
            0.0,
            4.0,
            52.0,
            1.0,
        ],
        occupation="Courier",
    )

    # Scenario 4 — High Income but Stable; same n=20 as volatile
    # Proves: higher income ≠ automatically higher risk; reliability ≠ amount
    high_stable = Persona(
        id="high_income_stable",
        name="High Income Stable",
        description="Same transaction count as volatile persona; high, steady fares.",
        expected_behaviour="Higher stability than volatile; prototype (count-only) identical.",
        transaction_count=20,
        transactions=[28.0] * 20,
        occupation="Courier",
    )

    return [new_worker, established, volatile, high_stable]
