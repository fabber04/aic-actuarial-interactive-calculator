"""
Thin predictor facade over ``aic.fremtpl_glm.LivePricingEngine``.

Keeps joblib load / hot-swap implementation in fremtpl_glm while giving
``core.risk_engine`` a stable call surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from aic.fremtpl_glm import (
    DEFAULT_MODEL_DIR,
    DEFAULT_STORE_PATH,
    FREMTPL_PROFILE,
    LivePricingEngine,
    PricingProfile,
    load_model_bundle,
)


class GlmPredictor:
    """Predict positive prices / pure-premium proxies from a live or loaded GLM."""

    def __init__(
        self,
        engine: Optional[LivePricingEngine] = None,
        *,
        store_path: Union[str, Path] = DEFAULT_STORE_PATH,
        model_dir: Union[str, Path] = DEFAULT_MODEL_DIR,
        profile: PricingProfile = FREMTPL_PROFILE,
    ) -> None:
        self.engine = engine or LivePricingEngine(
            store_path=store_path,
            model_dir=model_dir,
            profile=profile,
        )

    @property
    def has_model(self) -> bool:
        return self.engine.has_model()

    @property
    def version_id(self) -> Optional[str]:
        return self.engine.metrics.active_version_id

    def load_version(self, path: Union[str, Path]) -> None:
        """Hot-load a specific joblib bundle into the engine."""
        bundle = load_model_bundle(path)
        with self.engine._lock:
            self.engine._bundle = bundle
            self.engine.metrics.active_version_id = bundle.version_id

    def predict_records(
        self,
        records: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
    ) -> np.ndarray:
        if not self.has_model:
            raise RuntimeError(
                "No GLM loaded — train/deploy via fremtpl_glm CLI or pass a LivePricingEngine with a model"
            )
        return self.engine.predict(records)

    def predict_price(
        self,
        records: Union[pd.DataFrame, Dict[str, Any], List[Dict[str, Any]]],
    ) -> List[float]:
        return self.engine.predict_price(records)
