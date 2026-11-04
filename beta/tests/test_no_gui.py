"""Wymaganie podstawowe projektu beta: aplikacja bez GUI.

SPDX-License-Identifier: GPL-2.0-or-later

Te testy pilnują decyzji właściciela: w beta nie ma Qt, OpenGL, ekranu QtVCP ani panelu
web. Sprawdzamy i źródła (strażnik ``tools/check_no_gui.py``), i zachowanie w czasie
wykonania (żaden moduł graficzny nie jest importowany, ``system.info`` zgłasza gui=False).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BETA = Path(__file__).resolve().parent.parent


def test_straznik_bez_gui_przechodzi() -> None:
    result = subprocess.run([sys.executable, str(BETA / "tools" / "check_no_gui.py")],
                            capture_output=True, text=True, cwd=BETA)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: brak Qt, OpenGL" in result.stdout


def test_zaden_modul_graficzny_nie_jest_zaladowany(app) -> None:
    """Po złożeniu całej aplikacji w ``sys.modules`` nie ma Qt/OpenGL/webhmi."""
    forbidden = ("PyQt5", "PyQt6", "PySide2", "PySide6", "qtvcp", "OpenGL",
                 "pyqtgraph", "qtpy", "linumert_webhmi")
    loaded = [name for name in sys.modules
              if name.split(".")[0] in forbidden or name == "linumert_webhmi"]
    assert loaded == [], f"wczytano moduły graficzne: {loaded}"


def test_system_info_zglasza_brak_gui_i_opengl(call) -> None:
    info = call("system.info")
    assert info["gui"] is False
    assert info["opengl"] is False
    assert "bez GUI" in info["notes"]


def test_brak_plikow_ekranu_w_beta() -> None:
    for pattern in ("*.ui", "*.qss", "*.qrc", "render_view.py"):
        found = [p for p in BETA.rglob(pattern) if ".git" not in p.parts]
        assert found == [], f"zostały pliki ekranu {pattern}: {found}"


def test_brak_panelu_web_plant() -> None:
    panel = BETA / "src" / "linumert_plant" / "panel"
    assert not (panel / "app.py").exists(), "panel web Plant powinien być usunięty"
    assert not (panel / "static").exists(), "statyczne pliki panelu powinny być usunięte"

    from linumert_plant.panel import PanelUnavailable, load_app_module

    try:
        load_app_module()
    except PanelUnavailable as exc:
        assert "headless" in str(exc)
    else:  # pragma: no cover - panel nie istnieje
        raise AssertionError("load_app_module() powinien zgłosić PanelUnavailable")
