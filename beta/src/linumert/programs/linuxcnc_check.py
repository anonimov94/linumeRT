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
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ._interpreter_process import InterpreterOutputLimit, run_bounded

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


def _with_machine_remaps(config: str, machine_ini: Path) -> str:
    """REMAP i SUBROUTINE_PATH z INI maszyny (ścieżki bezwzględne) do konfiguracji analizy."""
    import configparser

    ini = configparser.RawConfigParser(strict=False)
    ini.optionxform = str
    if not ini.read(machine_ini, encoding="utf-8") or not ini.has_section("RS274NGC"):
        return config
    base = machine_ini.resolve().parent
    paths = [str((base / p).resolve()) if not os.path.isabs(p) else p
             for p in ini.get("RS274NGC", "SUBROUTINE_PATH", fallback="").split(":") if p]
    remaps = re.findall(r"(?im)^[ \t]*REMAP[ \t]*=.*$", machine_ini.read_text(encoding="utf-8"))
    if not paths and not remaps:
        return config
    config = re.sub(r"(?im)^[ \t]*(SUBROUTINE_PATH|REMAP)[ \t]*=.*(?:\n|$)", "", config)
    extra = [f"SUBROUTINE_PATH = {':'.join(paths)}"] if paths else []
    extra += [r.strip() for r in remaps]
    config, count = re.subn(r"(?im)^(\[RS274NGC\][ \t]*)$", "\\g<1>\n" + "\n".join(extra),
                            config, count=1)
    return config if count else config + "\n[RS274NGC]\n" + "\n".join(extra) + "\n"


def run_interpreter(ngc: Path | str, root: Path | str | None = None,
                    timeout: float = 20.0,
                    parameters_from: Path | str | None = None,
                    linear_units: str | None = None,
                    machine_ini: Path | str | None = None) -> subprocess.CompletedProcess:
    """Offline only: private HOME/tool mmap, parameters and cwd for every invocation.

    LinuxCNC 2.9.10 rs274 truncates $HOME/.tool.mmap even before reading its options.
    Sharing HOME with the live controller can therefore crash QtVCP with SIGBUS.
    Never invoke the standalone interpreter with the controller's HOME.
    """
    prefix, sim = find_linuxcnc(root)
    ngc = Path(ngc).resolve()
    with tempfile.TemporaryDirectory(prefix="linumert-analysis-") as directory:
        private = Path(directory)
        env = os.environ.copy()
        env.update(HOME=directory, TMPDIR=directory)
        parameters = private / "analysis.var"
        parameters.touch()  # rs274 links the original before saving its first backup.
        options = []
        if sim is not None and (sim / "axis.ini").exists():
            config = (sim / "axis.ini").read_text()
            # INI loading overrides -v. Enforce private parameters there as well,
            # including samples which name an absolute/shared parameter file.
            config = re.sub(r"(?im)^[ \t]*PARAMETER_FILE[ \t]*=.*(?:\n|$)", "", config)
            config, count = re.subn(r"(?im)^(\[RS274NGC\][ \t]*)$",
                                    r"\g<1>\nPARAMETER_FILE = analysis.var", config, count=1)
            if not count:
                config += "\n[RS274NGC]\nPARAMETER_FILE = analysis.var\n"
            if machine_ini is not None:  # remapy i podprogramy maszyny (np. M6 → G43)
                config = _with_machine_remaps(config, Path(machine_ini))
            if linear_units:  # parametry z .var są w jednostkach maszyny, nie domyślnych (cale)
                config = re.sub(r"(?im)^([ \t]*LINEAR_UNITS[ \t]*=).*$",
                                rf"\g<1> {linear_units}", config)
            ini = private / "analysis.ini"
            ini.write_text(config)
            options = ["-i", str(ini),
                       "-t", str((sim / "sim.tbl").resolve())]
            if (sim / "sim.var").exists():
                shutil.copyfile(sim / "sim.var", parameters)
        if parameters_from is not None and Path(parameters_from).is_file():
            shutil.copyfile(parameters_from, parameters)  # kopia: oryginał nietknięty
        options += ["-v", str(parameters), "-n", "0", str(ngc)]
        command = " ".join(prefix + ["exec rs274 " + shlex.join(options)])
        return run_bounded(["bash", "-c", command], cwd=directory, env=env, timeout=timeout)


def check_with_linuxcnc(ngc: Path | str, root: Path | str | None = None,
                        timeout: float = 20.0) -> InterpreterResult:
    """Uruchamia izolowane rs274; limit analizy nie jest pozytywnym wynikiem kontroli."""
    try:
        run = run_interpreter(ngc, root, timeout)
    except subprocess.TimeoutExpired:
        return InterpreterResult(["przekroczony czas interpretera (pętla bez końca?)"], False,
                                 timed_out=True)
    except InterpreterOutputLimit as exc:
        return InterpreterResult([str(exc)], False)
    output = run.stdout + run.stderr
    messages = []
    for line in output.splitlines():
        text = line.replace("enter choice => executing", "").strip()
        if text and not _CANON.match(line) and not text.startswith(_MENU):
            messages.append(text)
    if run.returncode:
        messages.append(f"interpreter zakończył się kodem {run.returncode}")
    return InterpreterResult(messages, "PROGRAM_END()" in output)
