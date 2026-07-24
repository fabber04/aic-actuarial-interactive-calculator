"""Helpers to extract observation series from StandardizedData — no pricing logic."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence


def income_amounts(observations: Sequence[Dict[str, Any]]) -> List[float]:
    """Extract income / amount observations as a float series."""
    out: List[float] = []
    for o in observations:
        if "income" in o:
            out.append(float(o.get("income") or 0.0))
        elif "amount" in o:
            out.append(float(o.get("amount") or 0.0))
    return out


def observation_dates(observations: Sequence[Dict[str, Any]]) -> List[Optional[str]]:
    return [o.get("date") if isinstance(o.get("date"), str) else None for o in observations]


def context_float(context: Dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(context.get(key, default) or default)
    except (TypeError, ValueError):
        return default
