"""Kontrola limitów osi przed startem programu (zakres 031/051).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

LinuxCNC odrzuca ruch dopiero, gdy planer do niego dojdzie, więc maszyna staje w połowie
programu. Tu ścieżka z interpretera `rs274` (z prawdziwymi przesunięciami układów z pliku
parametrów, bez ruchu maszyny) jest porównywana z `MIN_LIMIT`/`MAX_LIMIT` z INI. Kontrola
jest diagnostyczna: nie zmienia programu ani zachowania sterownika. Sprawdza końce
ruchów i ekstrema łuków w płaszczyznach XY/YZ/XZ z uwzględnieniem obrotu XY (G10 L2 R).
Sprawdza też osie obrotowe A/B/C (w stopniach, z pominięciem WRAPPED_ROTARY).
Położenie maszynowe XYZ = (program + G92) obrócony w XY + G5x + korekta długości narzędzia.
"""

from __future__ import annotations

import configparser
import dataclasses
import math
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ._interpreter_process import InterpreterOutputLimit
from .linuxcnc_check import run_interpreter

AXES = ("X", "Y", "Z")
ROTARY = ("A", "B", "C")
ALL_AXES = AXES + ROTARY
INCH = 25.4
_CALL = re.compile(r"^\s*\d+ N([.\d]+)\s+([A-Z0-9_]+)\((.*)\)\s*$")
EPS = 1e-6


@dataclass(frozen=True)
class Violation:
    line: int
    axis: str
    value: float          # [mm/°] położenie maszynowe, którego program żąda
    limit: float          # [mm/°] przekroczony limit
    side: str             # "min" albo "max"
    count: int = 1        # ile ruchów przekracza tę samą stronę limitu tej osi

    def message(self) -> str:
        kind = "dolny" if self.side == "min" else "górny"
        more = f" (i {self.count - 1} kolejnych ruchów)" if self.count > 1 else ""
        unit = "°" if self.axis in ROTARY else "mm"
        return (f"linia {self.line}: oś {self.axis} do {self.value:.3f} {unit} przekracza "
                f"{kind} limit {self.limit:.3f} {unit}{more}")


@dataclass(frozen=True)
class LimitReport:
    violations: list[Violation]
    cuts_without_tlo: bool = False   # ruch roboczy przy nieaktywnej korekcie długości (G49)

    @property
    def ok(self) -> bool:
        return not self.violations


def limits_from_ini(path: Path | str) -> dict[str, tuple[float, float]]:
    """Granice XYZ w mm i A/B/C w stopniach (bez osi zawijanych)."""
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    if not ini.read(path, encoding="utf-8"):
        raise ValueError("Brak pliku INI maszyny.")
    scale = INCH if _linear_units(path) == "inch" else 1.0
    out: dict[str, tuple[float, float]] = {}
    for axis in AXES:
        try:
            lo = float(ini.get(f"AXIS_{axis}", "MIN_LIMIT").split()[0])
            hi = float(ini.get(f"AXIS_{axis}", "MAX_LIMIT").split()[0])
        except (configparser.Error, ValueError, IndexError):
            continue
        out[axis] = (lo * scale, hi * scale)
    if not out:
        raise ValueError("INI nie zawiera MIN_LIMIT/MAX_LIMIT osi XYZ.")
    for axis in ROTARY:
        section = f"AXIS_{axis}"
        if ini.getboolean(section, "WRAPPED_ROTARY", fallback=False):
            continue
        try:
            lo = float(ini.get(section, "MIN_LIMIT").split()[0])
            hi = float(ini.get(section, "MAX_LIMIT").split()[0])
        except (configparser.Error, ValueError, IndexError):
            continue
        out[axis] = (lo, hi)  # stopnie, niezależne od LINEAR_UNITS
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


def _six(values: list[float]) -> tuple[float, ...]:
    """Dopełnia pozycje i przesunięcia XYZABC zerami."""
    return tuple((values + [0.0] * 6)[:6])


