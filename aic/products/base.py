from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from aic.contracts.data_objects import StandardizedData


class ProductAdapter(ABC):
    """Convert product-specific raw data into StandardizedData."""

    @abstractmethod
    def transform(self, raw_input: Dict[str, Any]) -> StandardizedData:
        ...
