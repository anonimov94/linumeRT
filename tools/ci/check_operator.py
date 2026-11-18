"""Validate the complete automated G2 subset, including skipped tests.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "tests/suite_operator.txt"


def verify(report: Path, suite: Path = SUITE) -> None:
    expected = Counter(
        line.removesuffix("\n").replace(".py::", ".").replace("/", ".")
        for line in suite.read_text(encoding="utf-8").splitlines() if line.strip()
    )
    cases = list(ET.parse(report).iter("testcase"))
    observed = Counter(f"{case.get('classname')}.{case.get('name')}" for case in cases)
    if not expected or observed != expected:
        raise ValueError(f"Operator suite mismatch: expected={expected}, observed={observed}")
    for case in cases:
        if any(case.find(tag) is not None for tag in ("failure", "error", "skipped")):
            raise ValueError(f"Operator case did not pass: {case.get('name')}")


def main() -> int:
    try:
        verify(Path(sys.argv[1]))
    except (OSError, ValueError, ET.ParseError) as error:
        print(f"Operator automation FAIL: {error}", file=sys.stderr)
        return 1
    print("Operator automation PASS. Full G2 acceptance is recorded in docs/raporty/G2.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

