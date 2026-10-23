# SPDX-License-Identifier: GPL-2.0-or-later
"""Ograniczony audyt tekstowych połączeń HAL, bez ich wykonania. Model-Author: Codex."""
from __future__ import annotations

import shlex
from pathlib import Path

ARROWS = {"=>", "<=", "<=>"}
# Audyt nie modeluje działania komponentów ani kierunków pinów.
KNOWN = {"loadrt", "loadusr", "addf", "delf", "start", "stop", "setp", "sets", "newsig",
         "net", "source", "show", "getp", "gets", "waitusr", "unloadrt", "unloadusr"}
DYNAMIC = ("$", "[", "]", "`")


def audit_hal(paths: list[Path], cfg, base_dir: Path) -> list[str]:
    """Weryfikuje znane bezpośrednie połączenia; wynik nie dopuszcza maszyny do ruchu."""
    errors: list[str] = []
    signals: dict[str, set[str]] = {}
    owners: dict[str, str] = {}
    visited: set[Path] = set()
    active: set[Path] = set()

    def read(path: Path) -> None:
        path = path.resolve()
        if path in active:
            errors.append(f"{path}: cykliczne source")
            return
        if path in visited:
            return
        if len(visited) >= 64:
            errors.append("przekroczony limit 64 plików HAL")
            return
        visited.add(path)
        active.add(path)
        try:
            if path.suffix != ".hal":
                errors.append(f"{path}: wymagany tekstowy plik .hal, bez Tcl")
                return
            text = path.read_text(encoding="utf-8").replace("\\\n", " ")
            for number, line in enumerate(text.splitlines(), 1):
                where = f"{path}:{number}"
                try:
                    words = shlex.split(line, comments=True)
                except ValueError as exc:
                    errors.append(f"{where}: {exc}")
                    continue
                if not words:
                    continue
                cmd, *args = words
                if cmd not in KNOWN:
                    errors.append(f"{where}: nieobsługiwane polecenie {cmd}")
                elif cmd == "source":
                    if len(args) != 1 or any(c in args[0] for c in DYNAMIC):
                        errors.append(f"{where}: nierozwiązane source")
                    else:
                        read(base_dir / args[0])
                elif cmd == "net":
                    if not args or any(c in " ".join(args) for c in DYNAMIC):
                        errors.append(f"{where}: nierozwiązane net")
                        continue
                    signal, *pins = args
                    members = signals.setdefault(signal, set())
                    for pin in pins:
                        if pin in ARROWS:
                            continue
                        if pin in owners and owners[pin] != signal:
                            errors.append(f"{where}: pin {pin} w różnych sygnałach")
                        owners[pin] = signal
                        members.add(pin)
                elif cmd == "setp" and args and args[0] == "iocontrol.0.emc-enable-in":
                    errors.append(f"{where}: stałe setp zezwolenia zamiast monitora")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{path}: {exc}")
        finally:
            active.remove(path)

    for path in paths:
        read(path if path.is_absolute() else base_dir / path)
    if not paths:
        errors.append("wymagany co najmniej jeden plik HAL")
    if cfg.get("LINUMERT", "MACHINE_PROFILE", fallback="").strip() != "hardware":
        errors.append("audyt toru fizycznego wymaga profilu hardware")
        return errors
    enable = "iocontrol.0.emc-enable-in"
    for members in signals.values():
        if enable in members and "iocontrol.0.user-enable-out" in members:
            errors.append("hardware: bezpośrednia pętla user-enable-out → emc-enable-in")
    monitor = cfg.get("SAFETY", "ESTOP_MONITOR_PIN", fallback="").strip()
    if not any({enable, monitor} <= pins for pins in signals.values()):
        errors.append("hardware: brak bezpośredniego połączenia monitora E-STOP z emc-enable-in")
    heartbeat = cfg.get("SAFETY", "PC_HEARTBEAT_OUTPUT_PIN", fallback="").strip()
    if not any({"linumert.hmi-heartbeat", heartbeat} <= pins for pins in signals.values()):
        errors.append("hardware: brak połączenia heartbeat HMI z deklarowanym wyjściem")
    feedback = cfg.get("SAFETY", "PC_WATCHDOG_MONITOR_PIN", fallback="").strip()
    if not feedback or feedback not in owners:
        errors.append("hardware: brak podłączenia monitora zewnętrznego watchdoga PC")
    return errors
