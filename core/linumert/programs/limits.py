"""Kontrola limitów osi przed startem programu (zakres 031/051).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

LinuxCNC odrzuca ruch dopiero, gdy planer do niego dojdzie, więc maszyna staje w połowie
programu. Tu ścieżka z interpretera `rs274` (z prawdziwymi przesunięciami układów z pliku
parametrów, bez ruchu maszyny) jest porównywana z `MIN_LIMIT`/`MAX_LIMIT` z INI. Kontrola
jest diagnostyczna: nie zmienia programu ani zachowania sterownika. Sprawdza punkty końcowe
ruchów; łuk może wyjść poza limit między punktami (NIE jest wykrywany). Położenie maszynowe =
program + przesunięcie G5x + G92 + korekta długości narzędzia; obrót XY (G10 L2 R) pominięty.
"""

from __future__ import annotations

import configparser
import dataclasses
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ._interpreter_process import InterpreterOutputLimit
from .linuxcnc_check import run_interpreter

AXES = ("X", "Y", "Z")
INCH = 25.4
_CALL = re.compile(r"^\s*\d+ N([.\d]+)\s+([A-Z0-9_]+)\((.*)\)\s*$")
EPS = 1e-6


@dataclass(frozen=True)
class Violation:
    line: int
    axis: str
    value: float          # [mm] położenie maszynowe, którego program żąda
    limit: float          # [mm] przekroczony limit
    side: str             # "min" albo "max"
    count: int = 1        # ile ruchów przekracza tę samą stronę limitu tej osi

    def message(self) -> str:
        kind = "dolny" if self.side == "min" else "górny"
        more = f" (i {self.count - 1} kolejnych ruchów)" if self.count > 1 else ""
        return (f"linia {self.line}: oś {self.axis} do {self.value:.3f} mm przekracza "
                f"{kind} limit {self.limit:.3f} mm{more}")


@dataclass(frozen=True)
class LimitReport:
    violations: list[Violation]
    cuts_without_tlo: bool = False   # ruch roboczy przy nieaktywnej korekcie długości (G49)

    @property
    def ok(self) -> bool:
        return not self.violations


def limits_from_ini(path: Path | str) -> dict[str, tuple[float, float]]:
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    if not ini.read(path, encoding="utf-8"):
        raise ValueError("Brak pliku INI maszyny.")
    out: dict[str, tuple[float, float]] = {}
    for axis in AXES:
        try:
            lo = float(ini.get(f"AXIS_{axis}", "MIN_LIMIT").split()[0])
            hi = float(ini.get(f"AXIS_{axis}", "MAX_LIMIT").split()[0])
        except (configparser.Error, ValueError, IndexError):
            continue
        out[axis] = (lo, hi)
    if not out:
        raise ValueError("INI nie zawiera MIN_LIMIT/MAX_LIMIT osi XYZ.")
    return out


def _linear_units(path: Path | str) -> str:
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    ini.read(path, encoding="utf-8")
    value = ini.get("TRAJ", "LINEAR_UNITS", fallback="mm").split()[0].lower()
    return "inch" if value in ("inch", "in", "imperial") else "mm"


def parameter_file(ini_path: Path | str) -> Path | None:
    """Plik parametrów (przesunięcia układów) z [RS274NGC] PARAMETER_FILE obok INI."""
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    ini.read(ini_path, encoding="utf-8")
    name = ini.get("RS274NGC", "PARAMETER_FILE", fallback="").strip()
    return (Path(ini_path).resolve().parent / name) if name else None


def _floats(args: str) -> list[float]:
    return [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]


def check_canon(text: str, limits: dict[str, tuple[float, float]]) -> list[Violation]:
    return analyze_canon(text, limits).violations


