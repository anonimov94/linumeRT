"""Szablon napędu wirtualnego: schemat, walidacja zakresów, mapowanie na rdzeń C, fizyka, live.

Model-Author: Claude · sesja 013 (REQ-VD-01, REQ-VD-04).

Szablon (`plant/library/drives/<id>.yaml`) opisuje napęd i jego domyślną mechanikę.
Wszystkie pola są jawne (brak ukrytych wartości domyślnych): ten sam szablon daje ten sam
model. Zakresy z tabeli `PARAMS` egzekwuje `validate_template()`; te same zakresy obowiązują
nadpisania instancji (REQ-VD-02) i zmiany w locie (REQ-VD-04). Plik JSON Schema
`plant/library/drives/drive_template.schema.json` jest generowany z tej tabeli
(`python -m linumert_plant drive schema`); reguły między polami są opisane w README biblioteki.

Jednostki: SI (N·m, kg·m², rad, rad/s, s, V, A); pozycje CiA 402 w impulsach.
NIEZWERYFIKOWANE NA SPRZĘCIE: wartości szablonów są przykładowe.
"""

from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from typing import Any, NamedTuple

TEMPLATE_VERSION_FIELD = "version"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,47}$")

# Typy napędu z REQ-VD-01 i ich odpowiedniki w rdzeniu C (plant/core/drive.h).
# Wrzeciono z falownikiem i oś obrotowa z przekładnią korzystają z modelu serwa CSP
# (wrzeciono: przybliżenie momentowe bez modelu falownika - patrz docs/DECYZJE.md).
TYPE_TO_C = {
    "servo_csp": 0,
    "stepper_open": 1,
    "servo_stepper": 2,
    "rotary_geared": 0,
    "spindle_vfd": 0,
}
STEPPER_TYPES = ("stepper_open", "servo_stepper")
ROTARY_ONLY_TYPES = ("rotary_geared", "spindle_vfd")

# Podzbiór obiektów CiA 402 (REQ-VD-01): wymagane i wszystkie obsługiwane przez rdzeń.
CIA_REQUIRED = (
    "603Fh", "6040h", "6041h", "6060h", "6061h", "6064h", "607Ah", "6065h", "6072h",
    "6098h", "6099h", "609Ah",
)
CIA_SUPPORTED = CIA_REQUIRED + (
    "605Ah", "605Eh", "6066h", "606Ch", "6077h", "6085h", "60B1h", "60B2h",
)

SECTIONS = (
    "motor", "electrical", "controller", "limits", "reactions", "cia402", "mechanics", "stepper",
)
TOP_FIELDS = (
    "id", "version", "based_on", "name", "description", "value_source", "type", "live",
)
U32_MAX = 4294967295


@dataclass(frozen=True)
class Param:
    """Opis jednego parametru szablonu."""

    path: str
    kind: str  # float | int | bool | enum | curve | objects
    lo: float | None = None
    hi: float | None = None
    unit: str = ""
    live: bool = False
    lo_open: bool = False
    options: tuple[Any, ...] = ()
    doc: str = ""

    @property
    def section(self) -> str:
        return self.path.split(".", 1)[0]

    @property
    def key(self) -> str:
        return self.path.split(".", 1)[1]


def _f(path: str, lo: float, hi: float, unit: str, doc: str, *, live: bool = False,
       lo_open: bool = False) -> Param:
    return Param(path, "float", lo, hi, unit, live, lo_open, doc=doc)


def _i(path: str, lo: int, hi: int, unit: str, doc: str, *, live: bool = False) -> Param:
    return Param(path, "int", lo, hi, unit, live, doc=doc)


