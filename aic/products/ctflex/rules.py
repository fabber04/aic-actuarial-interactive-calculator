"""CT Flex Income product rules — commercial / cover, not GLM."""

from __future__ import annotations

from dataclasses import dataclass

# Phase-1 Income (aligned with CT Flex executive summary / demo)
CLASS_RATE_INCOME = 0.0263
EXPENSE_LOAD = 0.12
PROFIT_LOAD = 0.05
REPLACEMENT_RATIO = 0.60
BENEFIT_WEEKLY_CAP = 150.0
MIN_PREMIUM_RATE = 0.015
Z_REFER_THRESHOLD = 0.12
GRACE_DAYS = 7


@dataclass
class CTFlexRules:
    class_rate: float = CLASS_RATE_INCOME
    expense_load: float = EXPENSE_LOAD
    profit_load: float = PROFIT_LOAD
    replacement_ratio: float = REPLACEMENT_RATIO
    benefit_weekly_cap: float = BENEFIT_WEEKLY_CAP
    min_premium_rate: float = MIN_PREMIUM_RATE
    z_refer_threshold: float = Z_REFER_THRESHOLD
    grace_days: int = GRACE_DAYS