def analyze_canon(text: str, limits: dict[str, tuple[float, float]]) -> LimitReport:
    """Pierwsze przekroczenie każdej osi i strony limitu; `count` liczy wszystkie ruchy."""
    cuts_without_tlo = False
    found: list[Violation] = []
    seen: dict[tuple[str, str], int] = {}
    scale = 1.0
    g5x = g92 = tlo = (0.0, 0.0, 0.0)  # przesunięcia układu, G92 i korekta długości (XYZ)
    touched: set[str] = set()  # interpreter startuje w zerze maszyny: oś nieruszona = bez oceny
    for raw in text.splitlines():
        m = _CALL.match(raw)
        if m is None:
            continue
        line = int(m.group(1)) if m.group(1).isdigit() else 0
        name, args = m.group(2), m.group(3)
        if name == "USE_LENGTH_UNITS":
            scale = INCH if "INCHES" in args else 1.0
            continue
        if name == "SET_G5X_OFFSET":
            g5x = tuple(_floats(args)[1:4])
            continue
        if name == "SET_G92_OFFSET":
            g92 = tuple(_floats(args)[:3])
            continue
        if name == "USE_TOOL_LENGTH_OFFSET":
            tlo = tuple(_floats(args)[:3])
            continue
        if name == "ARC_FEED":
            vals = _floats(args)
            pos = (vals[0], vals[1], vals[5])
        elif name in ("STRAIGHT_TRAVERSE", "STRAIGHT_FEED"):
            pos = tuple(_floats(args)[:3])
        else:
            continue
        if name != "STRAIGHT_TRAVERSE" and not any(tlo):
            cuts_without_tlo = True
        for i, (axis, value) in enumerate(zip(AXES, pos, strict=False)):
            if axis not in limits:
                continue
            value = (value + g5x[i] + g92[i] + tlo[i]) * scale
            if axis not in touched:
                if abs(value) < EPS:
                    continue
                touched.add(axis)
            lo, hi = limits[axis]
            for side, limit, bad in (("min", lo, value < lo - EPS), ("max", hi, value > hi + EPS)):
                key = (axis, side)
                if bad and key not in seen:
                    seen[key] = len(found)
                    found.append(Violation(line, axis, value, limit, side))
                elif bad:
                    first = found[seen[key]]
                    found[seen[key]] = dataclasses.replace(first, count=first.count + 1)
    return LimitReport(found, cuts_without_tlo)


_N_WORD = re.compile(r"^\s*[Nn]\d+\s*")


def number_lines(text: str) -> str:
    """Kopia analityczna: każdy blok dostaje N<numer linii pliku> (rs274 drukuje tylko słowa N)."""
    out = []
    for number, raw in enumerate(text.splitlines(), start=1):
        body = _N_WORD.sub("", raw)
        out.append(raw if not body.strip() or body.lstrip().startswith("%")
                   else f"N{number} {body}")
    return "\n".join(out) + "\n"


def check_ngc(ngc: Path | str, ini: Path | str, var: Path | str | None = None,
              root: Path | str | None = None, timeout: float = 20.0) -> list[Violation]:
    return analyze_ngc(ngc, ini, var, root, timeout).violations


def analyze_ngc(ngc: Path | str, ini: Path | str, var: Path | str | None = None,
                root: Path | str | None = None, timeout: float = 20.0) -> LimitReport:
    """Uruchamia rs274 (z kopią parametrów `var`) i porównuje ścieżkę z limitami INI."""
    limits = limits_from_ini(ini)
    units = _linear_units(ini)
    try:
        text = Path(ngc).read_text(encoding="utf-8", errors="replace")
        with tempfile.TemporaryDirectory(prefix="linumert-limits-") as directory:
            copy = Path(directory) / "analiza.ngc"
            copy.write_text(number_lines(text), encoding="utf-8")
            run = run_interpreter(copy, root, timeout, parameters_from=var,
                                  linear_units=units, machine_ini=ini)
    except OSError as exc:
        raise ValueError(f"nie można odczytać programu: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Przekroczono limit czasu analizy (możliwa pętla bez końca).") from exc
    except InterpreterOutputLimit as exc:
        raise ValueError(str(exc)) from exc
    if run.returncode or "PROGRAM_END()" not in run.stdout:
        raise ValueError("interpreter nie doszedł do końca programu: "
                         + (run.stderr or run.stdout)[-300:])
    return analyze_canon(run.stdout, limits)
