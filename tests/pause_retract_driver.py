# SPDX-License-Identifier: GPL-2.0-or-later
"""Real LinuxCNC/QtVCP driver for paused retract. Model-Author: Codex."""

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import linuxcnc
from PyQt5 import QtCore, QtWidgets

import hal

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "screens/linumert"))
from linumert_pause_retract import RetractControl, RetractPanel  # noqa: E402


def run(ini, joint_count, output):
    app = QtWidgets.QApplication([])
    from qtvcp.core import Action, Status

    c, status, errors = linuxcnc.command(), Status(), linuxcnc.error_channel()
    s = status.stat
    seen_errors = []

    def wait(condition, timeout=20, control=None):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            s.poll()
            app.processEvents()
            if control is not None:
                control.tick()
            message = errors.poll()
            if message:
                seen_errors.append(message)
            if condition():
                return
            time.sleep(0.01)
        raise AssertionError(("timeout", seen_errors, s.task_state, s.interp_state,
                              repr(control.last) if control else None,
                              control.model.message if control else None))

    c.state(linuxcnc.STATE_ESTOP_RESET)
    wait(lambda: s.task_state == linuxcnc.STATE_ESTOP_RESET)
    c.state(linuxcnc.STATE_ON)
    wait(lambda: s.task_state == linuxcnc.STATE_ON)
    c.mode(linuxcnc.MODE_MANUAL)
    c.wait_complete()
    c.teleop_enable(0)
    c.wait_complete()
    c.home(-1)
    wait(lambda: all(s.homed[:joint_count]), 120)
    c.teleop_enable(1)
    c.wait_complete()
    c.mode(linuxcnc.MODE_MDI)
    c.wait_complete()
    c.mdi("G21 G90 G10 L2 P1 X0 Y0 Z0")
    c.wait_complete()

    component = hal.component("linumert")
    component.newpin("retract-own", hal.HAL_BIT, hal.HAL_OUT)
    component.newpin("retract-target", hal.HAL_FLOAT, hal.HAL_OUT)
    component.newpin("eoffset-spindle-count", hal.HAL_S32, hal.HAL_OUT)
    component.ready()
    hal.connect("linumert.retract-own", "linumert.retract.own")
    hal.new_sig("linumert.retract.target", hal.HAL_FLOAT)
    hal.connect("linumert.retract-target", "linumert.retract.target")
    hal.connect("lrt_retract_select.in1", "linumert.retract.target")

    class Pin:
        def __init__(self, name):
            self.name = name

        def set(self, value):
            component[self.name] = value

    shell = QtCore.QObject()
    shell.info = SimpleNamespace(INIPATH=str(ini), MACHINE_IS_METRIC=True,
                                 AVAILABLE_JOINTS=list(range(joint_count)))
    shell.s = SimpleNamespace(axes=("X", "Y", "Z"))
    shell.hmi_pins = {key: Pin(name) for key, name in
                     (("retract_own", "retract-own"), ("retract_target", "retract-target"))}
    shell.action, shell.status = Action(), status
    alarms = []
    shell.show_alarm = lambda *args: alarms.append(args)
    control = RetractControl(shell)
    control.timer.stop()
    panel = RetractPanel(control)
    panel.height.setValue(2)
    panel.feed.setValue(300)
    panel.resize(1200, 150)
    panel.show()
    rows = []

    def position():
        return tuple(float(hal.get_value(f"axis.{a}.pos-cmd")) for a in "xyz")

    def feedback_z():
        return float(hal.get_value(f"joint.{joint_count - 1}.motor-pos-fb"))

    for side, inch in ((40, False), (41, False), (42, False), (41, True), (42, True)):
        scale = 25.4 if inch else 1
        path = output / f"g{side}-{'inch' if inch else 'mm'}.ngc"
        def f(x, scale=scale):
            return f"{x / scale:.8f}"
        compensation = f"G{side} D1 " if side != 40 else ""
        path.write_text("G21 G17 G90 G94 G40 G49 G54\nM61 Q1\nS3000 M3\n"
                        "G53 G0 Z-5\nG0 X100 Y100\nG43 H1\nG1 Z-30 F600\n"
                        + ("G20\n" if inch else "")
                        + f"{compensation}G1 X{f(120)} Y{f(100)} F{f(1200)}\n"
                        + f"G1 X{f(230)} Y{f(100)}\n"
                        + f"G40 G1 X{f(250)} Y{f(100)}\nM5\nM2\n")
        c.mode(linuxcnc.MODE_AUTO)
        c.wait_complete()
        c.program_open(str(path))
        c.wait_complete()
        expected_y = {40: 100, 41: 102, 42: 98}[side]
        c.auto(linuxcnc.AUTO_RUN, 0)
        wait(lambda expected_y=expected_y: 145 < position()[0] < 210
             and abs(position()[1] - expected_y) < 0.01
             and abs(position()[2] + 20) < 0.01
             and s.interp_state != linuxcnc.INTERP_IDLE)
        c.auto(linuxcnc.AUTO_PAUSE)
        wait(lambda: s.paused and abs(s.current_vel) < 1e-7, control=control)
        wait(lambda: control.last and control.last.ready and panel.withdraw.isEnabled(),
             control=control)
        before, z_before, frame = position(), feedback_z(), control.last.frame
        assert abs(before[1] - expected_y) < 0.01, (side, before)
        panel.withdraw.click()
        assert control.model.active, control.model.message
        wait(lambda: control.model.phase == "retracted", control=control)
        wait(lambda z_before=z_before: abs(feedback_z() - z_before - 2) < 0.005, control=control)
        assert max(abs(a - b) for a, b in zip(position(), before, strict=True)) < 1e-6, (
            "planner changed", before, position())
        assert s.paused and control.last.frame == frame
        shell.action.PAUSE()  # Original QtVCP resume must be blocked.
        assert alarms and s.paused and control.model.active
        app.processEvents()
        panel.grab().save(str(output / f"retract-g{side}.png"))
        if side == 40:
            panel.return_button.click()
            wait(lambda: not control.model.active, control=control)
            assert s.paused  # Plain return must leave the original program paused.
            shell.action.PAUSE()
        else:
            panel.resume_button.click()
        wait(lambda: not control.model.active and not s.paused, control=control)
        assert abs(hal.get_value("axis.z.eoffset")) < 1e-6
        assert abs(hal.get_value("axis.z.eoffset-request")) < 1e-6
        wait(lambda before=before: position()[0] > before[0] + 0.2, control=control)
        assert abs(position()[1] - expected_y) < 0.01, ("compensation lost", position())
        wait(lambda: s.interp_state == linuxcnc.INTERP_IDLE, control=control)
        assert s.task_state == linuxcnc.STATE_ON
        rows.append({"correction": side, "inch": inch, "paused": before,
                     "end": position(), "offset": hal.get_value("axis.z.eoffset")})
    (output / "retract-results.json").write_text(json.dumps(rows, indent=2))
    print("D38_RESULT " + json.dumps(rows), flush=True)
    failures = [e for e in seen_errors if e[0] in (linuxcnc.NML_ERROR, linuxcnc.OPERATOR_ERROR)]
    assert not failures, seen_errors
    panel.close()
    component.exit()


if __name__ == "__main__":
    run(Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]))
