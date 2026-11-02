"""Schemat machine.yaml (Pydantic v2): jedno zrodlo prawdy dla Plant i generatora konfiguracji.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude

Jednostki: mm, stopnie (osie obrotowe A/B/C), mm/s i mm/s^2, wspolrzedne w ukladzie maszyny.
Ten modul sprawdza strukture i pojedyncze pola; spojnosc calej konfiguracji (REQ-VM-11)
sprawdza ``validate.py``. Wszystkie bledy sa po polsku i wskazuja sciezke pola.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError, model_validator

Vec3 = tuple[float, float, float]
Contact = Literal["NC", "NO"]
AxisLetter = Literal["X", "Y", "Z", "A", "B", "C", "U", "V", "W"]
KINEMATIC_PRESETS = {
    "router_gantry_xyz": "XYZ",
    "mill_table_xyz": "XYZ",
    "xyza_rotary": "XYZA",
    "xyzac_trunnion": "XYZAC",
    "xyzbc_trunnion": "XYZBC",
}
ROTARY_LETTERS = ("A", "B", "C")


class MachineConfigError(Exception):
    """Konfiguracja maszyny jest niepoprawna; ``errors`` to komunikaty po polsku."""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class Strict(BaseModel):
    # Wspólna granica Plant/generatora: NaN omija porównania zakresów, a inf
    # nie jest poprawną prędkością, pozycją ani wymiarem modelu fizycznego.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class MachineInfo(Strict):
    name: str = Field(min_length=1)
    type: Literal["router", "mill", "other"] = "other"


class Link(Strict):
    id: str = Field(min_length=1)
    kind: Literal["linear", "rotary"]
    axis: Vec3
    offset: Vec3 = (0.0, 0.0, 0.0)
    parent: str | None = None
    # Galaz lancucha (sesja 014): czlony niosace narzedzie albo detal (stol). Czlon o id rownym
    # literze osi jest napedzany ta osia; pozostale sa stale.
    branch: Literal["tool", "workpiece"] = "tool"

    @model_validator(mode="after")
    def _axis_not_zero(self) -> Link:
        if not any(self.axis):
            raise ValueError("wektor osi nie moze byc zerowy")
        return self


class Kinematics(Strict):
    preset: (
        Literal[
            "router_gantry_xyz", "mill_table_xyz", "xyza_rotary", "xyzac_trunnion", "xyzbc_trunnion"
        ]
        | None
    ) = None
    chain: list[Link] | None = None

    @model_validator(mode="after")
    def _one_of_preset_or_chain(self) -> Kinematics:
        if (self.preset is None) == (self.chain is None):
            raise ValueError("podaj dokladnie jedno: preset albo chain")
        return self


class HardStop(Strict):
    position: float
    stiffness_n_mm: float = Field(default=500.0, gt=0)
    damping_ns_mm: float = Field(default=5.0, ge=0)


class LimitSwitch(Strict):
    position: float
    hysteresis: float = Field(default=0.2, ge=0)
    contact: Contact = "NC"
    input: str = Field(min_length=1)
    debounce_ms: float = Field(default=1.0, ge=0)


class HomeSensor(Strict):
    shared_with: Literal["limit_min", "limit_max"] | None = None
    position: float | None = None
    hysteresis: float = Field(default=0.1, ge=0)
    contact: Contact = "NO"
    input: str | None = None

    @model_validator(mode="after")
    def _shared_or_own(self) -> HomeSensor:
        own = self.position is not None and self.input is not None
        if self.shared_with is None and not own:
            raise ValueError("czujnik wlasny wymaga pol position i input")
        if self.shared_with is not None and (self.position is not None or self.input is not None):
            raise ValueError("czujnik wspolny z krancowka nie ma wlasnych pol position i input")
        return self


class Limits(Strict):
    min: LimitSwitch | None = None
    max: LimitSwitch | None = None


class HardStops(Strict):
    min: HardStop | None = None
    max: HardStop | None = None
    # REQ-VM-04: wjazd w zderzak daje dodatkowo awarie napedu (E-4207)
    drive_fault: bool = False


class Homing(Strict):
    method: Literal["switch", "switch_index", "hardstop", "absolute", "drive"]
    direction: Literal[-1, 1] = -1
    search_speed: float = Field(default=20.0, gt=0)
    latch_speed: float = Field(default=2.0, gt=0)
    # metody switch/switch_index: zbocze zatrzaśnięcia bazy (jak znak HOME_LATCH_VEL w LinuxCNC)
    #   approach — zjazd z czujnika, ponowny wolny dojazd, baza na zadziałaniu (ten sam znak);
    #   release  — wolny zjazd z czujnika, baza na zwolnieniu styku (NC: obwód znów zamknięty;
    #              znak przeciwny). Po zadziałaniu czujnika master zawsze zawraca, nigdy nie
    #              jedzie dalej w stronę zderzaka.
    latch: Literal["approach", "release"] = "approach"
    offset: float = 0.0
    order: int = Field(default=0, ge=0)
    gantry_square: bool = False
    # metoda hardstop (c): ograniczony moment i detekcja
    reduced_torque_pct: float | None = Field(default=None, gt=0, le=100)
    detect: Literal["torque", "following_error"] | None = None
    detect_threshold: float | None = Field(default=None, gt=0)
    detect_time_ms: float | None = Field(default=None, gt=0)
    # metoda absolute (d): bateria enkodera
    battery_backed: bool = True
    # metoda drive (e): metoda bazowania CiA 402 (tryb 6)
    cia402_method: int | None = Field(default=None, ge=1, le=35)

    @model_validator(mode="after")
    def _method_parameters(self) -> Homing:
        if self.method == "hardstop":
            missing = [
                name
                for name in ("reduced_torque_pct", "detect", "detect_threshold", "detect_time_ms")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"metoda hardstop wymaga pol: {', '.join(missing)}")
        if self.latch == "release" and self.method not in ("switch", "switch_index"):
            raise ValueError("latch: release dotyczy tylko metod switch i switch_index")
        if self.method == "drive" and self.cia402_method is None:
            raise ValueError("metoda drive wymaga pola cia402_method")
        return self


class Axis(Strict):
    letter: AxisLetter
    drives: list[str] = Field(min_length=1)
    travel: tuple[float, float]
    soft_limits: tuple[float, float]
    hardstops: HardStops = HardStops()
    limits: Limits = Limits()
    home_sensor: HomeSensor | None = None
    max_velocity: float = Field(gt=0)
    max_acceleration: float = Field(gt=0)
    homing: Homing
    gantry_max_skew: float | None = Field(default=None, gt=0)

    @property
    def rotary(self) -> bool:
        return self.letter in ROTARY_LETTERS


class DriveInstance(Strict):
    # Klucz `id` (REQ-VD-02, sesja 013); `name` pozostaje akceptowany dla zgodnosci z sesja 010.
    name: str = Field(min_length=1, validation_alias=AliasChoices("id", "name"))
    template: str = Field(min_length=1)
    overrides: dict[str, Any] = {}


class ForbiddenZone(Strict):
    name: str = Field(min_length=1)
    min: Vec3
    max: Vec3


class Spindle(Strict):
    drive: str = Field(min_length=1)
    max_rpm: float = Field(gt=0)
    min_rpm: float = Field(default=0.0, ge=0)
    ramp_up_s: float = Field(default=2.0, gt=0)
    ramp_down_s: float = Field(default=2.0, gt=0)


class Cover(Strict):
    actuation_ms: float = Field(gt=0)
    sensor_open: str | None = None
    sensor_closed: str | None = None


class Clamp(Strict):
    time_ms: float = Field(gt=0)
    sensor: str | None = None


class ToolChanger(Strict):
    type: Literal["manual", "rack_linear", "carousel", "umbrella"] = "manual"
    slots: int = Field(default=0, ge=0)
    base_position: Vec3 | None = None
    base_orientation_deg: float = 0.0
    slot_positions: list[Vec3] | None = None
    pitch_mm: float | None = Field(default=None, gt=0)  # regal liniowy
    radius_mm: float | None = Field(default=None, gt=0)  # karuzela, parasolowy
    approach_z: float | None = None
    retract_z: float | None = None
    cover: Cover | None = None
    sensors: dict[str, str] = {}
    clamp: Clamp | None = None
    air_blast_output: str | None = None
    # sesja 019/020: wyjścia sterujące (rola -> nazwa z io.outputs): clamp_release (zwolnienie
    # narzędzia), cover_open (osłona), carousel_step (krok karuzeli), umbrella_in (wahadło)
    outputs: dict[Literal["clamp_release", "cover_open", "carousel_step", "umbrella_in"], str] = {}
    index_ms: float = Field(default=500.0, gt=0)  # krok karuzeli / ruch wahadła
    tolerance_mm: float = Field(default=0.5, gt=0)  # dopuszczalne niewspółosiowe gniazdo-wrzeciono


class ToolSetter(Strict):
    position: Vec3
    height: float
    input: str = Field(min_length=1)


class Positions(Strict):
    manual_change: Vec3 | None = None
    safe_z: float
    tool_setter: ToolSetter | None = None


class CollisionBody(Strict):
    name: str = Field(min_length=1)
    shape: Literal["box", "cylinder"]
    attached_to: Literal["head", "spindle", "table", "magazine", "toolsetter", "vise"]
    size: list[float] = Field(min_length=2, max_length=3)
    position: Vec3

    @model_validator(mode="after")
    def _size_matches_shape(self) -> CollisionBody:
        expected = 3 if self.shape == "box" else 2
        if len(self.size) != expected or any(value <= 0 for value in self.size):
            raise ValueError(
                f"ksztalt {self.shape} wymaga {expected} dodatnich wymiarow"
                + (" (x, y, z)" if self.shape == "box" else " (srednica, wysokosc)")
            )
        return self


class EStop(Strict):
    input: str = Field(min_length=1)
    contact: Contact = "NC"
    # Reakcja Plant na otwarcie petli: STO (awaria napedow) albo quick stop (hamowanie rampa)
    action: Literal["sto", "quick_stop"] = "sto"


class ProbeTarget(Strict):
    # box: prostopadloscian przygotowki; plate: plytka (kontakt ponizej max.z w obrysie XY)
    type: Literal["box", "plate"]
    min: Vec3
    max: Vec3

    @model_validator(mode="after")
    def _ordered(self) -> ProbeTarget:
        count = 3 if self.type == "box" else 2
        if any(self.min[i] >= self.max[i] for i in range(count)):
            raise ValueError("min musi byc mniejsze od max" + (" (x, y)" if count == 2 else ""))
        return self


class Probe(Strict):
    """Sonda w wrzecionie (sesja 014): wejscie i cel w ukladzie detalu."""

    input: str = Field(min_length=1)
    contact: Contact = "NO"
    tip_length: float = Field(default=50.0, ge=0)  # od nosa wrzeciona [mm]
    target: ProbeTarget


class IO(Strict):
    inputs: dict[str, int] = {}
    outputs: dict[str, int] = {}
    estop: EStop


class Hardware(Strict):
    """Sprzęt rzeczywisty (sesja 061, REQ-VD-06): interfejs i kanały napędów.

    `channels`: id napędu → numer kanału stepgen (parport/Mesa) albo pozycja slave EtherCAT.
    Sterownik i skalę napędu podaje szablon (sekcja `real:`). NIEZWERYFIKOWANE NA SPRZĘCIE.
    """

    interface: Literal["parport", "mesa", "ethercat"]
    board: Literal["7i96s", "7i76e"] | None = None       # karta Mesa
    address: str | None = None                            # parport: 0x378; Mesa: adres IP
    channels: dict[str, int] = Field(min_length=1)
    spindle_device: str | None = None                     # port falownika, np. /dev/ttyUSB0
    # Piny fizyczne HAL (sesja 062): wejście/wyjście z io.inputs/io.outputs → pin karty, np.
    # parport.0.pin-10-in, hm2_7i96s.0.inm.00.input-00. Stan jak w Plant: 1 = obwód zamknięty.
    # Wybór pinów należy do projektu maszyny; generator ich nie zgaduje.
    inputs: dict[str, str] = {}
    outputs: dict[str, str] = {}
    step_dir: dict[str, tuple[int, int]] = {}             # parport: napęd → (pin step, pin dir)
    base_period_ns: int = Field(default=25000, ge=5000, le=100000)  # parport: wątek impulsów
    # Kontrakt bezpieczeństwa (docs/bezpieczenstwo, deployment.py): wyjście sygnału życia PC
    # do zewnętrznego watchdoga i wejście jego potwierdzenia.
    heartbeat_output: str | None = None
    watchdog_monitor: str | None = None

    @model_validator(mode="after")
    def _board(self) -> Hardware:
        if self.interface == "mesa" and self.board is None:
            raise ValueError("interfejs mesa wymaga pola board (7i96s albo 7i76e)")
        if self.interface != "mesa" and self.board is not None:
            raise ValueError("pole board dotyczy tylko interfejsu mesa")
        if any(value < 0 for value in self.channels.values()):
            raise ValueError("numery kanałów muszą być nieujemne")
        return self


class MachineConfig(Strict):
    schema_version: Literal[1] = 1
    # Cel konfiguracji (sesja 061): plant (wirtualna obrabiarka), sim (LinuxCNC sim), hardware.
    # Reszta opisu maszyny jest wspólna; hardware wymaga sekcji `hardware:`.
    target: Literal["plant", "sim", "hardware"] = "plant"
    hardware: Hardware | None = None
    machine: MachineInfo
    kinematics: Kinematics
    axes: list[Axis] = Field(min_length=3, max_length=6)
    drives: list[DriveInstance] = Field(min_length=1)
    forbidden_zones: list[ForbiddenZone] = []
    spindle: Spindle
    toolchanger: ToolChanger = ToolChanger()
    positions: Positions
    collision_bodies: list[CollisionBody] = []
    probe: Probe | None = None
    io: IO

    def axis(self, letter: str) -> Axis | None:
        return next((axis for axis in self.axes if axis.letter == letter), None)

    @model_validator(mode="after")
    def _target(self) -> MachineConfig:
        if self.target == "hardware" and self.hardware is None:
            raise ValueError("target: hardware wymaga sekcji hardware (interfejs i kanały napędów)")
        if self.hardware is not None:
            known = {d.name for d in self.drives}
            unknown = sorted(set(self.hardware.channels) - known)
            if unknown:
                raise ValueError(f"hardware.channels: nieznane napędy {', '.join(unknown)}")
        return self


# ---- ladowanie i bledy po polsku -----------------------------------------
_MESSAGES = {
    "missing": "brak wymaganego pola",
    "extra_forbidden": "nieznane pole",
    "string_too_short": "tekst nie moze byc pusty",
    "too_short": "za malo elementow",
    "too_long": "za duzo elementow",
    "float_parsing": "oczekiwano liczby",
    "float_type": "oczekiwano liczby",
    "finite_number": "oczekiwano liczby skonczonej",
    "int_parsing": "oczekiwano liczby calkowitej",
    "int_type": "oczekiwano liczby calkowitej",
    "string_type": "oczekiwano tekstu",
    "bool_parsing": "oczekiwano wartosci tak/nie (true/false)",
    "bool_type": "oczekiwano wartosci tak/nie (true/false)",
    "dict_type": "oczekiwano obiektu (klucz: wartosc)",
    "list_type": "oczekiwano listy",
    "tuple_type": "oczekiwano listy wartosci",
}


def _path(location: tuple[Any, ...]) -> str:
    result = ""
    for part in location:
        result += f"[{part}]" if isinstance(part, int) else (f".{part}" if result else str(part))
    return result or "(korzen)"


def _message(error: dict[str, Any]) -> str:
    kind = error["type"]
    context = error.get("ctx", {})
    if kind in _MESSAGES:
        return _MESSAGES[kind]
    if kind == "literal_error":
        return f"niedozwolona wartosc (dozwolone: {context.get('expected', '?')})"
    if kind in ("greater_than", "greater_than_equal", "less_than", "less_than_equal"):
        words = {
            "greater_than": "wieksza niz",
            "greater_than_equal": "co najmniej",
            "less_than": "mniejsza niz",
            "less_than_equal": "co najwyzej",
        }
        limit = context.get("gt", context.get("ge", context.get("lt", context.get("le"))))
        return f"wartosc musi byc {words[kind]} {limit}"
    if kind == "value_error":
        return str(context.get("error", error["msg"]))
    return error["msg"]


def format_errors(exc: ValidationError) -> list[str]:
    return [f"{_path(error['loc'])}: {_message(error)}" for error in exc.errors()]


def parse_machine(data: Any) -> MachineConfig:
    """Sprawdza strukture slownika (bez kontroli spojnosci)."""
    if not isinstance(data, dict):
        raise MachineConfigError(["(korzen): oczekiwano obiektu (klucz: wartosc)"])
    try:
        return MachineConfig.model_validate(data)
    except ValidationError as exc:
        raise MachineConfigError(format_errors(exc)) from exc


def load_machine(source: Path | str) -> MachineConfig:
    """Wczytuje plik machine.yaml; kazdy blad pliku lub struktury to MachineConfigError."""
    path = Path(source)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MachineConfigError([f"nie mozna odczytac pliku {path.name}: {exc.strerror}"]) from exc
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise MachineConfigError([f"niepoprawny YAML w {path.name}: {exc}"]) from exc
    return parse_machine(data)
