"""Wiązanie ctypes z rdzeniem C Plant (`plant/core/build/libplant_core.so`).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 014.

Rdzeń konfiguruje się kluczami `nazwa wartość` (`lrt_machine_cfg_set`), więc po stronie Pythona
nie ma kopii układu struktur C — tylko bufory o rozmiarze zwracanym przez bibliotekę.
Jednostki API tej klasy są jednostkami `machine.yaml` (mm, stopnie, s); przeliczenie na SI
robi `MachineModel.unit()`.

Biblioteka powstaje przez `make -C plant/core shared` (Linux; w Windows przez WSL).
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
from pathlib import Path

from linumert.machine.schema import MachineConfigError

from .build_machine import MachineModel

ROOT = Path(__file__).resolve().parents[3]
CORE_DIR = ROOT / "plant" / "core"
DEFAULT_LIB = CORE_DIR / "build" / "libplant_core.so"

# Zdarzenia (machine.h: LRT_MACHINE_EV_*); nazwy jak w docs/PLANT.md.
EVENTS = {
    "CRASH_HARDSTOP": 1 << 0,
    "LIMIT_TRIP": 1 << 1,
    "GANTRY_SKEW": 1 << 2,
    "ESTOP": 1 << 3,
    "PROBE": 1 << 4,
    "DRIVE_FAULT": 1 << 5,
    "HOME_SENSOR": 1 << 6,
}
DRIVE_STATES = ("NOT_READY", "SWITCH_ON_DISABLED", "READY_TO_SWITCH_ON", "SWITCHED_ON",
                "OPERATION_ENABLED", "QUICK_STOP_ACTIVE", "FAULT_REACTION_ACTIVE", "FAULT")
CW_SHUTDOWN, CW_SWITCH_ON, CW_ENABLE = 0x0006, 0x0007, 0x000F
ERR_DRIVE, ERR_MECH, ERR_JOINT, ERR_LINK, ERR_SWITCH, ERR_IO, ERR_STEP = (
    -5, -6, -7, -8, -9, -10, -13)


class PlantCoreUnavailable(RuntimeError):
    """Brak biblioteki rdzenia C i brak możliwości jej zbudowania (np. Windows bez WSL)."""


def build_library() -> Path:
    """Buduje `libplant_core.so` (`make -C plant/core shared`); zwraca ścieżkę."""
    if shutil.which("make") is None or (shutil.which("cc") is None and shutil.which("gcc") is None):
        raise PlantCoreUnavailable("brak make i kompilatora C — zbuduj rdzeń w Linuksie/WSL")
    result = subprocess.run(["make", "-s", "-C", str(CORE_DIR), "shared"], capture_output=True,
                            text=True, timeout=600, check=False)
    if result.returncode != 0:
        raise PlantCoreUnavailable(f"budowa rdzenia C nie powiodła się:\n{result.stderr}")
    return DEFAULT_LIB


def _signatures(lib: ctypes.CDLL) -> ctypes.CDLL:
    vp, i, d, c = ctypes.c_void_p, ctypes.c_int, ctypes.c_double, ctypes.c_char_p
    u32 = ctypes.c_uint32
    table = {
        "lrt_machine_cfg_size": ([], ctypes.c_ulong),
        "lrt_machine_size": ([], ctypes.c_ulong),
        "lrt_machine_cfg_init": ([vp], None),
        "lrt_machine_cfg_set": ([vp, c, d], i),
        "lrt_machine_cfg_curve": ([vp, i, d, d], i),
        "lrt_machine_init": ([vp, vp], i),
        "lrt_machine_step": ([vp, d], i),
        "lrt_machine_strerror": ([i], c),
        "lrt_machine_set_controlword": ([vp, i, ctypes.c_uint16], i),
        "lrt_machine_set_target": ([vp, i, ctypes.c_int32], i),
        "lrt_machine_set_joint_target": ([vp, i, d], i),
        "lrt_machine_counts_for": ([vp, i, d], ctypes.c_int32),
        "lrt_machine_set_outputs": ([vp, u32], None),
        "lrt_machine_set_estop": ([vp, i], None),
        "lrt_machine_set_tool_length": ([vp, d], i),
        "lrt_machine_set_joint_position": ([vp, i, d], i),
        "lrt_machine_set_drive_position": ([vp, i, d], i),
        "lrt_machine_set_live": ([vp, i, i, d], i),
        "lrt_machine_inputs": ([vp], u32),
        "lrt_machine_events": ([vp], ctypes.c_uint),
        "lrt_machine_joint_events": ([vp, i], ctypes.c_uint),
        "lrt_machine_clear_events": ([vp], None),
        "lrt_machine_joint_position": ([vp, i], d),
        "lrt_machine_joint_velocity": ([vp, i], d),
        "lrt_machine_joint_skew": ([vp, i], d),
        "lrt_machine_impact_speed": ([vp, i], d),
        "lrt_machine_drive_position": ([vp, i], d),
        "lrt_machine_index_count": ([vp, i], ctypes.c_long),
        "lrt_machine_tool_tip": ([vp, i, ctypes.POINTER(d)], i),
        "lrt_machine_time": ([vp], d),
        "lrt_machine_drive": ([vp, i], vp),
        "lrt_machine_err_index": ([vp], i),
        "lrt_machine_err_detail": ([vp], i),
        "lrt_drive_get_state": ([vp], i),
        "lrt_drive_error_code": ([vp], ctypes.c_uint16),
        "lrt_drive_position_actual": ([vp], ctypes.c_int32),
        "lrt_drive_inject_fault": ([vp, i, i], i),
        "lrt_drive_strerror": ([i], c),
        "lrt_axis_strerror": ([i], c),
    }
    for name, (args, res) in table.items():
        fn = getattr(lib, name)
        fn.argtypes = args
        fn.restype = res
    return lib


_LIB: ctypes.CDLL | None = None


def load_library(path: Path | None = None, build: bool = True) -> ctypes.CDLL:
    """Ładuje bibliotekę rdzenia (zmienna LINUMERT_PLANT_LIB albo plant/core/build)."""
    global _LIB
    if _LIB is not None and path is None:
        return _LIB
    lib_path = Path(path or os.environ.get("LINUMERT_PLANT_LIB", DEFAULT_LIB))
    if build and path is None and "LINUMERT_PLANT_LIB" not in os.environ:
        lib_path = build_library()  # make przebudowuje tylko zmienione pliki
    if not lib_path.exists():
        raise PlantCoreUnavailable(f"brak biblioteki rdzenia {lib_path}")
    try:
        lib = _signatures(ctypes.CDLL(str(lib_path)))
    except OSError as exc:
        raise PlantCoreUnavailable(f"nie można załadować {lib_path}: {exc}") from exc
    if path is None:
        _LIB = lib
    return lib


class PlantMachine:
    """Uruchomiona wirtualna obrabiarka (rdzeń C) zbudowana z `MachineModel`."""

    def __init__(self, model: MachineModel, lib: ctypes.CDLL | None = None):
        self.model = model
        self.lib = lib or load_library()
        self._cfg = ctypes.create_string_buffer(self.lib.lrt_machine_cfg_size())
        self._m = ctypes.create_string_buffer(self.lib.lrt_machine_size())
        self.lib.lrt_machine_cfg_init(self._cfg)
        errors = []
        for key, value in model.settings:
            rc = self.lib.lrt_machine_cfg_set(self._cfg, key.encode(), value)
            if rc != 0:
                errors.append(f"{key} = {value}: {self._strerror(rc)}")
        for drive, points in model.curves.items():
            for omega, torque in points:
                rc = self.lib.lrt_machine_cfg_curve(self._cfg, drive, omega, torque)
                if rc != 0:
                    errors.append(f"krzywa napędu {model.drives[drive]}: {self._strerror(rc)}")
        if errors:
            raise MachineConfigError(errors)
        rc = self.lib.lrt_machine_init(self._m, self._cfg)
        if rc != 0:
            raise MachineConfigError([self._init_error(rc)])
        self._joint = {letter: j for j, letter in enumerate(model.joints)}
        self._drive = {name: i for i, name in enumerate(model.drives)}

    # ---- błędy -----------------------------------------------------------------------
    def _strerror(self, rc: int) -> str:
        return self.lib.lrt_machine_strerror(rc).decode()

    def _init_error(self, rc: int) -> str:
        index = self.lib.lrt_machine_err_index(self._m)
        detail = self.lib.lrt_machine_err_detail(self._m)
        text = self._strerror(rc)
        names = {ERR_DRIVE: self.model.drives, ERR_MECH: self.model.drives,
                 ERR_JOINT: self.model.joints, ERR_LINK: self.model.links}
        where = ""
        if rc in names and 0 <= index < len(names[rc]):
            where = f" ({names[rc][index]})"
        if rc == ERR_DRIVE:
            text += ": " + self.lib.lrt_drive_strerror(detail).decode()
        elif rc == ERR_MECH:
            text += ": " + self.lib.lrt_axis_strerror(detail).decode()
        elif rc == ERR_IO:
            where = f" (wejście {index})"
        return f"rdzeń C: {text}{where}"

    def _j(self, letter: str) -> int:
        try:
            return self._joint[letter]
        except KeyError:
            raise KeyError(f"maszyna {self.model.name} nie ma osi {letter}") from None

    def _d(self, drive: str) -> int:
        try:
            return self._drive[drive]
        except KeyError:
            raise KeyError(f"maszyna {self.model.name} nie ma napędu {drive}") from None

    def _check(self, rc: int) -> None:
        if rc != 0:
            detail = self.lib.lrt_machine_err_detail(self._m)
            index = self.lib.lrt_machine_err_index(self._m)
            raise RuntimeError(f"rdzeń C: {self._strerror(rc)} (element {index}, kod {detail})")

    # ---- czas ------------------------------------------------------------------------
    def step(self, dt: float, n: int = 1) -> None:
        for _ in range(n):
            self._check(self.lib.lrt_machine_step(self._m, dt))

    @property
    def time(self) -> float:
        return self.lib.lrt_machine_time(self._m)

    # ---- napędy (master) -------------------------------------------------------------
    def drive_state(self, drive: str) -> str:
        ptr = self.lib.lrt_machine_drive(self._m, self._d(drive))
        return DRIVE_STATES[self.lib.lrt_drive_get_state(ptr)]

    def drive_error_code(self, drive: str) -> int:
        return self.lib.lrt_drive_error_code(self.lib.lrt_machine_drive(self._m, self._d(drive)))

    def inject_fault(self, drive: str, fault: int, sticky: bool = True) -> None:
        ptr = self.lib.lrt_machine_drive(self._m, self._d(drive))
        if self.lib.lrt_drive_inject_fault(ptr, fault, int(sticky)) != 0:
            raise ValueError(f"nieznana awaria napędu {fault}")

    def set_controlword(self, drive: str, word: int) -> None:
        self._check(self.lib.lrt_machine_set_controlword(self._m, self._d(drive), word))

    def hold_position(self, drive: str) -> None:
        ptr = self.lib.lrt_machine_drive(self._m, self._d(drive))
        actual = self.lib.lrt_drive_position_actual(ptr)
        self._check(self.lib.lrt_machine_set_target(self._m, self._d(drive), actual))

    def enable_all(self, dt: float, timeout: float = 3.0) -> None:
        """Sekwencja CiA 402 dla wszystkich napędów: shutdown → switch on → enable operation."""
        for word, wanted in ((CW_SHUTDOWN, "READY_TO_SWITCH_ON"), (CW_SWITCH_ON, "SWITCHED_ON"),
                             (CW_ENABLE, "OPERATION_ENABLED")):
            for drive in self.model.drives:
                self.hold_position(drive)
                self.set_controlword(drive, word)
            steps = 0
            while any(self.drive_state(d) != wanted for d in self.model.drives):
                self.step(dt)
                steps += 1
                if steps * dt > timeout:
                    states = {d: self.drive_state(d) for d in self.model.drives}
                    raise RuntimeError(f"napędy nie osiągnęły {wanted}: {states}")

    def set_joint_target(self, letter: str, value: float) -> None:
        si = value * self.model.unit(letter)
        self._check(self.lib.lrt_machine_set_joint_target(self._m, self._j(letter), si))

    def move(self, letter: str, target: float, speed: float, dt: float) -> None:
        """Rampa pozycji zadanej osi ze stałą prędkością [jedn. machine.yaml/s]."""
        start = self.joint_position(letter)
        n = max(1, round(abs(target - start) / speed / dt))
        for k in range(1, n + 1):
            self.set_joint_target(letter, start + (target - start) * k / n)
            self.step(dt)

    # ---- otoczenie -------------------------------------------------------------------
    def set_joint_position(self, letter: str, value: float) -> None:
        si = value * self.model.unit(letter)
        self._check(self.lib.lrt_machine_set_joint_position(self._m, self._j(letter), si))

    def set_drive_position(self, drive: str, value: float) -> None:
        letter = next(a for a, ds in self.model.joint_drives.items() if drive in ds)
        si = value * self.model.unit(letter)
        self._check(self.lib.lrt_machine_set_drive_position(self._m, self._d(drive), si))

    def set_estop(self, pressed: bool) -> None:
        self.lib.lrt_machine_set_estop(self._m, int(pressed))

    def set_tool_length(self, mm: float) -> None:
        self._check(self.lib.lrt_machine_set_tool_length(self._m, mm / 1000.0))

    # ---- wyjścia ---------------------------------------------------------------------
    def joint_position(self, letter: str) -> float:
        si = self.lib.lrt_machine_joint_position(self._m, self._j(letter))
        return si / self.model.unit(letter)

    def joint_skew(self, letter: str) -> float:
        return self.lib.lrt_machine_joint_skew(self._m, self._j(letter)) / self.model.unit(letter)

    def impact_speed(self, letter: str) -> float:
        si = self.lib.lrt_machine_impact_speed(self._m, self._j(letter))
        return si / self.model.unit(letter)

    @property
    def inputs(self) -> int:
        return self.lib.lrt_machine_inputs(self._m)

    def input(self, name: str) -> bool:
        """Stan wejścia z `io.inputs` (True = obwód zamknięty)."""
        return bool(self.inputs >> self.model.inputs[name] & 1)

    @staticmethod
    def _names(mask: int) -> set[str]:
        return {name for name, bit in EVENTS.items() if mask & bit}

    def events(self) -> set[str]:
        return self._names(self.lib.lrt_machine_events(self._m))

    def joint_events(self, letter: str) -> set[str]:
        return self._names(self.lib.lrt_machine_joint_events(self._m, self._j(letter)))

    def clear_events(self) -> None:
        self.lib.lrt_machine_clear_events(self._m)

    def tool_tip(self, workpiece: bool = False) -> tuple[float, float, float]:
        """Koniec narzędzia [mm] w układzie maszyny albo detalu (kinematyka prosta)."""
        out = (ctypes.c_double * 3)()
        self._check(self.lib.lrt_machine_tool_tip(self._m, int(workpiece), out))
        return (out[0] * 1000.0, out[1] * 1000.0, out[2] * 1000.0)
