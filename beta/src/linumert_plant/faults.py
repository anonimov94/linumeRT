"""Wstrzykiwanie awarii w działający serwer Plant (sesja 024; panel: sesja 023).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 024.

Jedno API dla scenariuszy, testów i panelu: `Faults(server).inject(rodzaj, **parametry)`
i `clear(rodzaj, **parametry)`. Każda awaria ma włączenie i zdjęcie; aktywne awarie zwraca
`active()`. Rodzaje (docs/PLANT.md §7b):

  estop        pętla E-STOP otwarta (przycisk wciśnięty w modelu C: zdarzenie ESTOP,
               reakcja `io.estop.action`, flaga ESTOP_OPEN w ramce)
  drive_fault  awaria napędu `drive`, rodzaj `code` (domyślnie GENERIC, E-4200; drive.h), trwała
               do zdjęcia; po zdjęciu master kasuje ją fault resetem (bit 7 słowa sterującego)
  frame_loss   utrata `percent` % ramek (losowo z ziarnem z plant.yaml; 100 % = zerwane łącze,
               watchdog E-4003); Plant nie odpowiada na utraconą ramkę
  delay        opóźnienie odpowiedzi o `ms` [ms] (pętla UDP `serve`; master widzi spóźnione ramki)
  limit        krańcówka `input` zadziałała (stan elektryczny wg `contact` z machine.yaml)
  axis_jam     zablokowanie osi `axis`: tarcie statyczne i Coulomba jej napędów na maksimum
               szablonu (parametry live, REQ-VD-04); zdjęcie przywraca poprzednie wartości
  vfd_loss     utrata falownika wrzeciona: z sekcją `vfd` brak odpowiedzi Modbus/hy_vfd, bez niej
               awaria wrzeciona (wybieg do zatrzymania)
  atc_sensor   czujnik magazynu `input` zablokowany w stanie `closed` (True/False)
  estop_channel  kanał B E-STOP (`io.inputs.estop_b`) zablokowany w stanie `closed`

Wymuszenia wejść (limit, atc_sensor) nakładane są na `digital_in` jako ostatnie, po modelach
magazynu i pulpicie. Moduł działa poza RT; zmiany robione pod blokadą serwera.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .server import PlantServer

# drive.h: LRT_DRIVE_FAULT_LIST (numer, alarm katalogu)
DRIVE_FAULTS = {"GENERIC": (1, "E-4200"), "FOLLOWING_ERROR": (2, "E-4201"),
                "OVERLOAD": (3, "E-4202"), "OVERCURRENT": (4, "E-4203"),
                "OVERTEMP": (5, "E-4204"), "DC_BUS": (6, "E-4205"),
                "ENCODER_LOST": (7, "E-4206"), "HW_LIMIT": (8, "E-4207"), "STO": (9, "E-4208")}
JAM_PATHS = ("mechanics.friction_static", "mechanics.friction_coulomb")

CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {
    "estop": ("E-STOP: pętla bezpieczeństwa otwarta", ()),
    "drive_fault": ("Awaria napędu", ("drive", "code")),
    "frame_loss": ("Utrata części ramek LRT-NET", ("percent",)),
    "delay": ("Opóźnienie odpowiedzi Plant", ("ms",)),
    "limit": ("Zadziałanie krańcówki", ("input",)),
    "axis_jam": ("Zablokowanie osi", ("axis",)),
    "vfd_loss": ("Utrata falownika wrzeciona", ()),
    "atc_sensor": ("Zablokowany czujnik magazynu", ("input", "closed")),
    "estop_channel": ("E-STOP: kanał B zablokowany (rozbieżność kanałów)", ("closed",)),
}
TARGET = {"drive_fault": "drive", "limit": "input", "axis_jam": "axis", "atc_sensor": "input"}


class FaultError(ValueError):
    """Nieznana awaria albo zły parametr (komunikat po polsku)."""


@dataclass
class FaultState:
    """Stan czytany przez serwer w pętli ramek (bez blokad dłuższych niż odczyt pól)."""

    drop_percent: float = 0.0
    delay_ms: float = 0.0
    forced: dict[int, bool] = field(default_factory=dict)  # bit digital_in → stan elektryczny
    dropped: int = 0
    rng: random.Random = field(default_factory=lambda: random.Random(1))

    def drop(self) -> bool:
        """Czy zgubić tę ramkę (losowanie tylko przy aktywnej awarii: determinizm bez niej)."""
        if self.drop_percent <= 0:
            return False
        if self.drop_percent >= 100 or self.rng.random() * 100 < self.drop_percent:
            self.dropped += 1
            return True
        return False

    def inputs(self) -> tuple[int, int]:
        mask = value = 0
        for bit, closed in self.forced.items():
            mask |= 1 << bit
            value |= int(closed) << bit
        return mask, value


class Faults:
    """API awarii nad `PlantServer` (scenariusze, panel, testy)."""

    def __init__(self, server: PlantServer):
        self.server = server
        self.state: FaultState = server.fault_state
        self._active: dict[tuple[str, str], dict[str, Any]] = {}
        self._jam_saved: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    # ---- opis ----------------------------------------------------------------------------
    @staticmethod
    def catalog() -> list[dict]:
        return [{"kind": k, "desc": d, "params": list(p)} for k, (d, p) in CATALOG.items()]

    def active(self) -> list[dict]:
        with self._lock:
            return [dict(v) for v in self._active.values()]

    def is_active(self, kind: str, target: str = "") -> bool:
        return (kind, target) in self._active

    # ---- pomocnicze ----------------------------------------------------------------------
    def _key(self, kind: str, params: dict) -> tuple[str, str]:
        if kind not in CATALOG:
            raise FaultError(f"nieznana awaria „{kind}” (znane: {', '.join(CATALOG)})")
        name = TARGET.get(kind)
        if name is None:
            return kind, ""
        if not params.get(name):
            raise FaultError(f"{kind}: brak parametru {name}")
        return kind, str(params[name])

    def _input_bit(self, name: str) -> int:
        inputs = self.server.machine.model.inputs
        if name not in inputs:
            raise FaultError(f"nieznane wejście „{name}” (machine.yaml io.inputs: "
                             f"{', '.join(sorted(inputs))})")
        return inputs[name]

    def _limit_contact(self, name: str) -> str:
        cfg = self.server.machine.model.config
        for axis in cfg.axes:
            for sw in (axis.limits.min, axis.limits.max):
                if sw is not None and sw.input == name:
                    return sw.contact
        raise FaultError(f"„{name}” nie jest wejściem krańcówki (axes[].limits)")

    def _atc_sensors(self) -> set[str]:
        """Wejścia czujników magazynu z `toolchanger` (pola sensor*, np. clamp.sensor)."""
        tc = getattr(self.server.machine.model.config, "toolchanger", None)
        found: set[str] = set()

        def walk(node) -> None:
            if isinstance(node, dict):
                for k, v in node.items():
                    if k.startswith("sensor") and isinstance(v, str):
                        found.add(v)
                    else:
                        walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        if tc is not None:
            walk(tc.model_dump())
        return found

    def _drives_of(self, axis: str) -> list[str]:
        drives = self.server.machine.model.joint_drives.get(str(axis).upper())
        if not drives:
            raise FaultError(f"maszyna nie ma osi {axis}")
        return drives

    # ---- włączenie i zdjęcie -------------------------------------------------------------
    def inject(self, kind: str, **params) -> dict:
        key = self._key(kind, params)
        srv = self.server
        with self._lock, srv._lock:
            entry = {"kind": kind, **{k: v for k, v in params.items() if v is not None}}
            m = srv.machine
            if kind == "estop":
                m.set_estop(True)
            elif kind == "drive_fault":
                drive = params["drive"]
                if drive not in srv.drives:
                    raise FaultError(f"nieznany napęd {drive} (znane: {', '.join(srv.drives)})")
                name = str(params.get("code") or "GENERIC").upper()
                if name not in DRIVE_FAULTS:
                    raise FaultError(f"drive_fault: rodzaj {name} — dozwolone "
                                     f"{', '.join(DRIVE_FAULTS)}")
                m.inject_fault(drive, DRIVE_FAULTS[name][0], sticky=True)
                entry.update(code=name, alarm=DRIVE_FAULTS[name][1])
            elif kind == "frame_loss":
                pct = float(params.get("percent", 100))
                if not 0 < pct <= 100:
                    raise FaultError(f"frame_loss: percent {pct} poza (0; 100]")
                self.state.rng.seed(srv.cfg.seed)
                self.state.drop_percent = pct
            elif kind == "delay":
                ms = float(params.get("ms", 0))
                if not 0 < ms <= 10_000:
                    raise FaultError(f"delay: ms {ms} poza (0; 10000]")
                self.state.delay_ms = ms
            elif kind == "limit":
                name = params["input"]
                bit = self._input_bit(name)
                self.state.forced[bit] = self._limit_contact(name) == "NO"  # NC zadziała = 0
            elif kind == "axis_jam":
                saved = {}
                for d in self._drives_of(params["axis"]):
                    if d not in srv.live:
                        raise FaultError(f"axis_jam: napęd {d} bez parametrów live")
                    live = srv.live[d]
                    missing = [p for p in JAM_PATHS if p not in live.params["live"]]
                    if missing:
                        raise FaultError(f"axis_jam: {d} — {', '.join(missing)} nie jest live")
                    saved[d] = {p: live.get(p) for p in JAM_PATHS}
                for d in saved:
                    srv._set_live(d, "mechanics.friction_static", 1000.0)
                    srv._set_live(d, "mechanics.friction_coulomb", 1000.0)
                self._jam_saved[key[1]] = {d: v for d, v in saved.items()}
            elif kind == "vfd_loss":
                if srv.cfg.vfd is not None:
                    srv.vfd_faults.comm_lost = True
                else:
                    from .vfd import FAULT_DRIVE

                    srv.spindle.fault = FAULT_DRIVE
            elif kind == "atc_sensor":
                sensors = self._atc_sensors()
                if params["input"] not in sensors:
                    raise FaultError(f"„{params['input']}” nie jest czujnikiem magazynu "
                                     f"(toolchanger: {', '.join(sorted(sensors)) or 'brak'})")
                bit = self._input_bit(params["input"])
                self.state.forced[bit] = bool(params.get("closed", True))
            elif kind == "estop_channel":
                if srv._estop_b is None:
                    raise FaultError("estop_channel: maszyna bez wejścia estop_b (io.inputs)")
                self.state.forced[srv._estop_b] = bool(params.get("closed", True))
            self._active[key] = entry
            srv._note(f"awaria: {kind} {key[1]}".rstrip())
            return dict(entry)

    def clear(self, kind: str, **params) -> None:
        key = self._key(kind, params)
        srv = self.server
        with self._lock, srv._lock:
            if key not in self._active:
                raise FaultError(f"awaria {kind} {key[1]} nie jest aktywna".replace("  ", " "))
            m = srv.machine
            if kind == "estop":
                m.set_estop(False)
            elif kind == "drive_fault":
                m.clear_fault_cause(params["drive"], DRIVE_FAULTS[
                    self._active[key]["code"]][0])
            elif kind == "frame_loss":
                self.state.drop_percent = 0.0
            elif kind == "delay":
                self.state.delay_ms = 0.0
            elif kind in ("limit", "atc_sensor"):
                self.state.forced.pop(self._input_bit(params["input"]), None)
            elif kind == "estop_channel":
                self.state.forced.pop(srv._estop_b, None)
            elif kind == "axis_jam":
                saved = self._jam_saved.pop(key[1])
                for d, values in saved.items():  # Coulomb przed statycznym (statyczne >= Coulomb)
                    srv._set_live(d, "mechanics.friction_coulomb", values[JAM_PATHS[1]])
                    srv._set_live(d, "mechanics.friction_static", values[JAM_PATHS[0]])
            elif kind == "vfd_loss":
                srv.vfd_faults.comm_lost = False
                srv.spindle.reset_fault()
            del self._active[key]
            srv._note(f"awaria zdjęta: {kind} {key[1]}".rstrip())

    def clear_all(self) -> None:
        for entry in self.active():
            params = {k: v for k, v in entry.items() if k not in ("kind", "alarm")}
            self.clear(entry["kind"], **params)
