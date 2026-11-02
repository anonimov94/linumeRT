"""Punkty wejścia: każdy skrypt z ``[project.scripts]`` musi dać się uruchomić.

SPDX-License-Identifier: GPL-2.0-or-later

``pip install`` NIE wykrywa błędnego punktu wejścia — wpis ``moduł:funkcja`` jest
sprawdzany dopiero przy pierwszym uruchomieniu skryptu. Ten test czyta deklaracje
z ``pyproject.toml`` i importuje wskazaną funkcję, więc martwy wpis pada od razu,
a nie u użytkownika po instalacji.
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

BETA = Path(__file__).resolve().parent.parent
PYPROJECT = BETA / "pyproject.toml"


def scripts() -> dict[str, str]:
    """Deklaracje ``[project.scripts]``: nazwa skryptu → ``moduł:funkcja``."""
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return dict(payload["project"]["scripts"])


def test_pyproject_deklaruje_skrypty() -> None:
    declared = scripts()
    assert declared, "brak [project.scripts] w pyproject.toml"
    # Te trzy są osią interfejsu — ich zniknięcie byłoby regresją API.
    assert {"linumertd", "linumertctl", "linumert-plant"} <= set(declared)


@pytest.mark.parametrize("name", sorted(scripts()))
def test_kazdy_skrypt_wskazuje_istniejaca_funkcje(name: str) -> None:
    target = scripts()[name]
    module_name, _, function_name = target.partition(":")
    assert function_name, f"{name}: wpis {target!r} bez ':funkcja'"

    module = importlib.import_module(module_name)
    function = getattr(module, function_name, None)
    assert callable(function), f"{name}: {module_name}.{function_name} nie jest wywoływalna"


def test_nie_ma_martwych_wpisow_po_usunieciu_gui() -> None:
    """Skrypty nie mogą wskazywać modułów usuniętych razem z GUI."""
    forbidden = ("webhmi", "panel.app", "render_view", "screens")
    for name, target in scripts().items():
        module_name = target.partition(":")[0]
        for word in forbidden:
            assert word not in module_name, f"{name} wskazuje usunięty moduł: {module_name}"


def test_kompilacja_programu_jest_operacja_kontraktu_nie_skryptem() -> None:
    """Kompilacja .lnx → G-code idzie przez kontrakt, nie osobnym skryptem.

    Jedno źródło prawdy: ta sama operacja działa przez REST, WebSocket, SDK i CLI.
    Osobny skrypt byłby drugą ścieżką walidacji do utrzymania.
    """
    assert not any(n.startswith("linumert-compile") for n in scripts())
