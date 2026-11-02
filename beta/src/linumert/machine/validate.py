"""Walidacja spojnosci machine.yaml (REQ-VM-11).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

``schema.py`` sprawdza strukture; tutaj reguly miedzy polami. Kazda regula zwraca komunikaty po
polsku ze sciezka pola. ``validate_machine`` zbiera wszystkie bledy naraz (nie konczy na pierwszym).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

from .schema import (
    KINEMATIC_PRESETS,
    MachineConfig,
    MachineConfigError,
    load_machine,
)

Rule = Callable[[MachineConfig, set[str] | None], Iterable[str]]


def _dupes(items: Iterable[str]) -> list[str]:
    return [name for name, count in Counter(items).items() if count > 1]


def r_axis_letters_unique(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for letter in _dupes(a.letter for a in cfg.axes):
        yield f"axes: os {letter} wystepuje wiecej niz raz"


def r_preset_matches_axes(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    preset = cfg.kinematics.preset
    if preset is None:
        return
    expected = set(KINEMATIC_PRESETS[preset])
    actual = {a.letter for a in cfg.axes}
    if expected != actual:
        yield (
            f"kinematics.preset: {preset} wymaga osi {''.join(sorted(expected))}, "
            f"a zdefiniowano {''.join(sorted(actual))}"
        )


def r_chain_links(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    chain = cfg.kinematics.chain
    if not chain:
        return
    ids = [link.id for link in chain]
    for name in _dupes(ids):
        yield f"kinematics.chain: powtorzony identyfikator czlonu {name}"
    by_id = {link.id: link for link in chain}
    for index, link in enumerate(chain):
        if link.parent is not None and link.parent not in ids:
            yield f"kinematics.chain[{index}].parent: nieznany czlon {link.parent}"
        parent = by_id.get(link.parent) if link.parent is not None else None
        if parent is not None and parent.branch != link.branch:
            yield (f"kinematics.chain[{index}].branch: czlon {link.id} musi byc w tej samej "
                   f"galezi co rodzic {parent.id} ({parent.branch})")
    for index, axis in enumerate(cfg.axes):
        link = by_id.get(axis.letter)
        if link is None:
            yield f"axes[{index}]: brak czlonu o id {axis.letter} w kinematics.chain"
        elif (link.kind == "rotary") != axis.rotary:
            yield (f"kinematics.chain: czlon {axis.letter} ma rodzaj {link.kind}, a os "
                   f"{axis.letter} jest {'obrotowa' if axis.rotary else 'liniowa'}")


def r_travel_order(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        if axis.travel[0] >= axis.travel[1]:
            yield f"axes[{index}].travel: minimum musi byc mniejsze od maksimum"
        if axis.soft_limits[0] >= axis.soft_limits[1]:
            yield f"axes[{index}].soft_limits: minimum musi byc mniejsze od maksimum"


def r_soft_in_travel(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        if axis.soft_limits[0] < axis.travel[0] or axis.soft_limits[1] > axis.travel[1]:
            yield f"axes[{index}].soft_limits: poza zakresem mechanicznym travel (os {axis.letter})"


def r_limits_order(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    """Krancowka lezy poza programowym limitem, a ogranicznik mechaniczny za krancowka."""
    for index, axis in enumerate(cfg.axes):
        base = f"axes[{index}]"
        low, high = axis.limits.min, axis.limits.max
        if low is not None and low.position > axis.soft_limits[0]:
            yield f"{base}.limits.min.position: krancowka musi byc nie dalej niz soft_limits.min"
        if high is not None and high.position < axis.soft_limits[1]:
            yield f"{base}.limits.max.position: krancowka musi byc nie blizej niz soft_limits.max"
        stop_low, stop_high = axis.hardstops.min, axis.hardstops.max
        if stop_low is not None:
            edge = low.position if low is not None else axis.soft_limits[0]
            if stop_low.position > edge:
                yield f"{base}.hardstops.min.position: ogranicznik musi byc za krancowka"
        if stop_high is not None:
            edge = high.position if high is not None else axis.soft_limits[1]
            if stop_high.position < edge:
                yield f"{base}.hardstops.max.position: ogranicznik musi byc za krancowka"


def r_home_shared(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        sensor = axis.home_sensor
        if sensor is None or sensor.shared_with is None:
            continue
        side = sensor.shared_with.removeprefix("limit_")
        if getattr(axis.limits, side) is None:
            yield (
                f"axes[{index}].home_sensor.shared_with: os {axis.letter} nie ma krancowki "
                f"{side}, ktora miala byc wspolna"
            )


def r_drive_names(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for name in _dupes(d.name for d in cfg.drives):
        yield f"drives: powtorzona nazwa napedu {name}"


def r_drive_refs(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    known = {d.name for d in cfg.drives}
    for index, axis in enumerate(cfg.axes):
        for drive in axis.drives:
            if drive not in known:
                yield f"axes[{index}].drives: nieznany naped {drive}"
    if cfg.spindle.drive not in known:
        yield f"spindle.drive: nieznany naped {cfg.spindle.drive}"


def r_drive_single_owner(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    owners: dict[str, list[str]] = {}
    for axis in cfg.axes:
        for drive in axis.drives:
            owners.setdefault(drive, []).append(axis.letter)
    for drive, letters in owners.items():
        if len(letters) > 1 or letters.count(letters[0]) > 1:
            yield f"axes: naped {drive} jest przypisany do wielu osi ({', '.join(letters)})"
    if cfg.spindle.drive in owners:
        yield f"spindle.drive: naped {cfg.spindle.drive} jest juz uzyty przez os"


def r_templates_known(cfg: MachineConfig, templates: set[str] | None) -> Iterable[str]:
    if templates is None:
        return
    for index, drive in enumerate(cfg.drives):
        if drive.template not in templates:
            yield f"drives[{index}].template: brak szablonu {drive.template} w bibliotece napedow"


def r_gantry(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        if len(axis.drives) > 1:
            if not axis.homing.gantry_square:
                yield (
                    f"axes[{index}].homing.gantry_square: os {axis.letter} ma wiele napedow "
                    "(portal) - wlacz zgrywanie portalu"
                )
            if axis.gantry_max_skew is None:
                yield f"axes[{index}].gantry_max_skew: portal wymaga maksymalnego przekosu"
        elif axis.homing.gantry_square or axis.gantry_max_skew is not None:
            yield f"axes[{index}]: zgrywanie portalu dotyczy tylko osi z wieloma napedami"


def _homing_side(axis_direction: int) -> str:
    return "min" if axis_direction < 0 else "max"


def r_homing_prereqs(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        homing = axis.homing
        side = _homing_side(homing.direction)
        base = f"axes[{index}].homing"
        if homing.method in ("switch", "switch_index"):
            if axis.home_sensor is None and getattr(axis.limits, side) is None:
                yield f"{base}.method: {homing.method} wymaga czujnika bazy lub krancowki {side}"
        elif homing.method == "hardstop":
            if getattr(axis.hardstops, side) is None:
                yield f"{base}.method: hardstop wymaga ogranicznika mechanicznego {side}"
        if homing.latch_speed > homing.search_speed:
            yield f"{base}.latch_speed: nie moze byc wieksza niz search_speed"
        if homing.search_speed > axis.max_velocity:
            yield f"{base}.search_speed: wieksza niz max_velocity osi {axis.letter}"


def r_homing_order(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    z = cfg.axis("Z")
    if z is None:
        return
    for index, axis in enumerate(cfg.axes):
        if axis.letter in ("X", "Y") and axis.homing.order < z.homing.order:
            yield (
                f"axes[{index}].homing.order: os {axis.letter} nie moze byc bazowana "
                "przed osia Z (ryzyko zderzenia narzedzia)"
            )


def r_inputs_exist(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    known = set(cfg.io.inputs)

    def need(path: str, name: str | None) -> Iterable[str]:
        if name is not None and name not in known:
            yield f"{path}: wejscie {name} nie jest zdefiniowane w io.inputs"

    yield from need("io.estop.input", cfg.io.estop.input)
    for index, axis in enumerate(cfg.axes):
        for side in ("min", "max"):
            switch = getattr(axis.limits, side)
            if switch is not None:
                yield from need(f"axes[{index}].limits.{side}.input", switch.input)
        if axis.home_sensor is not None:
            yield from need(f"axes[{index}].home_sensor.input", axis.home_sensor.input)
    setter = cfg.positions.tool_setter
    if setter is not None:
        yield from need("positions.tool_setter.input", setter.input)
    if cfg.probe is not None:
        yield from need("probe.input", cfg.probe.input)
    for name, pin in cfg.toolchanger.sensors.items():
        yield from need(f"toolchanger.sensors.{name}", pin)
    tc = cfg.toolchanger
    if tc.clamp is not None:
        yield from need("toolchanger.clamp.sensor", tc.clamp.sensor)
    if tc.cover is not None:
        yield from need("toolchanger.cover.sensor_open", tc.cover.sensor_open)
        yield from need("toolchanger.cover.sensor_closed", tc.cover.sensor_closed)
    outputs = set(cfg.io.outputs)
    for role, name in tc.outputs.items():
        if name not in outputs:
            yield f"toolchanger.outputs.{role}: wyjscie {name} nie jest zdefiniowane w io.outputs"
    if tc.air_blast_output is not None and tc.air_blast_output not in outputs:
        yield (f"toolchanger.air_blast_output: wyjscie {tc.air_blast_output} nie jest "
               "zdefiniowane w io.outputs")


def r_io_pins_unique(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for kind, mapping in (("inputs", cfg.io.inputs), ("outputs", cfg.io.outputs)):
        for pin, count in Counter(mapping.values()).items():
            if count > 1:
                names = sorted(n for n, p in mapping.items() if p == pin)
                yield f"io.{kind}: numer {pin} uzyty wielokrotnie ({', '.join(names)})"
        for name, pin in mapping.items():
            if pin < 0:
                yield f"io.{kind}.{name}: numer wejscia/wyjscia nie moze byc ujemny"


def r_estop_present(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    # CLAUDE.md §6: konfiguracja sprzetowa bez E-STOP jest odrzucana.
    if cfg.io.estop.input not in cfg.io.inputs:
        yield "io.estop: brak wejscia E-STOP - konfiguracja bez E-STOP jest odrzucana"


def r_spindle(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    if cfg.spindle.min_rpm >= cfg.spindle.max_rpm:
        yield "spindle.min_rpm: musi byc mniejsze od max_rpm"


def r_safe_z(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    z = cfg.axis("Z")
    if z is None:
        yield "axes: brak osi Z"
        return
    if not (z.soft_limits[0] <= cfg.positions.safe_z <= z.soft_limits[1]):
        yield "positions.safe_z: poza zakresem programowym osi Z"


def r_positions_in_range(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    def check(path: str, point: tuple[float, float, float]) -> Iterable[str]:
        for letter, value in zip("XYZ", point, strict=True):
            axis = cfg.axis(letter)
            if axis is not None and not (axis.soft_limits[0] <= value <= axis.soft_limits[1]):
                yield f"{path}: wspolrzedna {letter}={value} poza zakresem programowym"

    if cfg.positions.manual_change is not None:
        yield from check("positions.manual_change", cfg.positions.manual_change)
    if cfg.positions.tool_setter is not None:
        yield from check("positions.tool_setter.position", cfg.positions.tool_setter.position)


def r_forbidden_zones(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, zone in enumerate(cfg.forbidden_zones):
        if any(lo >= hi for lo, hi in zip(zone.min, zone.max, strict=True)):
            yield f"forbidden_zones[{index}]: min musi byc mniejsze od max w kazdej osi"
    for name in _dupes(z.name for z in cfg.forbidden_zones):
        yield f"forbidden_zones: powtorzona nazwa strefy {name}"


def r_toolchanger(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    tc = cfg.toolchanger
    if tc.type == "manual":
        if tc.slots != 0:
            yield "toolchanger.slots: reczna zmiana narzedzia nie ma gniazd (slots=0)"
        return
    if tc.slots < 1:
        yield f"toolchanger.slots: magazyn {tc.type} wymaga co najmniej 1 gniazda"
    if tc.base_position is None and tc.slot_positions is None:
        yield "toolchanger: podaj base_position albo slot_positions"
    if tc.slot_positions is not None and len(tc.slot_positions) != tc.slots:
        yield "toolchanger.slot_positions: liczba pozycji rozna od slots"
    if tc.type == "rack_linear" and tc.slot_positions is None and tc.pitch_mm is None:
        yield "toolchanger.pitch_mm: regal liniowy wymaga rozstawu gniazd"
    if tc.type in ("carousel", "umbrella") and tc.slot_positions is None and tc.radius_mm is None:
        yield f"toolchanger.radius_mm: magazyn {tc.type} wymaga promienia"
    if tc.retract_z is not None and tc.approach_z is not None and tc.approach_z > tc.retract_z:
        yield "toolchanger.approach_z: nie moze byc wyzej niz retract_z"


def r_collision_bodies(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for name in _dupes(b.name for b in cfg.collision_bodies):
        yield f"collision_bodies: powtorzona nazwa bryly {name}"


def r_rotary_ranges(cfg: MachineConfig, _t: set[str] | None) -> Iterable[str]:
    for index, axis in enumerate(cfg.axes):
        if axis.rotary and (axis.travel[1] - axis.travel[0]) > 36000:
            yield f"axes[{index}].travel: zakres osi obrotowej powyzej 100 obrotow jest nierealny"


RULES: tuple[Rule, ...] = (
    r_axis_letters_unique,
    r_preset_matches_axes,
    r_chain_links,
    r_travel_order,
    r_soft_in_travel,
    r_limits_order,
    r_home_shared,
    r_drive_names,
    r_drive_refs,
    r_drive_single_owner,
    r_templates_known,
    r_gantry,
    r_homing_prereqs,
    r_homing_order,
    r_inputs_exist,
    r_io_pins_unique,
    r_estop_present,
    r_spindle,
    r_safe_z,
    r_positions_in_range,
    r_forbidden_zones,
    r_toolchanger,
    r_collision_bodies,
    r_rotary_ranges,
)


def validate_machine(cfg: MachineConfig, drive_templates: set[str] | None = None) -> list[str]:
    """Zwraca liste bledow spojnosci (pusta = poprawna)."""
    errors: list[str] = []
    for rule in RULES:
        errors.extend(rule(cfg, drive_templates))
    return errors


def load_valid_machine(
    source: Path | str, drive_templates: set[str] | None = None
) -> MachineConfig:
    """Wczytuje plik, sprawdza strukture i spojnosc; wyjatek MachineConfigError z lista bledow."""
    cfg = load_machine(source)
    errors = validate_machine(cfg, drive_templates)
    if errors:
        raise MachineConfigError(errors)
    return cfg
