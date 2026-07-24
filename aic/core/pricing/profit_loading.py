"""Profit / contingency loading helpers."""

from __future__ import annotations


def profit_loading_amount(premium: float, profit_load: float) -> float:
    return max(0.0, float(premium) * max(0.0, float(profit_load)))
