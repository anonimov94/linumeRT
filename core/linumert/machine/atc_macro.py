"""Generator makra remapu M6 dla ATC z sekcji `toolchanger` w machine.yaml (sesja 066).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 066.
Geometry and preflight: Model-Author: Codex.

Zakres: magazyn liniowy (`rack_linear`), narzędzie N leży w gnieździe N (RANDOM_TOOLCHANGER=0).
Karuzela i parasol nie są jeszcze obsługiwane — generator odmawia jawnie, zamiast zgadywać.
Makro tylko układa ruchy i czeka na czujniki; stan fizyczny po przerwaniu (E-STOP, timeout)
nie jest zgadywany: błąd kończy program przez `(abort,…)` i wymaga ręcznego uzgodnienia magazynu.
Wszystkie ruchy w G53 (współrzędne maszyny). NIEZWERYFIKOWANE NA SPRZĘCIE.
"""

from __future__ import annotations

import math

from .toolchanger_geometry import pocket_positions

APPROACH_FEED_MM_MIN = 500.0
SENSOR_TIMEOUT_S = 3.0


class AtcMacroError(ValueError):
    """Konfiguracja nie pozwala wygenerować makra ATC."""


def _num(value: float) -> str:
    return f"{round(value, 4):.4f}".rstrip("0").rstrip(".") if value else "0"


def _io(cfg, section: str, name: str, what: str) -> int:
    pins = getattr(cfg.io, section)
    if name not in pins:
        raise AtcMacroError(f"toolchanger: {what} '{name}' nie występuje w io.{section}")
    return pins[name]


def _positions(cfg) -> list[tuple[float, float, float]]:
    """Reject a rack that cannot be reached using the generated G53 coordinates."""
    tc = cfg.toolchanger
    if tc.type != "rack_linear":
        raise AtcMacroError(
            f"toolchanger.type={tc.type}: makro ATC obsługuje na razie tylko rack_linear")
    if tc.slots < 1:
        raise AtcMacroError("toolchanger: wymagane slots >= 1")
    if tc.slot_positions is not None:
        if len(tc.slot_positions) != tc.slots:
            raise AtcMacroError("toolchanger.slot_positions: liczba pozycji różna od slots")
    elif tc.base_position is None or tc.pitch_mm is None:
        raise AtcMacroError("toolchanger: wymagane slot_positions albo base_position i pitch_mm")
    elif not all(math.isfinite(v) for v in
                 (*tc.base_position, tc.pitch_mm, tc.base_orientation_deg)):
        raise AtcMacroError("toolchanger: geometria bazowa musi być skończona")
    if tc.approach_z is None or tc.retract_z is None:
        raise AtcMacroError("toolchanger: wymagane approach_z i retract_z")
    heights = (tc.approach_z, tc.retract_z, cfg.positions.safe_z)
    if not all(math.isfinite(v) for v in heights):
        raise AtcMacroError("toolchanger: wysokości muszą być skończone")
    if not tc.approach_z <= tc.retract_z <= cfg.positions.safe_z:
        raise AtcMacroError("toolchanger: wymagane approach_z <= retract_z <= positions.safe_z")
    points = pocket_positions(tc)
    checks = [(f"gniazdo {i}", p) for i, p in enumerate(points, 1)]
    checks += [("retract_z", (None, None, tc.retract_z)),
               ("safe_z", (None, None, cfg.positions.safe_z))]
    for label, point in checks:
        for letter, value in zip("XYZ", point, strict=True):
            axis = cfg.axis(letter)
            if axis is None:
                raise AtcMacroError(f"toolchanger: wymagana oś {letter}")
            if value is None:
                continue
            if not math.isfinite(value):
                raise AtcMacroError(f"toolchanger: {label} {letter}: wartość nieskończona")
            lo, hi = axis.soft_limits
            # Check the geometry and the actual four-decimal command after rounding.
            if not (lo <= value <= hi and lo <= float(_num(value)) <= hi):
                raise AtcMacroError(f"toolchanger: {label} {letter} poza zakresem programowym")
    return points


def plan_swap(cfg, old: int, new: int) -> list[tuple]:
    """Kolejność kroków wymiany old → new (0 = puste wrzeciono) w G53; wzorzec dla makra i testów.

    Kroki: ("cover", otwarta), ("xy", x, y), ("z", z), ("release", włączone),
    ("wait", rola czujnika, "high"|"low").
    """
    tc = cfg.toolchanger
    positions = _positions(cfg)
    if any(type(tool) is not int or not 0 <= tool <= tc.slots for tool in (old, new)):
        raise AtcMacroError("toolchanger: numer narzędzia poza zakresem magazynu")

    def xy(slot: int) -> tuple:
        return ("xy", *positions[slot - 1][:2])

    if old == new:
        return []
    steps: list[tuple] = [("z", cfg.positions.safe_z)]
    if tc.cover is not None:
        steps += [("cover", True), ("wait", "cover_open", "high")]
    if old > 0:
        steps += [xy(old), ("z", tc.approach_z), ("release", True), ("wait", "clamped", "low"),
                  ("z", tc.retract_z)]
    else:
        steps.append(("release", True))
    if new > 0:
        steps += [xy(new), ("z", tc.approach_z), ("release", False), ("wait", "clamped", "high"),
                  ("z", tc.retract_z)]
    if tc.cover is not None:
        steps += [("cover", False), ("wait", "cover_closed", "high")]
    steps.append(("z", cfg.positions.safe_z))
    return steps


