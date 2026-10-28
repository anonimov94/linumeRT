"""Architecture contracts, including imports hidden inside functions.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_IMPORTS = {"PyQt5", "PySide2", "PySide6", "qtpy", "qtvcp", "pyqtgraph",
              "fastapi", "uvicorn", "websockets", "linumert_webhmi"}


def test_backend_dependency_boundaries():
    violations = []
    for directory, forbidden in (("core/linumert", {"linumert_plant", "linumert_sim"}),
                                  ("plant/server/linumert_plant", {"linumert_sim"}),
                                  ("simulation/linumert_sim", {"linumert_plant"})):
        for path in (ROOT / directory).rglob("*.py"):
            blocked = UI_IMPORTS | forbidden
            if path == ROOT / "core/linumert/cli.py":
                blocked = UI_IMPORTS  # composition root may invoke either independent service
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imports = []
                if isinstance(node, ast.Import):
                    imports = [x.name for x in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    imports = [node.module or ""]
                for name in imports:
                    if name.split(".")[0] in blocked:
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}: {name}")
    assert not violations, "\n".join(violations)


def test_no_frontend_trees_or_dependencies():
    for directory in ("screens", "webhmi", "plant/server/linumert_plant/panel"):
        assert not any(p.is_file() for p in (ROOT / directory).rglob("*")), directory
    import tomllib

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["project"]["name"] == "linumert-lite"
    dependencies = config["project"]["dependencies"]
    assert not any(name in " ".join(dependencies).lower()
                   for name in ("fastapi", "qt", "uvicorn", "websockets"))
