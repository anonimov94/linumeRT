"""Model-Author: Codex. Failure reporting of the shared test runner."""

import importlib.util
import json
import sys

from conftest import REPO

spec = importlib.util.spec_from_file_location("agent_runner", REPO / "tools/agent_tests/run.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def test_failure_does_not_hide_later_results(tmp_path):
    report_dir = tmp_path / "report"
    code = runner.run_checks(tmp_path, "Codex", report_dir, [
        ("failing", [sys.executable, "-c", "print('failed check'); raise SystemExit(3)"]),
        ("passing", [sys.executable, "-c", "print('later check')"]),
    ])
    report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    assert code == 1
    assert report["passed"] is False
    assert [check["exit_code"] for check in report["checks"]] == [3, 0]
    assert "later check" in (report_dir / "passing.log").read_text(encoding="utf-8")


def test_missing_executable_is_failure(tmp_path):
    report_dir = tmp_path / "report"
    code = runner.run_checks(tmp_path, "Claude", report_dir, [
        ("missing", [str(tmp_path / "does-not-exist")]),
    ])
    report = json.loads((report_dir / "report.json").read_text(encoding="utf-8"))
    assert code == 1
    assert report["model"] == "Claude"
    assert report["checks"][0]["exit_code"] == 127