PARAMS: tuple[Param, ...] = (
    # --- silnik ---
    _f("motor.rated_torque", 0, 1000, "N·m", "moment znamionowy (krokowiec: moment trzymania)",
       lo_open=True),
    _f("motor.peak_torque", 0, 5000, "N·m", "moment szczytowy (>= znamionowy)", lo_open=True),
    _f("motor.peak_time_s", 0, 60, "s", "czas pracy ze szczytem (ochrona I2t); 0 = bez ochrony"),
    _f("motor.rotor_inertia", 1e-8, 10, "kg·m²", "moment bezwładności wirnika", live=True),
    _f("motor.torque_constant", 1e-3, 100, "N·m/A", "stała momentu"),
    _f("motor.rated_current", 0, 500, "A", "prąd znamionowy", lo_open=True),
    _f("motor.peak_current", 0, 2000, "A", "prąd szczytowy (>= znamionowy)", lo_open=True),
    _i("motor.encoder_counts_per_rev", 16, 100_000_000, "imp/obr",
       "rozdzielczość enkodera (krokowiec bez sprzężenia: mikrokroki na obrót)"),
    _f("motor.encoder_noise_counts", 0, 1000, "imp", "szum enkodera, odch. std."),
    Param("motor.torque_curve", "curve", unit="rad/s → N·m",
          doc="krzywa moment–prędkość: [[omega, moment], ...], 2..16 punktów, od omega = 0"),
    Param("motor.brake_present", "bool", doc="hamulec postojowy (model: sesja 014+)"),
    _f("motor.brake_release_ms", 0, 5000, "ms", "czas zwolnienia hamulca"),
    _f("motor.brake_engage_ms", 0, 5000, "ms", "czas zadziałania hamulca"),
    # --- zasilanie ---
    _f("electrical.nominal_voltage", 5, 1000, "V", "napięcie znamionowe zasilania"),
    _f("electrical.supply_voltage", 5, 1500, "V",
       "napięcie bieżące (0,1..1,5 × znamionowe); skaluje krzywą momentu", live=True),
    # --- regulatory ---
    _f("controller.kp_pos", 0, 5000, "1/s", "wzmocnienie położenia"),
    _f("controller.kv", 0, 100, "N·m·s/rad", "wzmocnienie prędkości"),
    _f("controller.ti", 0, 10, "s", "czas całkowania prędkości; 0 = bez całki"),
    _f("controller.kff_vel", 0, 2, "", "udział sprzężenia w przód od prędkości"),
    _f("controller.kff_acc", 0, 2, "", "udział sprzężenia w przód od przyspieszenia"),
    _f("controller.inertia_est", 0, 10, "kg·m²", "estymata J dla FF przyspieszenia"),
    _f("controller.vel_filter_hz", 0, 5000, "Hz", "filtr prędkości mierzonej", lo_open=True),
    _f("controller.ff_filter_hz", 0, 5000, "Hz", "filtr pochodnych pozycji zadanej",
       lo_open=True),
    _f("controller.max_speed", 0, 5000, "rad/s", "ograniczenie prędkości zadanej",
       lo_open=True),
    # --- limity ---
    _i("limits.torque_limit_permille", 0, 10000, "‰",
       "domyślna wartość 6072h (promile znamionowego)", live=True),
    _i("limits.following_window", 1, U32_MAX, "imp", "okno błędu nadążania 6065h"),
    _i("limits.following_window_ms", 0, 10000, "ms", "czas okna 6066h"),
    _i("limits.quick_stop_decel", 1, U32_MAX, "imp/s²", "hamowanie quick stop 6085h"),
    _f("limits.standstill_speed", 0, 10, "rad/s", "próg zatrzymania", lo_open=True),
    _f("limits.boot_time_s", 0, 30, "s", "czas rozruchu napędu"),
    # --- reakcje na błędy ---
    Param("reactions.quick_stop_option", "enum", options=(1, 2),
          doc="605Ah: 1 = wyłącz napęd, 2 = rampa i wyłączenie"),
    Param("reactions.fault_reaction_option", "enum", options=(0, 2),
          doc="605Eh: 0 = wyłącz napęd, 2 = rampa quick stop"),
    Param("reactions.brake_on_fault", "bool", doc="załącz hamulec po awarii"),
    # --- CiA 402 ---
    Param("cia402.objects", "objects", doc="obsługiwane obiekty CiA 402 (podzbiór wymagany)"),
    _i("cia402.homing_method", -128, 127, "", "6098h"),
    _i("cia402.homing_speed_switch", 0, U32_MAX, "imp/s", "6099h:1"),
    _i("cia402.homing_speed_zero", 0, U32_MAX, "imp/s", "6099h:2"),
    _i("cia402.homing_accel", 0, U32_MAX, "imp/s²", "609Ah"),
    # --- mechanika (domyślna; w maszynie może być nadpisana instancją) ---
    Param("mechanics.kind", "enum", options=("linear", "rotary"),
          doc="oś liniowa (load w kg, ratio w m/rad) albo obrotowa (load w kg·m², ratio rad/rad)"),
    _f("mechanics.load", 0, 1e6, "kg | kg·m²", "masa albo moment bezwładności obciążenia",
       live=True),
    _f("mechanics.ratio", 1e-7, 1000, "m/rad | rad/rad", "przemieszczenie obciążenia na rad wału"),
    _f("mechanics.j_screw", 0, 10, "kg·m²", "śruba/sprzęgło/przekładnia po stronie silnika",
       live=True),
    _f("mechanics.friction_coulomb", 0, 1000, "N·m", "tarcie suche na wale", live=True),
    _f("mechanics.friction_static", 0, 1000, "N·m", "tarcie statyczne (>= Coulomba)", live=True),
    _f("mechanics.friction_viscous", 0, 1000, "N·m·s/rad", "tarcie lepkie", live=True),
    _f("mechanics.backlash", 0, 0.1, "m | rad", "luz całkowity", live=True),
    _f("mechanics.contact_stiffness", 0, 1e7, "N·m/rad",
       "sztywność połączenia na wale; 0 = domyślna rdzenia"),
    _f("mechanics.gravity_force", -1e6, 1e6, "N | N·m", "stała siła zewnętrzna na obciążenie"),
    # --- krokowiec (tylko dla typów krokowych) ---
    _i("stepper.full_steps_per_rev", 4, 1000, "", "pełne kroki na obrót (wielokrotność 4)"),
    _f("stepper.damping_ratio", 0, 2, "", "względne tłumienie wirnika"),
)

