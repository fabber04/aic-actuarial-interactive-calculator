"""
AIC Pricing Framework — contracts.

Separates expected loss from technical / indicated commercial premium.
Product payment mechanics (PAYG, annual bill) stay in the Decision Engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from aic.contracts.risk_result import RiskResult


@dataclass
class PricingAssumptions:
    """Portfolio / line actuarial pricing assumptions (not product UX rules)."""

    expense_ratio: float = 0.12  # variable expense as fraction of premium
    fixed_expense: float = 0.0  # monetary fixed expense in same units as expected loss
    profit_load: float = 0.05
    risk_margin: float = 0.03
    tax_fee_ratio: float = 0.0
    discount_ratio: float = 0.0  # post-technical commercial discount
    min_premium: float = 0.0
    portfolio: str = ""
    currency: str = "USD"


@dataclass
class PricingResult:
    """
    Actuarial pricing output.

    ``technical_premium`` = loaded rate before commercial discounts.
    ``commercial_premium`` = indicated commercial after discounts / floors
    (still not product packaging — Decision Engine applies PAYG etc.).
    """

    expected_loss: float
    pure_premium: float
    expense_loading: float
    profit_loading: float
    risk_margin_amount: float
    taxes_fees: float
    technical_premium: float
    discount_amount: float
    commercial_premium: float
    components: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PricingEngine(ABC):
    """Expected loss → technical / indicated commercial premium."""

    method_name: str = "pricing"
    method_version: str = "1.0"

    @abstractmethod
    def price(
        self,
        risk: RiskResult,
        assumptions: PricingAssumptions,
    ) -> PricingResult:
        ...
