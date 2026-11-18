"""Regression for false operator acceptance after skipped or missing tests.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import importlib.util
from pathlib import Path

import pytest

CHECKER = Path(__file__).resolve().parents[1] / "tools/ci/check_operator.py"
spec = importlib.util.spec_from_file_location("check_operator", CHECKER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.mark.parametrize("contents", [
    '<testcase classname="tests.test_example" name="test_operator"/>',
    '<testcase classname="tests.test_example" name="test_operator"><skipped/></testcase>',
    '<testcase classname="tests.test_example" name="test_operator"><failure/></testcase>',
    '<testcase classname="tests.test_example" name="test_operator"><error/></testcase>',
    "",
    '<testcase classname="tests.test_other" name="test_operator"/>',
    ('<testcase classname="tests.test_example" name="test_operator"/>'
     '<testcase classname="tests.test_example" name="test_operator"/>'),
])
def test_operator_acceptance_requires_every_selected_case(tmp_path, contents):
    suite = tmp_path / "suite.txt"
    suite.write_text("tests/test_example.py::test_operator\n", encoding="utf-8")
    report = tmp_path / "report.xml"
    report.write_text(f"<testsuites><testsuite>{contents}</testsuite></testsuites>",
                      encoding="utf-8")
    if contents == '<testcase classname="tests.test_example" name="test_operator"/>':
        module.verify(report, suite)
    else:
        with pytest.raises(ValueError):
            module.verify(report, suite)