PARAM_BY_PATH = {p.path: p for p in PARAMS}
LIVE_CAPABLE = tuple(p.path for p in PARAMS if p.live)
STEPPER_PARAMS = tuple(p.path for p in PARAMS if p.section == "stepper")

# Odwzorowanie parametrów live na rdzeń C (lrt_live_param z plant/core/live.h): parametry osi
# idą do lrt_axis_set_live(), limit momentu do lrt_drive_set_live() (6072h, z dziennikiem).
LIVE_TO_C: dict[str, str] = {
    "motor.rotor_inertia": "LRT_LIVE_J_MOTOR",
    "mechanics.load": "LRT_LIVE_LOAD",
    "mechanics.j_screw": "LRT_LIVE_J_SCREW",
    "mechanics.friction_coulomb": "LRT_LIVE_FRICTION_COULOMB",
    "mechanics.friction_static": "LRT_LIVE_FRICTION_STATIC",
    "mechanics.friction_viscous": "LRT_LIVE_FRICTION_VISCOUS",
    "mechanics.backlash": "LRT_LIVE_BACKLASH",
    "electrical.supply_voltage": "LRT_LIVE_SUPPLY_SCALE",
    "limits.torque_limit_permille": "LRT_LIVE_TORQUE_LIMIT",
}