def check_canon(text: str, limits: dict[str, tuple[float, float]]) -> list[Violation]:
    return analyze_canon(text, limits).violations


def _arc_candidates(
    start: tuple[float, ...], vals: list[float], plane: tuple[int, int, int],
    xy_rot: float = 0.0,
) -> list[tuple[float, ...]]:
    """Ekstrema osi w zakresie łuku i jego koniec, w kolejności przejścia."""
    first, second, spiral = plane
    end = list(start)
    end[first], end[second], end[spiral] = vals[0], vals[1], vals[5]
    for index, value in enumerate(vals[6:9], start=3):
        end[index] = value
    endpoint = tuple(end)
    center_first, center_second, rotation = vals[2], vals[3], vals[4]
    radius = math.hypot(start[first] - center_first, start[second] - center_second)
    end_radius = math.hypot(endpoint[first] - center_first, endpoint[second] - center_second)
    # Niepełny/niepoprawny zapis kanoniczny: zachowaj dotychczasową kontrolę końca.
    if (rotation == 0 or radius < EPS
            or not math.isclose(radius, end_radius, rel_tol=1e-4, abs_tol=EPS)):
        return [endpoint]

    start_angle = math.atan2(start[second] - center_second, start[first] - center_first)
    end_angle = math.atan2(endpoint[second] - center_second, endpoint[first] - center_first)
    direction = 1 if rotation > 0 else -1
    if (math.hypot(endpoint[first] - start[first],
                   endpoint[second] - start[second]) <= EPS):
        sweep = abs(rotation) * math.tau
    else:
        sweep = ((end_angle - start_angle) * direction) % math.tau
        if abs(rotation) > 1:
            sweep += (abs(rotation) - 1) * math.tau
    if sweep <= EPS:
        return [endpoint]

    # Each machine coordinate is A*cos(theta) + B*sin(theta) + C*progress
    # plus a constant. Include the linear helix term before finding extrema.
    angle = math.radians(xy_rot)
    cosine, sine = math.cos(angle), math.sin(angle)
    rows = ((cosine, -sine, 0), (sine, cosine, 0), (0, 0, 1))
    progress_values: set[float] = set()
    for row in rows:
        a = -direction * radius * row[first]
        b = direction * radius * row[second]
        drift = row[spiral] * (endpoint[spiral] - start[spiral]) / sweep
        amplitude = math.hypot(a, b)
        if amplitude < EPS or abs(drift) > amplitude:
            continue  # This coordinate is constant or monotonic.
        phase = math.atan2(b, a)
        root = math.asin(max(-1.0, min(1.0, -drift / amplitude)))
        for theta in (root - phase, math.pi - root - phase):
            progress = ((theta - start_angle) * direction) % math.tau
            if progress <= EPS:
                progress += math.tau
            # Equal-phase extrema differ only by the linear drift per turn.
            # First and last suffice even for arbitrarily many revolutions.
            last = math.floor((sweep - progress) / math.tau)
            for turn in (0, last):
                value = progress + turn * math.tau
                if turn >= 0 and EPS < value < sweep - EPS:
                    progress_values.add(value)

    interior = []
    for progress in sorted(progress_values):
        theta = start_angle + direction * progress
        point = list(start)
        point[first] = center_first + radius * math.cos(theta)
        point[second] = center_second + radius * math.sin(theta)
        point[spiral] = start[spiral] + (endpoint[spiral] - start[spiral]) * progress / sweep
        for index in range(3, len(start)):
            point[index] = start[index] + (endpoint[index] - start[index]) * progress / sweep
        interior.append(tuple(point))
    return interior + [endpoint]


