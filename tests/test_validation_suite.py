"""Tests for the AIC Research Validation suite."""

from __future__ import annotations

import unittest

from aic.validation import run_validation_suite


class TestResearchValidationSuite(unittest.TestCase):
    def test_suite_passes(self) -> None:
        report = run_validation_suite()
        failed = [
            f"{layer.layer}:{check.name}"
            for layer in report.layers
            for check in layer.checks
            if not check.passed
        ]
        self.assertTrue(report.passed, msg=f"Failed checks: {failed}")
        self.assertGreaterEqual(len(report.layers), 5)


if __name__ == "__main__":
    unittest.main()