def generate_atc_m6(cfg, name: str = "lrt_m6_atc") -> str:
    """Zwraca tekst podprogramu `o<name>` do `REMAP = M6 modalgroup=6 ngc=<name>`."""
    tc = cfg.toolchanger
    positions = _positions(cfg)
    if "clamp_release" not in tc.outputs:
        raise AtcMacroError("toolchanger.outputs: brak roli clamp_release")
    if tc.clamp is None or not tc.clamp.sensor:
        raise AtcMacroError("toolchanger.clamp.sensor: brak czujnika zacisku")
    release = _io(cfg, "outputs", tc.outputs["clamp_release"], "wyjście zwolnienia zacisku")
    clamped = _io(cfg, "inputs", tc.clamp.sensor, "czujnik zacisku")
    cover = tc.cover
    cover_out = cover_open = cover_closed = None
    if cover is not None:
        if "cover_open" not in tc.outputs:
            raise AtcMacroError("toolchanger.outputs: osłona wymaga roli cover_open")
        cover_out = _io(cfg, "outputs", tc.outputs["cover_open"], "wyjście osłony")
        cover_open = _io(cfg, "inputs", cover.sensor_open, "czujnik otwarcia osłony")
        cover_closed = _io(cfg, "inputs", cover.sensor_closed, "czujnik zamknięcia osłony")

    feed = _num(APPROACH_FEED_MM_MIN)
    timeout = _num(SENSOR_TIMEOUT_S)
    safe_z, approach_z = _num(cfg.positions.safe_z), _num(tc.approach_z)
    retract_z = _num(tc.retract_z)

    def wait(pin: int, level: str, what: str) -> list[str]:
        mode = {"high": 3, "low": 4}[level]
        return [f"M66 P{pin} L{mode} Q{timeout}",
                f"o<{what}_chk> if [#5399 LT 0]",
                f"  (abort, ATC: brak potwierdzenia czujnika: {what})",
                f"o<{what}_chk> endif"]

    lines = [
        "; SPDX-License-Identifier: GPL-2.0-or-later",
        "; Model-Author: Claude",
        f"; Generowane z machine.yaml ({tc.type}, gniazd {tc.slots}); nie edytuj ręcznie.",
        f"; Remap M6 dla ATC (INI: REMAP=M6 modalgroup=6 ngc={name}). Narzędzie N = gniazdo N.",
        "; Błąd lub timeout = abort; magazyn uzgodnij ręcznie. NIEZWERYFIKOWANE NA SPRZĘCIE.",
        f"o<{name}> sub",
        "#<lrt_new> = #<_selected_tool>",
        "#<lrt_old> = #<_current_tool>",
        f"o<range> if [[#<lrt_new> LT 0] OR [#<lrt_new> GT {tc.slots}] "
        f"OR [#<lrt_old> LT 0] OR [#<lrt_old> GT {tc.slots}]]",
        "  (abort, ATC: numer narzędzia poza zakresem magazynu)",
        "o<range> endif",
        "o<same> if [#<lrt_new> EQ #<lrt_old>]",
        f"  o<{name}> return",
        "o<same> endif",
        "o<modes> if [[#<_metric> EQ 0] OR [#<_absolute> EQ 0] "
        "OR [#<_units_per_minute> EQ 0]]",
        "  (abort, ATC: wymiana wymaga G21 G90 G94)",
        "o<modes> endif",
        "o<spindle> if [#<_spindle_on> NE 0]",
        "  (abort, ATC: przed wymiana wymagane M5)",
        "o<spindle> endif",
        f"G53 G0 Z{safe_z}",
    ]
    if cover_out is not None:
        lines += [f"M64 P{cover_out}", *wait(cover_open, "high", "oslona_otwarta")]

    def slot_xy(var: str) -> list[str]:
        result = []
        for slot, (x, y, _) in enumerate(positions, 1):
            label = f"{var}_slot_{slot}"
            result += [f"  o<{label}> if [#<{var}> EQ {slot}]",
                       f"    G53 G0 X{_num(x)} Y{_num(y)}",
                       f"  o<{label}> endif"]
        return result

    lines += [
        "; odłożenie starego narzędzia (T0 w wrzecionie = nic do odłożenia)",
        "o<put> if [#<lrt_old> GT 0]",
        *slot_xy("lrt_old"),
        f"  G53 G1 Z{approach_z} F{feed}",
        f"  M64 P{release}",
        "  " + "\n  ".join(wait(clamped, "low", "zacisk_zwolniony")),
        f"  G53 G0 Z{retract_z}",
        "o<put> else",
        f"  M64 P{release}",
        "o<put> endif",
        "; pobranie nowego narzędzia (T0 = zostaw wrzeciono puste)",
        "o<get> if [#<lrt_new> GT 0]",
        *slot_xy("lrt_new"),
        f"  G53 G1 Z{approach_z} F{feed}",
        f"  M65 P{release}",
        "  " + "\n  ".join(wait(clamped, "high", "zacisk_zamkniety")),
        f"  G53 G1 Z{retract_z} F{feed}",
        "o<get> endif",
    ]
    if cover_out is not None:
        lines += [f"M65 P{cover_out}", *wait(cover_closed, "high", "oslona_zamknieta")]
    lines += [
        f"G53 G0 Z{safe_z}",
        "M6",
        "o<offset> if [#<lrt_new> GT 0]",
        "  G43 H#<lrt_new>",
        "o<offset> else",
        "  G49",
        "o<offset> endif",
        f"o<{name}> endsub",
        "M2",
        "",
    ]
    return "\n".join(lines)
