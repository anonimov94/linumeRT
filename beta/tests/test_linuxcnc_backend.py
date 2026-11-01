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
    def wait_complete(self, timeout=5.0): return 0


def module_for(joint_axes, *, homed=None, axis_mask=0b111, task_state=4, interp=1):
    module = SimpleNamespace(
        STATE_ESTOP=1, STATE_ESTOP_RESET=2, STATE_OFF=3, STATE_ON=4,
        MODE_MANUAL=1, MODE_AUTO=2, MODE_MDI=3,
        INTERP_IDLE=1, INTERP_READING=2, INTERP_PAUSED=3, INTERP_WAITING=4,
        JOG_STOP=0, JOG_CONTINUOUS=1, JOG_INCREMENT=2,
    )
    module.cmd = Command(module)
    module.command = lambda: module.cmd
    module.ini = lambda _path: SimpleNamespace(
        find=lambda section, key: dict(enumerate(joint_axes)).get(
            int(section.split("_")[1])) if key == "AXIS" else None)
    count = len(joint_axes)
    stat = SimpleNamespace(
        poll=lambda: None, axis_mask=axis_mask, joints=count, ini_filename="m.ini",
        actual_position=(0.0,) * 9, position=(0.0,) * 9,
        homed=tuple(homed if homed is not None else (1,) * count), limit=(0,) * count,
        axis=(), task_state=task_state, task_mode=1, interp_state=interp)
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