def analyze_canon(text: str, limits: dict[str, tuple[float, float]]) -> LimitReport:
    """Pierwsze przekroczenie każdej osi i strony limitu; `count` liczy sprawdzone punkty."""
    cuts_without_tlo = False
    found: list[Violation] = []
    seen: dict[tuple[str, str], int] = {}
    scale = 1.0
    g5x = g92 = tlo = (0.0,) * 6  # przesunięcia układu, G92 i korekta narzędzia (XYZABC)
    touched: set[str] = set()  # interpreter startuje w zerze maszyny: oś nieruszona = bez oceny
    position = (0.0,) * 6
    plane = (0, 1, 2)  # XY, osie: pierwsza, druga, spiralna
    xy_rot = 0.0  # stopnie, dodatnie = CCW

    def machine_position(pos: tuple[float, ...]) -> tuple[float, ...]:
        x, y, z = (pos[i] + g92[i] for i in range(3))
        angle = math.radians(xy_rot)
        cosine, sine = math.cos(angle), math.sin(angle)
        rotated = (x * cosine - y * sine, x * sine + y * cosine, z)
        coordinates = rotated + tuple(pos[i] + g92[i] for i in range(3, len(pos)))
        return tuple(value + g5x[i] + tlo[i] for i, value in enumerate(coordinates))

    def program_position(machine: tuple[float, ...]) -> tuple[float, ...]:
        x, y, z = (machine[i] - g5x[i] - tlo[i] for i in range(3))
        angle = math.radians(xy_rot)
        cosine, sine = math.cos(angle), math.sin(angle)
        rotated = (x * cosine + y * sine, -x * sine + y * cosine, z)
        coordinates = rotated + tuple(machine[i] - g5x[i] - tlo[i]
                                      for i in range(3, len(machine)))
        return tuple(value - g92[i] for i, value in enumerate(coordinates))

    def check_position(pos: tuple[float, ...], line: int) -> None:
        machine = tuple(value * scale if i < 3 else value
                        for i, value in enumerate(machine_position(pos)))
        for axis, value in zip(ALL_AXES, machine, strict=True):
            if axis not in limits:
                continue
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

    for raw in text.splitlines():
        m = _CALL.match(raw)
        if m is None:
            continue
        line = int(m.group(1)) if m.group(1).isdigit() else 0
        name, args = m.group(2), m.group(3)
        if name == "USE_LENGTH_UNITS":
            new_scale = INCH if "INCHES" in args else 1.0
            position = tuple(value * scale / new_scale if i < 3 else value
                             for i, value in enumerate(position))
            factor = scale / new_scale
            g5x, g92, tlo = (tuple(value * factor if i < 3 else value
                                   for i, value in enumerate(offset))
                             for offset in (g5x, g92, tlo))
            scale = new_scale
            continue
        if name in ("SET_G5X_OFFSET", "SET_G92_OFFSET", "USE_TOOL_LENGTH_OFFSET",
                    "SET_XY_ROTATION"):
            machine = machine_position(position)
            values = _floats(args)
            if name == "SET_G5X_OFFSET":
                g5x = _six(values[1:7])
            elif name == "SET_G92_OFFSET":
                g92 = _six(values[:6])
            elif name == "USE_TOOL_LENGTH_OFFSET":
                tlo = _six(values[:6])
            else:
                xy_rot = values[0] if values else 0.0
            position = program_position(machine)
            continue
        if name == "SELECT_PLANE":
            plane_name = args.strip().rsplit("_", 1)[-1].upper()
            plane = {"XY": (0, 1, 2), "YZ": (1, 2, 0), "XZ": (2, 0, 1)}.get(plane_name, plane)
            continue
        if name == "ARC_FEED":
            vals = _floats(args)
            candidates = _arc_candidates(position, vals, plane, xy_rot)
            pos = candidates[-1]
        elif name in ("STRAIGHT_TRAVERSE", "STRAIGHT_FEED"):
            pos = _six(_floats(args)[:6])
            candidates = [pos]
        else:
            continue
        if name != "STRAIGHT_TRAVERSE" and not any(tlo):
            cuts_without_tlo = True
        for candidate in candidates:
            check_position(candidate, line)
        position = pos
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
