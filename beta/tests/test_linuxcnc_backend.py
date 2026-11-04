# SPDX-License-Identifier: GPL-2.0-or-later
"""Backend LinuxCNC na ścisłej atrapie modułu ``linuxcnc``: tylko to, co ma prawdziwe API 2.9.

Model-Author: Claude. Odbiór na prawdziwym LinuxCNC: integration/test_machine_linuxcnc.py.
Atrapa przepuszczająca dowolne atrybuty ukryła wcześniej nieistniejące ``command.estop``.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from linumert.cnc.linuxcnc_reader import LinuxCNCReader
from linumert_headless.backends.linuxcnc import ERROR_RETENTION_S, LinuxCNCBackend
from linumert_headless.errors import Conflict, InvalidRequest, SafetyRefused
from linumert_headless.services.machine import MachineService
from linumert_headless.session import SessionManager


class Command:
    """Sloty = metody, których używamy, z listy ``linuxcnc.command`` 2.9."""

    __slots__ = ("calls", "module")

    def __init__(self, module):
        self.module = module
        self.calls = []

    def _log(self, name, *args):
        self.calls.append((name, *args))

    def state(self, value): self._log("state", value)
    def mode(self, value): self._log("mode", value)
    def teleop_enable(self, value): self._log("teleop_enable", value)
    def home(self, joint): self._log("home", joint)
    def jog(self, *args): self._log("jog", *args)
    def mdi(self, text): self._log("mdi", text)
    def load_tool_table(self): self._log("load_tool_table")
    def wait_complete(self, timeout=5.0): return 0


def module_for(joint_axes, *, homed=None, axis_mask=0b111, task_state=4, interp=1,
               motion_mode=1, task_mode=1):
    module = SimpleNamespace(
        STATE_ESTOP=1, STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=4,
        MODE_MANUAL=1, MODE_AUTO=2, MODE_MDI=3,
        INTERP_IDLE=1, INTERP_READING=2, INTERP_PAUSED=3, INTERP_WAITING=4,
        JOG_STOP=0, JOG_CONTINUOUS=1, JOG_INCREMENT=2,
        TRAJ_MODE_FREE=1, TRAJ_MODE_COORD=2, TRAJ_MODE_TELEOP=3,
    )
    module.cmd = Command(module)
    module.command = lambda: module.cmd
    module.ini = lambda _path: SimpleNamespace(
        find=lambda section, key: "tool.tbl" if key == "TOOL_TABLE" else (
            dict(enumerate(joint_axes)).get(int(section.split("_")[1]))))
    count = len(joint_axes)
    stat = SimpleNamespace(
        poll=lambda: None, axis_mask=axis_mask, joints=count, ini_filename="m.ini",
        actual_position=(0.0,) * 9, position=(0.0,) * 9,
        homed=tuple(homed if homed is not None else (1,) * count), limit=(0,) * count,
        axis=(), task_state=task_state, task_mode=task_mode, interp_state=interp,
        motion_mode=motion_mode)
    module.stat = lambda: stat
    module.error_channel = lambda: SimpleNamespace(poll=lambda: None)
    return module


GANTRY = ["X", "Y", "Y", "Z"]


def test_estop_i_reset_ida_przez_state() -> None:
    module = module_for(GANTRY)
    backend = LinuxCNCBackend(module=module)
    backend.estop()
    backend.estop_reset()
    assert module.cmd.calls == [("state", module.STATE_ESTOP),
                                ("state", module.STATE_ESTOP_RESET)]


def test_bazowanie_osi_portalu_wybiera_joint_z_ini_w_trybie_manual_bez_teleop() -> None:
    module = module_for(GANTRY)
    backend = LinuxCNCBackend(module=module)
    backend.home("Z")
    assert module.cmd.calls == [("mode", module.MODE_MANUAL), ("teleop_enable", 0), ("home", 3)]


def test_bazowanie_wszystkich() -> None:
    module = module_for(GANTRY)
    LinuxCNCBackend(module=module).home(None)
    assert module.cmd.calls[-1] == ("home", -1)


def test_niezbazowany_joint_portalu_nie_daje_all_homed() -> None:
    backend = LinuxCNCBackend(module=module_for(GANTRY, homed=(1, 1, 1, 0)))
    snap = backend.snapshot()
    assert snap.axis("Y").homed and not snap.axis("Z").homed and not snap.all_homed
    backend = LinuxCNCBackend(module=module_for(GANTRY, homed=(1, 1, 0, 1)))
    assert not backend.snapshot().axis("Y").homed


def test_ini_bez_mapy_jointow_jest_bezpieczne() -> None:
    module = module_for([None, None, None, None], homed=(1, 1, 1, 0))
    backend = LinuxCNCBackend(module=module)
    assert not backend.snapshot().all_homed
    with pytest.raises(Conflict):
        backend.home("Z")


def test_jog_po_bazowaniu_to_teleop_z_numerem_osi() -> None:
    module = module_for(GANTRY)
    backend = LinuxCNCBackend(module=module)
    backend.jog_increment("Z", -10.0, 3.0)
    assert module.cmd.calls[-2:] == [("teleop_enable", 1),
                                     ("jog", module.JOG_INCREMENT, False, 2, -10.0, 3.0)]


def test_odswiezanie_jogu_nie_zmienia_trybu_w_ruchu() -> None:
    module = module_for(GANTRY, motion_mode=3)
    LinuxCNCBackend(module=module).jog("X", 5.0)
    assert module.cmd.calls == [("jog", module.JOG_CONTINUOUS, False, 0, 5.0)]


def test_jog_z_mdi_przelacza_tryb_i_teleop() -> None:
    module = module_for(GANTRY, motion_mode=2, task_mode=3)
    LinuxCNCBackend(module=module).jog("X", 5.0)
    assert module.cmd.calls[:2] == [("mode", module.MODE_MANUAL), ("teleop_enable", 1)]


def test_tabela_narzedzi_z_ini_i_wczytanie() -> None:
    module = module_for(GANTRY)
    backend = LinuxCNCBackend(module=module)
    assert backend.active_tool_table().name == "tool.tbl"
    backend.reload_tools()
    assert module.cmd.calls == [("load_tool_table",)]


def test_bezpieczna_wysokosc_generatorow_bierze_limit_maszyny(tmp_path) -> None:
    ini = tmp_path / "m.ini"
    ini.write_text("[TRAJ]\nLINEAR_UNITS = mm\n[AXIS_Z]\nMIN_LIMIT = -119\nMAX_LIMIT = -1\n",
                   encoding="utf-8")
    backend = SimpleNamespace(active_ini=lambda: ini)
    machine = MachineService(backend, SessionManager())
    assert machine.localize_gcode("M5\nG53 G0 Z0\nT1 M6\n") == "M5\nG53 G0 Z-1\nT1 M6\n"
    assert machine.localize_gcode("G53 G0 Z0 X5\n") == "G53 G0 Z0 X5\n"
    assert MachineService(SimpleNamespace(), SessionManager()).localize_gcode(
        "G53 G0 Z0") == "G53 G0 Z0"


def test_numer_osi_teleop_jest_z_dziewieciu_liter_nie_z_kolejnosci() -> None:
    module = module_for(["X", "Y", "Z", "C"], axis_mask=0b100111)
    LinuxCNCBackend(module=module).jog("C", 5.0)
    assert module.cmd.calls[-1] == ("jog", module.JOG_CONTINUOUS, False, 5, 5.0)


def test_jog_przed_bazowaniem_to_joint_a_portal_odmawia() -> None:
    module = module_for(GANTRY, homed=(0, 0, 0, 0))
    backend = LinuxCNCBackend(module=module)
    backend.jog("Z", 5.0)
    assert module.cmd.calls[-1] == ("jog", module.JOG_CONTINUOUS, True, 3, 5.0)
    module.cmd.calls.clear()
    with pytest.raises(SafetyRefused):
        backend.jog("Y", 5.0)
    assert module.cmd.calls == []


def test_jog_stop_idzie_w_obu_trybach_na_wszystkie_jointy_osi() -> None:
    module = module_for(GANTRY)
    LinuxCNCBackend(module=module).jog_stop("Y")
    assert module.cmd.calls == [("jog", module.JOG_STOP, False, 1),
                                ("jog", module.JOG_STOP, True, 1),
                                ("jog", module.JOG_STOP, True, 2)]


def test_komunikat_linuxcnc_przezywa_odczyty_i_wygasa() -> None:
    module = module_for(GANTRY)
    messages = [(1, "odmowa")]
    module.error_channel = lambda: SimpleNamespace(
        poll=lambda: messages.pop() if messages else None)
    now = [100.0]
    reader = LinuxCNCReader(module=module, clock=lambda: now[0])
    backend = LinuxCNCBackend(module=module, reader=reader)
    assert backend.snapshot().errors == ("odmowa",)
    assert backend.snapshot().errors == ("odmowa",)
    now[0] += ERROR_RETENTION_S
    assert backend.snapshot().errors == ()


def test_powtorzony_komunikat_jest_jeden_raz() -> None:
    module = module_for(GANTRY)
    messages = [(1, "odmowa"), (1, "odmowa")]
    module.error_channel = lambda: SimpleNamespace(
        poll=lambda: messages.pop() if messages else None)
    assert LinuxCNCBackend(module=module).snapshot().errors == ("odmowa",)


def test_offset_pracy_to_g10_l2_z_wlasciwym_p() -> None:
    module = module_for(GANTRY)
    LinuxCNCBackend(module=module).set_work_offset("G59.2", {"X": 12.5, "z": -1.0})
    assert module.cmd.calls[-1] == ("mdi", "G10 L2 P8 X12.500000 Z-1.000000")


@pytest.mark.parametrize(("name", "values", "kwargs", "error"), [
    ("G54.1", {"X": 1.0}, {}, InvalidRequest),
    ("G54", {"A": 1.0}, {}, InvalidRequest),
    ("G54", {"X": 1.0}, {"task_state": 2}, SafetyRefused),
    ("G54", {"X": 1.0}, {"interp": 2}, Conflict),
])
def test_offset_pracy_odmowy(name, values, kwargs, error) -> None:
    module = module_for(GANTRY, **kwargs)
    with pytest.raises(error):
        LinuxCNCBackend(module=module).set_work_offset(name, values)
    assert module.cmd.calls == []
