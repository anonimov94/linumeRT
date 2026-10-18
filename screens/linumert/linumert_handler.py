# SPDX-License-Identifier: GPL-2.0-or-later
"""Handler ekranu linumeRT (QtVCP): wzorzec patch na kopii handlera QtDragon.

Model-Author: Claude · sesja 005.

`linumert_upstream_handler.py` to niezmieniona kopia `qtdragon_handler.py` z LinuxCNC 2.9.10
(GPL-2, UPSTREAM.md). Własne zmiany linumeRT żyją wyłącznie tutaj, w klasie pochodnej, więc
aktualizacja upstream = podmiana kopii i diff (procedura w UPSTREAM.md).
"""

import importlib.util
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_upstream():
    path = os.path.join(_HERE, "linumert_upstream_handler.py")
    spec = importlib.util.spec_from_file_location("linumert_upstream_handler", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_upstream = _load_upstream()


class HandlerClass(_upstream.HandlerClass):
    """Ekran linumeRT. Na razie zachowanie QtDragon bez zmian, poza tytułem okna."""

    def initialized__(self):
        super().initialized__()
        self.w.setWindowTitle("linumeRT")


def get_handlers(halcomp, widgets, paths):
    return [HandlerClass(halcomp, widgets, paths)]