class Issue(NamedTuple):
    """Jeden błąd walidacji: ścieżka pola i komunikat po polsku."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


class TemplateError(ValueError):
    """Błędy szablonu, instancji albo zmiany w locie (wszystkie naraz, ze ścieżkami pól)."""

    def __init__(self, issues: list[Issue] | Issue) -> None:
        self.issues: list[Issue] = [issues] if isinstance(issues, Issue) else list(issues)
        super().__init__("\n".join(str(i) for i in self.issues))


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _num_text(value: float) -> str:
    return f"{value:g}"


def _range_text(p: Param) -> str:
    lo = "(" if p.lo_open else "["
    unit = f" {p.unit}" if p.unit else ""
    return f"{lo}{_num_text(p.lo or 0)}; {_num_text(p.hi or 0)}]{unit}"


def _not_number_message(value: Any) -> str:
    if isinstance(value, str):
        return (f"wartość „{value}” jest tekstem, nie liczbą (zapisz np. 0.0001 albo 1.0e-4; "
                "„1e-4” bez kropki YAML czyta jako tekst)")
    return f"wymagana liczba, podano {type(value).__name__}"


def _check_value(p: Param, value: Any, path: str, issues: list[Issue]) -> Any:
    """Waliduje jedną wartość parametru; zwraca wartość znormalizowaną albo None przy błędzie."""
    if p.kind in ("float", "int"):
        if not _is_number(value):
            issues.append(Issue(path, _not_number_message(value)))
            return None
        if p.kind == "int" and (isinstance(value, float) and not value.is_integer()):
            issues.append(Issue(path, f"wymagana liczba całkowita, podano {value}"))
            return None
        if p.lo is not None and p.hi is not None:
            below = value <= p.lo if p.lo_open else value < p.lo
            if below or value > p.hi:
                issues.append(Issue(path, f"wartość {_num_text(value)} poza zakresem "
                                          f"{_range_text(p)}"))
                return None
        return float(value) if p.kind == "float" else int(value)
    if p.kind == "bool":
        if not isinstance(value, bool):
            issues.append(Issue(path, "wymagana wartość logiczna (true/false)"))
            return None
        return value
    if p.kind == "enum":
        if isinstance(value, bool) or value not in p.options:
            opts = ", ".join(str(o) for o in p.options)
            issues.append(Issue(path, f"niedozwolona wartość „{value}”; dozwolone: {opts}"))
            return None
        return value
    if p.kind == "curve":
        return _check_curve(value, path, issues)
    if p.kind == "objects":
        return _check_objects(value, path, issues)
    raise AssertionError(p.kind)  # pragma: no cover


def _check_curve(value: Any, path: str, issues: list[Issue]) -> list[list[float]] | None:
    if not isinstance(value, list) or not 2 <= len(value) <= 16:
        issues.append(Issue(path, "krzywa musi być listą 2..16 punktów [omega, moment]"))
        return None
    points: list[list[float]] = []
    ok = True
    for n, pt in enumerate(value):
        where = f"{path}[{n}]"
        if not (isinstance(pt, list) and len(pt) == 2 and all(_is_number(x) for x in pt)):
            issues.append(Issue(where, "punkt krzywej musi być parą liczb [omega, moment]"))
            ok = False
            continue
        omega, torque = float(pt[0]), float(pt[1])
        if omega < 0 or torque < 0:
            issues.append(Issue(where, "omega i moment nie mogą być ujemne"))
            ok = False
        if points and omega <= points[-1][0]:
            issues.append(Issue(where, "omega musi rosnąć (omega <= omega poprzedniego punktu)"))
            ok = False
        points.append([omega, torque])
    if ok and points[0][0] != 0:
        issues.append(Issue(f"{path}[0]", "krzywa musi zaczynać się od omega = 0"))
        ok = False
    return points if ok else None


def _check_objects(value: Any, path: str, issues: list[Issue]) -> list[str] | None:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        issues.append(Issue(path, "wymagana lista nazw obiektów, np. [\"6040h\", \"6041h\"]"))
        return None
    ok = True
    unknown = sorted(set(value) - set(CIA_SUPPORTED))
    if unknown:
        issues.append(Issue(path, f"nieobsługiwane obiekty: {', '.join(unknown)}"))
        ok = False
    missing = [o for o in CIA_REQUIRED if o not in value]
    if missing:
        issues.append(Issue(path, f"brak wymaganych obiektów: {', '.join(missing)}"))
        ok = False
    if len(set(value)) != len(value):
        issues.append(Issue(path, "powtórzone obiekty"))
        ok = False
    return list(value) if ok else None


def _normalize(data: Any, issues: list[Issue]) -> dict[str, Any]:
    """Sprawdza strukturę i pojedyncze wartości; zbiera wszystkie błędy."""
    out: dict[str, Any] = {}
    if not isinstance(data, dict):
        issues.append(Issue("", "szablon musi być słownikiem YAML (klucz: wartość)"))
        return out
    for key in data:
        if key == "real":
            # Napęd rzeczywisty (REQ-VD-06, sesja 061): opcjonalna sekcja, osobny walidator.
            from .drive_real import check_real

            real = check_real(data["real"], data.get("type"), issues, Issue)
            if real is not None:
                out["real"] = real
        elif key not in TOP_FIELDS and key not in SECTIONS:
            issues.append(Issue(str(key), "nieznane pole"))
    _check_top(data, out, issues)
    for section in SECTIONS:
        if section not in data:
            continue
        raw = data[section]
        if not isinstance(raw, dict):
            issues.append(Issue(section, "sekcja musi być słownikiem"))
            continue
        out[section] = {}
        known = {p.key for p in PARAMS if p.section == section}
        for key in raw:
            if key not in known:
                issues.append(Issue(f"{section}.{key}", "nieznane pole"))
    for p in PARAMS:
        sec = data.get(p.section)
        if not isinstance(sec, dict):
            continue
        if p.key not in sec:
            if p.section != "stepper":
                issues.append(Issue(p.path, "brak wymaganego pola"))
            continue
        value = _check_value(p, sec[p.key], p.path, issues)
        if value is not None:
            out.setdefault(p.section, {})[p.key] = value
    for section in SECTIONS:
        if section != "stepper" and section not in data:
            issues.append(Issue(section, "brak wymaganej sekcji"))
    return out


def _check_top(data: dict[str, Any], out: dict[str, Any], issues: list[Issue]) -> None:
    tid = data.get("id")
    if not isinstance(tid, str) or not ID_PATTERN.match(tid):
        issues.append(Issue("id", "identyfikator: małe litery, cyfry i _, od litery, 2..48 znaków"))
    else:
        out["id"] = tid
    ver = data.get("version")
    if isinstance(ver, bool) or not isinstance(ver, int) or ver < 1:
        issues.append(Issue("version", "wersja szablonu: liczba całkowita >= 1"))
    else:
        out["version"] = ver
    based = data.get("based_on")
    if based is not None and (not isinstance(based, str) or not ID_PATTERN.match(based)):
        issues.append(Issue("based_on", "identyfikator szablonu źródłowego albo null"))
    else:
        out["based_on"] = based
    for key in ("name", "description", "value_source"):
        val = data.get(key)
        if not isinstance(val, str) or not val.strip():
            issues.append(Issue(key, "wymagany niepusty tekst"))
        else:
            out[key] = val.strip()
    typ = data.get("type")
    if typ not in TYPE_TO_C:
        issues.append(Issue("type", f"nieznany typ „{typ}”; dozwolone: {', '.join(TYPE_TO_C)}"))
    else:
        out["type"] = typ
    live = data.get("live")
    if not isinstance(live, list) or not all(isinstance(x, str) for x in live):
        issues.append(Issue("live", "lista ścieżek parametrów live (może być pusta)"))
        return
    ok = True
    for path in live:
        if path not in LIVE_CAPABLE:
            issues.append(Issue("live", f"parametr „{path}” nie może być zmieniany w locie; "
                                        f"dozwolone: {', '.join(LIVE_CAPABLE)}"))
            ok = False
    if len(set(live)) != len(live):
        issues.append(Issue("live", "powtórzone ścieżki"))
        ok = False
    if ok:
        out["live"] = list(live)


def _cross_checks(t: dict[str, Any], issues: list[Issue]) -> None:
    """Reguły między polami; wywoływane tylko dla szablonu bez błędów podstawowych."""
    m, e, lim, mech = t["motor"], t["electrical"], t["limits"], t["mechanics"]
    typ = t["type"]
    if m["peak_torque"] < m["rated_torque"]:
        issues.append(Issue("motor.peak_torque", "moment szczytowy nie może być mniejszy od "
                                                 "znamionowego"))
    if m["peak_current"] < m["rated_current"]:
        issues.append(Issue("motor.peak_current", "prąd szczytowy nie może być mniejszy od "
                                                  "znamionowego"))
    if abs(m["torque_constant"] * m["rated_current"] - m["rated_torque"]) > 0.1 * m["rated_torque"]:
        issues.append(Issue("motor.torque_constant",
                            "niespójne: stała momentu × prąd znamionowy różni się od momentu "
                            "znamionowego o więcej niż 10 %"))
    curve = m["torque_curve"]
    curve_max = max(p[1] for p in curve)
    if curve[0][1] < m["rated_torque"] * 0.999 or curve_max > m["peak_torque"] * 1.001:
        issues.append(Issue("motor.torque_curve",
                            "moment przy omega = 0 musi być >= znamionowego, a żaden punkt nie "
                            "może przekraczać momentu szczytowego"))
    limit_max = (int(m["peak_torque"] / m["rated_torque"] * 1000)
                 if m["peak_torque"] > m["rated_torque"] else 1000)
    if lim["torque_limit_permille"] > limit_max:
        issues.append(Issue("limits.torque_limit_permille",
                            f"limit momentu {lim['torque_limit_permille']} ‰ przekracza moment "
                            f"szczytowy ({limit_max} ‰ znamionowego)"))
    nom = e["nominal_voltage"]
    if not 0.1 * nom <= e["supply_voltage"] <= 1.5 * nom:
        issues.append(Issue("electrical.supply_voltage",
                            f"napięcie {_num_text(e['supply_voltage'])} V poza 0,1..1,5 × "
                            f"znamionowego ({_num_text(nom)} V)"))
    if mech["friction_static"] < mech["friction_coulomb"]:
        issues.append(Issue("mechanics.friction_static",
                            "tarcie statyczne nie może być mniejsze od tarcia Coulomba"))
    if mech["backlash"] > 0 and mech["load"] <= 0:
        issues.append(Issue("mechanics.load", "model z luzem wymaga masy (load) większej od zera"))
    if typ in ROTARY_ONLY_TYPES and mech["kind"] != "rotary":
        issues.append(Issue("mechanics.kind", f"typ „{typ}” wymaga osi obrotowej (rotary)"))
    if typ in STEPPER_TYPES:
        _check_stepper(t, issues)
    elif "stepper" in t:
        issues.append(Issue("stepper", f"sekcja dotyczy tylko krokowców, a typ to „{typ}”"))


def _check_stepper(t: dict[str, Any], issues: list[Issue]) -> None:
    st = t.get("stepper")
    if not isinstance(st, dict) or set(st) != {"full_steps_per_rev", "damping_ratio"}:
        issues.append(Issue("stepper", "typ krokowy wymaga sekcji stepper z polami "
                                       "full_steps_per_rev i damping_ratio"))
        return
    if st["full_steps_per_rev"] % 4 != 0:
        issues.append(Issue("stepper.full_steps_per_rev", "liczba pełnych kroków musi być "
                                                          "wielokrotnością 4"))
    counts = t["motor"]["encoder_counts_per_rev"]
    if t["type"] == "stepper_open" and counts % st["full_steps_per_rev"] != 0:
        issues.append(Issue("motor.encoder_counts_per_rev",
                            "dla krokowca bez sprzężenia liczba mikrokroków na obrót musi być "
                            "wielokrotnością pełnych kroków"))


def validate_template(data: Any) -> dict[str, Any]:
    """Waliduje szablon (zakresy, typy, reguły między polami); zwraca znormalizowaną kopię.

    Zgłasza TemplateError ze wszystkimi znalezionymi błędami (ścieżka pola + komunikat).
    """
    issues: list[Issue] = []
    out = _normalize(data, issues)
    if not issues:
        _cross_checks(out, issues)
    if issues:
        raise TemplateError(issues)
    return out


def template_issues(data: Any) -> list[Issue]:
    """Jak validate_template(), ale zwraca listę błędów zamiast wyjątku."""
    try:
        validate_template(data)
    except TemplateError as exc:
        return exc.issues
    return []


# ----------------------------------------------------------------------------------------
# Mapowanie na rdzeń C
# ----------------------------------------------------------------------------------------

DEFAULT_CONTACT_STIFFNESS = 1000.0  # LRT_AXIS_DEFAULT_CONTACT_STIFFNESS


def to_c_params(tpl: dict[str, Any]) -> dict[str, Any]:
    """Mapuje (zwalidowany) szablon na pola `lrt_drive_params` i `lrt_axis_params`."""
    m, c, lim, rea, cia, mech = (tpl[k] for k in
                                 ("motor", "controller", "limits", "reactions", "cia402",
                                  "mechanics"))
    stepper = tpl.get("stepper", {"full_steps_per_rev": 200, "damping_ratio": 0.2})
    stiffness = mech["contact_stiffness"]
    if stiffness == 0 and "mechanics.backlash" in tpl["live"]:
        stiffness = DEFAULT_CONTACT_STIFFNESS  # model dwuczłonowy aktywny od startu
    drive = {
        "counts_per_rev": m["encoder_counts_per_rev"],
        "enc_noise_counts": m["encoder_noise_counts"],
        "rated_torque": m["rated_torque"],
        "peak_torque": m["peak_torque"],
        "peak_time_s": m["peak_time_s"],
        "torque_limit_permille": lim["torque_limit_permille"],
        "kp_pos": c["kp_pos"],
        "kv": c["kv"],
        "ti": c["ti"],
        "kff_vel": c["kff_vel"],
        "kff_acc": c["kff_acc"],
        "inertia_est": c["inertia_est"],
        "vel_filter_hz": c["vel_filter_hz"],
        "ff_filter_hz": c["ff_filter_hz"],
        "max_speed": c["max_speed"],
        "following_window": lim["following_window"],
        "following_window_ms": lim["following_window_ms"],
        "quick_stop_decel": lim["quick_stop_decel"],
        "quick_stop_option": rea["quick_stop_option"],
        "fault_reaction_option": rea["fault_reaction_option"],
        "standstill_speed": lim["standstill_speed"],
        "boot_time_s": lim["boot_time_s"],
        "full_steps_per_rev": stepper["full_steps_per_rev"],
        "stepper_damping_ratio": stepper["damping_ratio"],
        "homing_method": cia["homing_method"],
        "homing_speed_switch": cia["homing_speed_switch"],
        "homing_speed_zero": cia["homing_speed_zero"],
        "homing_accel": cia["homing_accel"],
    }
    axis = {
        "kind": 0 if mech["kind"] == "linear" else 1,
        "j_motor": m["rotor_inertia"],
        "j_screw": mech["j_screw"],
        "load": mech["load"],
        "ratio": mech["ratio"],
        "friction_coulomb": mech["friction_coulomb"],
        "friction_static": mech["friction_static"],
        "friction_viscous": mech["friction_viscous"],
        "gravity_force": mech["gravity_force"],
        "backlash": mech["backlash"],
        "stiffness": stiffness,
    }
    return {"type": TYPE_TO_C[tpl["type"]], "drive": drive, "axis": axis,
            "curve": [list(p) for p in m["torque_curve"]]}


def c_check_input(tpl: dict[str, Any]) -> str:
    """Tekst wejściowy dla `plant/core/build/lrt_check_params` (walidatory rdzenia C)."""
    mapped = to_c_params(tpl)
    lines = [f"type {mapped['type']}"]
    lines += [f"drive.{k} {v!r}" for k, v in mapped["drive"].items()]
    lines += [f"axis.{k} {v!r}" for k, v in mapped["axis"].items()]
    lines += [f"curve {o!r} {t!r}" for o, t in mapped["curve"]]
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------------------
# Fizyka szablonu (REQ-VD-01)
# ----------------------------------------------------------------------------------------


def total_inertia(tpl: dict[str, Any], load: float | None = None) -> float:
    """Bezwładność zastępcza na wale silnika [kg·m²]: J_wirnika + J_śruby + load·ratio²."""
    mech = tpl["mechanics"]
    load_value = mech["load"] if load is None else load
    return tpl["motor"]["rotor_inertia"] + mech["j_screw"] + load_value * mech["ratio"] ** 2


def available_torque(tpl: dict[str, Any], omega: float = 0.0, supply_scale: float = 1.0) -> float:
    """Moment dostępny z krzywej przy prędkości omega [rad/s] (interpolacja liniowa)."""
    curve = tpl["motor"]["torque_curve"]
    w = abs(omega)
    if w <= curve[0][0]:
        return curve[0][1] * supply_scale
    for (w0, t0), (w1, t1) in zip(curve, curve[1:], strict=False):
        if w <= w1:
            return (t0 + (w - w0) / (w1 - w0) * (t1 - t0)) * supply_scale
    return 0.0


def max_acceleration(tpl: dict[str, Any], *, omega: float = 0.0, load: float | None = None,
                     supply_scale: float = 1.0) -> float:
    """Największe przyspieszenie obciążenia [m/s² albo rad/s²] bez tarcia i grawitacji.

    a = (moment dostępny / J_zastępcze) · ratio — bezwładność rośnie z masą, więc przyspieszenie
    maleje (REQ-VD-01, test_drive_template_physics).
    """
    torque = available_torque(tpl, omega, supply_scale)
    return torque / total_inertia(tpl, load) * tpl["mechanics"]["ratio"]


# ----------------------------------------------------------------------------------------
# Zmiany w locie z dziennikiem (REQ-VD-04)
# ----------------------------------------------------------------------------------------


class ChangeRecord(NamedTuple):
    """Wpis dziennika zmian parametru w locie."""

    t: float
    path: str
    old: Any
    new: Any


class LiveParams:
    """Parametry napędu z możliwością zmiany w trakcie pracy (`live:` z szablonu).

    Zmiana jest walidowana tymi samymi zakresami co szablon; błędna nie zmienia stanu ani
    dziennika. Dziennik zawiera czas modelu `t` podany przez wywołującego (determinizm).
    Orkiestrator przekazuje zmianę do rdzenia C przez `c_command()` (lrt_axis_set_live albo
    lrt_drive_od_write 6072h).
    """

    def __init__(self, params: dict[str, Any]) -> None:
        self.params: dict[str, Any] = validate_template(copy.deepcopy(params))
        self.log: list[ChangeRecord] = []

    def get(self, path: str) -> Any:
        section, key = path.split(".", 1)
        return self.params[section][key]

    def set(self, path: str, value: Any, *, t: float) -> ChangeRecord:
        if path not in self.params["live"]:
            raise TemplateError(Issue(path, "parametr nie jest oznaczony jako live w tym "
                                            "szablonie (zmiana wymaga przeładowania modelu)"))
        if not _is_number(t) or t < 0:
            raise TemplateError(Issue("t", "czas zmiany musi być liczbą >= 0"))
        if self.log and t < self.log[-1].t:
            raise TemplateError(Issue("t", "czas zmiany nie może cofać się względem poprzedniej"))
        candidate = copy.deepcopy(self.params)
        section, key = path.split(".", 1)
        candidate[section][key] = value
        try:
            candidate = validate_template(candidate)
        except TemplateError as exc:
            raise TemplateError([Issue(i.path or path, i.message) for i in exc.issues]) from None
        record = ChangeRecord(float(t), path, self.get(path), candidate[section][key])
        self.params = candidate
        self.log.append(record)
        return record

    def c_command(self, path: str, value: Any) -> tuple[str, float]:
        """Polecenie dla rdzenia C: ("LRT_LIVE_LOAD", 120.0), ("LRT_LIVE_TORQUE_LIMIT", 800.0)."""
        target = LIVE_TO_C[path]
        if target == "LRT_LIVE_SUPPLY_SCALE":
            return target, float(value) / self.params["electrical"]["nominal_voltage"]
        return target, float(value)

    def log_as_dicts(self) -> list[dict[str, Any]]:
        return [r._asdict() for r in self.log]


# ----------------------------------------------------------------------------------------
# JSON Schema (generowany z tabeli PARAMS)
# ----------------------------------------------------------------------------------------


def _param_schema(p: Param) -> dict[str, Any]:
    desc = f"{p.doc}" + (f" [{p.unit}]" if p.unit else "")
    if p.kind in ("float", "int"):
        schema: dict[str, Any] = {"type": "number" if p.kind == "float" else "integer"}
        if p.lo_open:
            schema["exclusiveMinimum"] = p.lo
        else:
            schema["minimum"] = p.lo
        schema["maximum"] = p.hi
    elif p.kind == "bool":
        schema = {"type": "boolean"}
    elif p.kind == "enum":
        schema = {"enum": list(p.options)}
    elif p.kind == "curve":
        schema = {
            "type": "array", "minItems": 2, "maxItems": 16,
            "items": {"type": "array", "minItems": 2, "maxItems": 2,
                      "items": {"type": "number", "minimum": 0}},
        }
    else:
        schema = {"type": "array", "items": {"enum": list(CIA_SUPPORTED)},
                  "contains": {"enum": list(CIA_REQUIRED)}, "uniqueItems": True}
    schema["description"] = desc
    if p.live:
        schema["x-live"] = True
    return schema


def json_schema() -> dict[str, Any]:
    """JSON Schema (2020-12) szablonu napędu; reguły między polami: README biblioteki."""
    props: dict[str, Any] = {
        "id": {"type": "string", "pattern": ID_PATTERN.pattern},
        "version": {"type": "integer", "minimum": 1},
        "based_on": {"type": ["string", "null"], "pattern": ID_PATTERN.pattern},
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string", "minLength": 1},
        "value_source": {"type": "string", "minLength": 1},
        "type": {"enum": list(TYPE_TO_C)},
        "live": {"type": "array", "items": {"enum": list(LIVE_CAPABLE)}, "uniqueItems": True},
    }
    required = list(TOP_FIELDS)
    for section in SECTIONS:
        sec_props = {p.key: _param_schema(p) for p in PARAMS if p.section == section}
        props[section] = {"type": "object", "properties": sec_props,
                          "required": list(sec_props), "additionalProperties": False}
        if section != "stepper":
            required.append(section)
    from .drive_real import real_schema

    props["real"] = real_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/anonimov94/linumeRT/plant/library/drives/drive_template",
        "title": "Szablon napędu wirtualnego linumeRT",
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }
