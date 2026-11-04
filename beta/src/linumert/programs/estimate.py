"""Estymator czasu obróbki z wywołań kanonicznych interpretera LinuxCNC (sesja 053).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · 2026-10-20

Ruch bierzemy z prawdziwego interpretera (`rs274`, ten sam co w `linuxcnc_check.py`), więc
podprogramy, pętle i cykle wiercenia są już rozwinięte. Model czasu jest celowo zachowawczy:
- każdy odcinek i łuk to profil trapezowy od zera do zera (zatrzymanie w narożu — tak jak
  G61; w trybie G64 maszyna jest szybsza, więc wynik to górne oszacowanie),
- prędkość i przyspieszenie wzdłuż kierunku ruchu ograniczają osie z `[AXIS_*]` INI oraz
  `[TRAJ]MAX_LINEAR_VELOCITY`; ruch roboczy dodatkowo posuw F, łuk przyspieszenie dośrodkowe,
- DWELL dodaje czas postoju, CHANGE_TOOL stały czas `[LINUMERT]TOOL_CHANGE_TIME` (domyślnie 10 s).
Wynik: całość, ruchy szybkie / robocze / postoje / wymiany, czas na narzędzie i na krok `.lnx`
(komentarze `( krok N: ... )` z kompilatora). Model nie gwarantuje górnej granicy czasu
całego cyklu: startuje od XYZ=0, pomija oczekiwanie operatora i rozpędzanie wrzeciona.
Porównanie z Plant: pocket_calibration.json w artefaktach CI (plan 25.10).
"""

from __future__ import annotations

import configparser
import math
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ._interpreter_process import InterpreterOutputLimit
from .linuxcnc_check import InterpreterUnavailable as InterpreterUnavailable
from .linuxcnc_check import run_interpreter

AXES = "XYZ"
INCH = 25.4
_CALL = re.compile(r"^\s*\d+ N[.\d]+\s+([A-Z_]+)\((.*)\)\s*$")
_STEP = re.compile(r"^krok (\d+)\b")


@dataclass(frozen=True)
class Limits:
    max_vel: dict[str, float]          # [mm/s] na oś
    max_acc: dict[str, float]          # [mm/s²] na oś
    max_linear: float = math.inf       # [mm/s] TRAJ
    tool_change: float = 10.0          # [s]

    def along(self, u: tuple[float, float, float]) -> tuple[float, float]:
        """Prędkość i przyspieszenie dopuszczalne w kierunku jednostkowym `u`."""
        v, a = self.max_linear, math.inf
        for axis, c in zip(AXES, u, strict=True):
            if abs(c) > 1e-12:
                v = min(v, self.max_vel.get(axis, math.inf) / abs(c))
                a = min(a, self.max_acc.get(axis, math.inf) / abs(c))
        return v, a


def limits_from_ini(path: Path | str) -> Limits:
    ini = configparser.ConfigParser(strict=False, interpolation=None)
    if not ini.read(path, encoding="utf-8"):
        raise ValueError("Brak pliku INI maszyny.")

    def num(section: str, key: str, default: float) -> float:
        try:
            return float(ini.get(section, key).split()[0])
        except (configparser.Error, ValueError, IndexError):
            return default

    vel = {a: num(f"AXIS_{a}", "MAX_VELOCITY", math.inf) for a in AXES}
    acc = {a: num(f"AXIS_{a}", "MAX_ACCELERATION", math.inf) for a in AXES}
    if any(not math.isfinite(v) or v <= 0 for v in (*vel.values(), *acc.values())):
        raise ValueError("Wymagane dodatnie limity prędkości i przyspieszenia XYZ w INI.")
    linear = num("TRAJ", "MAX_LINEAR_VELOCITY", math.inf)
    change = num("LINUMERT", "TOOL_CHANGE_TIME", 10.0)
    if linear <= 0 or math.isnan(linear) or not math.isfinite(change) or change < 0:
        raise ValueError("Niepoprawny limit TRAJ lub czas wymiany narzędzia w INI.")
    return Limits(vel, acc, linear, change)


def trapezoid(length: float, v: float, a: float) -> float:
    """Czas przejazdu `length` z zatrzymaniem na końcach: v [mm/s], a [mm/s²]."""
    if length <= 0:
        return 0.0
    if not math.isfinite(a):
        return length / v
    if length >= v * v / a:
        return length / v + v / a
    return 2 * math.sqrt(length / a)


@dataclass
class Estimate:
    total: float = 0.0
    rapid: float = 0.0
    feed: float = 0.0
    dwell: float = 0.0
    tool_change: float = 0.0
    rapid_length: float = 0.0
    feed_length: float = 0.0
    per_tool: dict[int, float] = field(default_factory=dict)
    per_step: dict[int, float] = field(default_factory=dict)

    def add(self, kind: str, seconds: float, tool: int, step: int | None,
            length: float = 0.0) -> None:
        setattr(self, kind, getattr(self, kind) + seconds)
        if kind in ("rapid", "feed"):
            setattr(self, f"{kind}_length", getattr(self, f"{kind}_length") + length)
        self.total += seconds
        self.per_tool[tool] = self.per_tool.get(tool, 0.0) + seconds
        if step is not None:
            self.per_step[step] = self.per_step.get(step, 0.0) + seconds


def _floats(args: str) -> list[float]:
    return [float(x) for x in re.split(r"[,\s]+", args.strip()) if x]


def _arc(pos, args: list[float]) -> tuple[float, float]:
    """(długość, promień) łuku w płaszczyźnie XY z ARC_FEED; inne płaszczyzny jak XY."""
    ex, ey, cx, cy, rot, ez = args[:6]
    r = math.hypot(pos[0] - cx, pos[1] - cy)
    a0 = math.atan2(pos[1] - cy, pos[0] - cx)
    a1 = math.atan2(ey - cy, ex - cx)
    turns = int(rot)
    if turns > 0:   # CCW
        sweep = (a1 - a0) % (2 * math.pi) + 2 * math.pi * (turns - 1)
    else:           # CW
        sweep = (a0 - a1) % (2 * math.pi) + 2 * math.pi * (-turns - 1)
    if sweep < 1e-9 and math.hypot(ex - pos[0], ey - pos[1]) < 1e-9:
        sweep = 2 * math.pi
    planar = r * sweep
    return math.hypot(planar, ez - pos[2]), r


def estimate_canon(text: str, limits: Limits) -> Estimate:
    """Czas z wyjścia `rs274` (wywołania kanoniczne, jedno w linii)."""
    est = Estimate()
    pos = (0.0, 0.0, 0.0)
    scale, feed, tool, step = 1.0, 0.0, 0, None
    plane = "CANON_PLANE_XY"
    for line in text.splitlines():
        m = _CALL.match(line)
        if m is None:
            continue
        name, args = m.groups()
        if name == "USE_LENGTH_UNITS":
            scale = INCH if "INCHES" in args else 1.0
        elif name == "SELECT_PLANE":
            plane = args.strip()
        elif name == "SET_FEED_MODE" and _floats(args)[-1] != 0:
            raise ValueError("Model czasu obsługuje wyłącznie posuw G94 (mm/min).")
        elif name == "SET_FEED_RATE":
            feed = _floats(args)[0] * scale / 60.0
        elif name == "COMMENT":
            sm = _STEP.match(args.strip().strip('"').strip())
            if sm:
                step = int(sm.group(1))
        elif name == "CHANGE_TOOL":
            tool = int(_floats(args)[0])
            est.add("tool_change", limits.tool_change, tool, step)
        elif name == "DWELL":
            est.add("dwell", _floats(args)[0], tool, step)
        elif name in ("STRAIGHT_TRAVERSE", "STRAIGHT_FEED"):
            end = tuple(v * scale for v in _floats(args)[:3])
            d = [b - a for a, b in zip(pos, end, strict=True)]
            length = math.sqrt(sum(c * c for c in d))
            if length > 0:
                v, a = limits.along(tuple(c / length for c in d))
                kind = "rapid" if name == "STRAIGHT_TRAVERSE" else "feed"
                if kind == "feed" and feed > 0:
                    v = min(v, feed)
                est.add(kind, trapezoid(length, v, a), tool, step, length)
            pos = end
        elif name == "ARC_FEED":
            if plane != "CANON_PLANE_XY":
                raise ValueError("Model czasu łuków obsługuje wyłącznie płaszczyznę G17.")
            vals = _floats(args)
            vals = [v * scale if i != 4 else v for i, v in enumerate(vals)]
            length, r = _arc(pos, vals)
            plane_v, plane_a = limits.along((1.0, 0.0, 0.0))
            v2, a2 = limits.along((0.0, 1.0, 0.0))
            v, a = min(plane_v, v2, feed if feed > 0 else math.inf), min(plane_a, a2)
            dz = abs(vals[5] - pos[2])
            if dz > 0 and length > 0:
                vz, az = limits.along((0.0, 0.0, dz / length))
                v, a = min(v, vz), min(a, az)
            if r > 0 and math.isfinite(a):
                v = min(v, math.sqrt(0.5 * a * r))  # połowa przyspieszenia na dośrodkowe
            est.add("feed", trapezoid(length, v, a), tool, step, length)
            pos = (vals[0], vals[1], vals[5])
    return est


def estimate_ngc(ngc: Path | str, ini: Path | str, root: Path | str | None = None,
                 timeout: float = 20.0) -> Estimate:
    """Uruchamia rs274 na programie i liczy czas z limitami z `ini` (InterpreterUnavailable)."""
    try:
        run = run_interpreter(ngc, root, timeout)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("Przekroczono limit czasu analizy (możliwa pętla bez końca). "
                         "Nie wyliczono czasu całego programu; sprawdź składnię i warunek "
                         "wyjścia z pętli.") from exc
    except InterpreterOutputLimit as exc:
        raise ValueError(str(exc) + " Nie wyliczono czasu całego programu.") from exc
    if run.returncode or "PROGRAM_END()" not in run.stdout:
        raise ValueError("interpreter nie doszedł do końca programu: "
                         + (run.stderr or run.stdout)[-500:])
    return estimate_canon(run.stdout, limits_from_ini(ini))
