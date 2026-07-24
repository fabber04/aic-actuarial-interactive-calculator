"""Assemble and run all layer validators."""

from __future__ import annotations

from typing import List

from aic.validation.akl import validate_akl
from aic.validation.credibility import validate_credibility
from aic.validation.decision import validate_decision_and_explainability
from aic.validation.pricing import validate_pricing
from aic.validation.risk import validate_risk_engine
from aic.validation.types import LayerReport, ValidationSuiteReport


def run_validation_suite() -> ValidationSuiteReport:
    layers: List[LayerReport] = [
        validate_akl(),
        validate_credibility(),
        validate_risk_engine(),
        validate_pricing(),
        validate_decision_and_explainability(),
    ]
    return ValidationSuiteReport(layers=layers)
