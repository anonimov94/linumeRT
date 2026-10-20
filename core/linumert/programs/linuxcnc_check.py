"""Dodatkowa kontrola programu w interpreterze LinuxCNC (`rs274`), gdy jest dostępny (sesja 044).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 044

Lekser (`lexer.py`) sprawdza składnię bez LinuxCNC. Interpreter LinuxCNC wykrywa dodatkowo błędy
semantyczne (brak posuwu dla G1, słowo E bez kodu, który go używa, kolizje grup modalnych…).
`rs274` (samodzielny interpreter z instalacji LinuxCNC) czyta plik i wypisuje wywołania
kanoniczne; zawsze kończy się kodem 0 i drukuje menu, więc błąd to każda linia, która nie jest
ani menu, ani wywołaniem kanonicznym. Komunikaty są po angielsku (tekst LinuxCNC).

Interpreter działa poza RT, w osobnym procesie z limitem czasu (pętla bez końca w programie
nie zawiesza ekranu). Ścieżki z ustawień albo zmiennej `LINUXCNC_DIR` (CLAUDE.md §9).
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_CANON = re.compile(r"^\s*\d+ N[.\d]+\s")
_MENU = ("enter a number:", "1 = ", "2 = ", "3 = ", "4 = ", "5 = ", "enter choice")


class InterpreterUnavailable(RuntimeError):
    """Brak interpretera LinuxCNC (rs274) w tym środowisku."""


@dataclass(frozen=True)
class InterpreterResult:
    messages: list[str]       # błędy interpretera (puste = program przeszedł do końca)
    completed: bool           # interpreter doszedł do PROGRAM_END
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return not self.messages and self.completed and not self.timed_out


def find_linuxcnc(root: Path | str | None = None) -> tuple[list[str], Path | None]:
    """Polecenie uruchamiające rs274: RIP (`<root>/scripts/rip-environment`) albo instalacja
    systemowa (rs274 w PATH). Zwraca (prefiks polecenia powłoki, katalog konfiguracji sim)."""
    candidate = root or os.environ.get("LINUXCNC_DIR")
    if candidate:
        base = Path(candidate).resolve()
        if (base / "scripts" / "rip-environment").exists() and (base / "bin" / "rs274").exists():
            script = shlex.quote(str(base / "scripts" / "rip-environment"))
            return ([f"source {script} >/dev/null &&"],
                    base / "configs" / "sim" / "axis")
        raise InterpreterUnavailable(f"{base}: brak scripts/rip-environment albo bin/rs274")
    if shutil.which("rs274"):
        system_sim = Path("/usr/share/doc/linuxcnc/examples/sample-configs/sim/axis")
        return [], system_sim if system_sim.exists() else None
    raise InterpreterUnavailable("brak rs274 (ustaw LINUXCNC_DIR na budowę RIP LinuxCNC 2.9)")


def check_with_linuxcnc(ngc: Path | str, root: Path | str | None = None,
                        timeout: float = 20.0) -> InterpreterResult:
    """Uruchamia rs274 na pliku; InterpreterUnavailable, gdy nie ma LinuxCNC."""
    prefix, sim = find_linuxcnc(root)
    ngc = Path(ngc).resolve()
    options = "-i axis.ini -t sim.tbl " if sim is not None and (sim / "axis.ini").exists() else ""
    # exec keeps the timeout attached to rs274, not a shell waiting for its child.
    command = " ".join(prefix + [f"exec rs274 {options}-n 0 {shlex.quote(str(ngc))} </dev/null"])
    try:
        run = subprocess.run(["bash", "-c", command], cwd=sim, capture_output=True, text=True,
                             timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return InterpreterResult(["przekroczony czas interpretera (pętla bez końca?)"], False,
                                 timed_out=True)
    output = run.stdout + run.stderr
    messages = []
    for line in output.splitlines():
        text = line.replace("enter choice => executing", "").strip()
        if text and not _CANON.match(line) and not text.startswith(_MENU):
            messages.append(text)
    if run.returncode:
        messages.append(f"interpreter zakończył się kodem {run.returncode}")
    return InterpreterResult(messages, "PROGRAM_END()" in output)
