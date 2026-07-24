from __future__ import annotations

from typing import Any, Dict, List

from aic.contracts.data_objects import StandardizedData
from aic.products.base import ProductAdapter


class CTFlexAdapter(ProductAdapter):
    """
    CT Flex Income (Phase 1) adapter.

    Hides EcoCash / Bolt / InDrive specifics from the actuarial core.
    Occupation hazard scores live in ``aic.features.occupational.OccupationRiskTable``.
    """

    def transform(self, raw_input: Dict[str, Any]) -> StandardizedData:
        txns = raw_input.get("transactions") or []
        observations: List[Dict[str, Any]] = []
        for t in txns:
            if isinstance(t, (int, float)):
                observations.append({"income": float(t)})
            elif isinstance(t, dict):
                amount = t.get("amount", t.get("income", 0))
                observations.append(
                    {
                        "income": float(amount or 0),
                        "date": t.get("date"),
                    }
                )

        # Also accept transaction_count-only demos (CT Flex MVP style)
        if not observations and "transaction_count" in raw_input:
            n = int(raw_input["transaction_count"])
            base = float(raw_input.get("fare_hint", 15.0))
            observations = [{"income": base} for _ in range(max(n, 0))]

        return StandardizedData(
            product=str(raw_input.get("product", "ctflex_income")),
            observations=observations,
            context={
                "occupation": raw_input.get("occupation", "Courier"),
                "platform": raw_input.get("platform", "Bolt"),
                "transaction_count": raw_input.get(
                    "transaction_count", len(observations)
                ),
                "area": raw_input.get("area") or raw_input.get("city"),
                "corridor": raw_input.get("corridor"),
            },
        )
