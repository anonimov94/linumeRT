"""Wspólne fikstury testów aplikacji headless i przejętego rdzenia.

SPDX-License-Identifier: GPL-2.0-or-later

Testy działają bez LinuxCNC, bez Qt i bez serwera X: backend to atrapa z zegarem
sterowanym ręcznie (``autostart=False``), więc przebiegi są deterministyczne — ruch
postępuje tylko wtedy, gdy test przesunie zegar przez ``clock``.

Katalogi konfiguracyjne są kopiowane do katalogu tymczasowego, żeby testy nie pisały
do ``state/`` ani do bazy narzędzi projektu.

W tym samym katalogu leżą testy przejętego rdzenia (``linumert``, ``linumert_sim``,
``linumert_plant``) — liczą one ścieżki względem ``parents[1]``, czyli ``beta/``,
dokładnie tak jak w głównym repozytorium względem jego korzenia.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

BETA = Path(__file__).resolve().parent.parent
# Przejęte testy rdzenia liczą ścieżki względem korzenia projektu (``from conftest
# import REPO``) — w bliźniaku tym korzeniem jest ``beta/``.
REPO = BETA
SRC = BETA / "src"
TESTS = Path(__file__).resolve().parent
for path in (str(SRC), str(TESTS)):
    if path not in sys.path:
        sys.path.insert(0, path)

# Przejęte testy rdzenia uruchamiają procesy potomne (``python -m linumert...``).
# Bliźniak nie jest instalowany w site-packages, więc PYTHONPATH musi dziedziczyć src/.
_existing = os.environ.get("PYTHONPATH", "")
if str(SRC) not in _existing.split(os.pathsep):
    os.environ["PYTHONPATH"] = str(SRC) + (os.pathsep + _existing if _existing else "")

from linumert_headless.app import build_application  # noqa: E402
from linumert_headless.config import AppConfig  # noqa: E402


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Kopia config/library/scenarios w katalogu tymczasowym (izolacja zapisu)."""
    root = tmp_path / "beta"
    for name in ("config", "library", "scenarios"):
        source = BETA / name
        if source.exists():
            shutil.copytree(source, root / name)
    (root / "state").mkdir()
    monkeypatch.chdir(root)
    return root


@pytest.fixture
def config(workdir: Path) -> AppConfig:
    return AppConfig(root=workdir, backend="fake", axes=("X", "Y", "Z"), autostart=False)


@pytest.fixture
def app(config: AppConfig):
    application = build_application(config)
    yield application
    application.stop()


@pytest.fixture
def call(app):
    """Skrót wywołania operacji: ``call("machine.state")`` → dict JSON."""

    def _call(command: str, params: dict | None = None, **kwargs):
        return app.call_json(command, params, **kwargs)

    return _call


@pytest.fixture
def clock(app):
    """Przesuwa zegar atrapy o ``dt`` sekund i odświeża stan.

    Atrapa ma zegar wirtualny (``autostart=False``): bez tego ruchu nie ma, a testy
    byłyby zależne od czasu ściennego.
    """

    def _advance(dt: float) -> None:
        app.backend.advance(dt)
        app.backend.tick()

    return _advance


@pytest.fixture
def ready_machine(app, call, clock):
    """Maszyna gotowa do ruchu: E-STOP zwolniony, zasilanie włączone, osie zbazowane.

    Zwraca ten sam skrót co ``call`` — testy piszą ``ready_machine("machine.jog", ...)``.
    """
    call("machine.estop_reset")
    call("machine.power_on")
    call("machine.home")
    for _ in range(50):  # bazowanie jest ruchem w kolejce atrapy — czekamy na wynik
        if call("machine.state")["all_homed"]:
            break
        clock(0.5)
    assert call("machine.state")["all_homed"] is True, "baza nie została domknięta"
    return call
