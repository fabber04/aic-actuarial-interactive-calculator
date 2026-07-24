"""
Run the AIC Research Validation suite.

  python -m aic.validation
  python -m aic.validation --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from aic.validation.suite import run_validation_suite


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AIC Research Validation Suite")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    ns = parser.parse_args(argv)
    report = run_validation_suite()

    if ns.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(f"AIC Research Validation  v{report.version}")
        print(f"generated_at: {report.generated_at}")
        print("-" * 60)
        for layer in report.layers:
            mark = "PASS" if layer.passed else "FAIL"
            print(f"[{mark}] {layer.layer}  ({len(layer.checks)} checks)")
            for check in layer.checks:
                cmark = "ok" if check.passed else "X "
                print(f"   {cmark}  {check.name}: {check.detail}")
            if layer.notes:
                print(f"   note: {layer.notes}")
        print("-" * 60)
        print("OVERALL:", "PASS" if report.passed else "FAIL")

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
