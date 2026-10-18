"""Narzędzie pokrycia wymagań tools/check_requirements.py (sesja 024).

Model-Author: Claude
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_requirements  # noqa: E402


def _repo(tmp_path: Path, *, done: str, test: str, scenario: str = "",
          status: str = "planowane") -> Path:
    (tmp_path / "docs" / "wymagania").mkdir(parents=True)
    (tmp_path / "prompts").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "plant" / "scenarios").mkdir(parents=True)
    (tmp_path / "docs" / "wymagania" / "A.md").write_text(
        "| ID | Wymaganie | Sesja | Test |\n|---|---|---|---|\n"
        "| REQ-QA-01 | narzędzie | 024 | t |\n| REQ-VD-06 | sprzęt | 061 | t |\n",
        encoding="utf-8")
    (tmp_path / "docs" / "wymagania" / "MACIERZ.md").write_text(
        "| REQ | Sesja | Test | Status |\n|---|---|---|---|\n"
        f"| REQ-QA-01 | 024 | t | {status} |\n| REQ-VD-06 | 061 | t | planowane |\n",
        encoding="utf-8")
    (tmp_path / "prompts" / "DONE.md").write_text(f"# x\n\n{done}\n", encoding="utf-8")
    (tmp_path / "tests" / "test_x.py").write_text(test, encoding="utf-8")
    if scenario:
        (tmp_path / "plant" / "scenarios" / "s.yaml").write_text(scenario, encoding="utf-8")
    return tmp_path


def test_repository_requirements_are_covered() -> None:  # REQ-QA-01
    errors, _warnings, lines = check_requirements.check(ROOT)
    assert errors == []
    assert len(lines) >= 22  # wszystkie REQ z docs/wymagania


def test_missing_coverage_of_done_session_is_error(tmp_path) -> None:  # REQ-QA-01
    root = _repo(tmp_path, done="024 | 2026-10-18 | x", test="def test_a():\n    pass\n")
    errors, _w, _l = check_requirements.check(root)
    assert len(errors) == 1 and "REQ-QA-01" in errors[0] and "wykonane" in errors[0]
    assert check_requirements.main(["--root", str(root)]) == 1


def test_future_session_is_only_planned(tmp_path) -> None:  # REQ-QA-01
    root = _repo(tmp_path, done="023 | 2026-10-18 | x", test="def test_a():\n    pass\n")
    assert check_requirements.check(root)[0] == []


def test_markers_and_scenarios_and_write(tmp_path) -> None:  # REQ-QA-01
    root = _repo(tmp_path, done="024 | 2026-10-18 | x",
                 test="def test_a():  # REQ-QA-01\n    pass\n",
                 scenario="name: s\nrequirements: [REQ-VD-06]\n")
    errors, warnings, _l = check_requirements.check(root)
    assert errors == [] and any("zaimplementowane" in w for w in warnings)
    assert check_requirements.main(["--root", str(root), "--write"]) == 0
    text = (root / "docs" / "wymagania" / "MACIERZ.md").read_text(encoding="utf-8")
    assert "| REQ-QA-01 | 024 | t | zaimplementowane |" in text
    assert "| REQ-VD-06 | 061 | t | planowane |" in text  # scenariusz, ale sesja przyszła
    assert check_requirements.check(root)[1] == []


def test_unknown_marker_is_error(tmp_path) -> None:  # REQ-QA-01
    bad = "REQ-" + "ZZ-99"  # składany, żeby nie był znacznikiem w tym pliku
    root = _repo(tmp_path, done="", test=f"def test_a():  # REQ-QA-01, {bad}\n    pass\n")
    errors = check_requirements.check(root)[0]
    assert any(bad in e and "nie ma takiego wymagania" in e for e in errors)
