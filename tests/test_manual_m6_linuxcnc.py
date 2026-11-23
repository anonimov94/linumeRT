# SPDX-License-Identifier: GPL-2.0-or-later
"""Sesja 034/G2: ręczny handshake M6 w LinuxCNC + Plant bez ekranu."""

from pathlib import Path

import pytest
from plant_session import run_generated_plant

MACHINE = Path(__file__).resolve().parents[1] / "config/machines/mill_servo_table.yaml"

DRIVER = r"""
import subprocess
from pathlib import Path

REQUEST = "iocontrol.0.tool-change"
ACK = "iocontrol.0.tool-changed"
NUMBER = "iocontrol.0.tool-prep-number"

def pin(name):
    return subprocess.check_output(["halcmd", "getp", name], text=True).strip()

def ack(value):
    subprocess.run(["halcmd", "setp", ACK, str(int(value))], check=True)

def run_to_request(tool, mounted, offset):
    program = Path.cwd() / f"manual-m6-t{tool}.ngc"
    program.write_text(f"T{tool} M6\nG43 H{tool}\nM2\n", encoding="ascii")
    c.program_open(str(program))
    c.wait_complete()
    c.auto(linuxcnc.AUTO_RUN, 0)
    assert wait(lambda: pin(REQUEST) == "TRUE", 30), f"Brak żądania M6 dla T{tool}"
    until = time.monotonic() + 0.5
    while time.monotonic() < until:
        s.poll()
        assert pin(REQUEST) == "TRUE" and pin(ACK) == "FALSE"
        assert int(pin(NUMBER)) == tool
        assert s.interp_state != linuxcnc.INTERP_IDLE
        assert s.tool_in_spindle == mounted and abs(s.tool_offset[2] - offset) < 1e-6
        time.sleep(0.02)

def confirm(tool, offset):
    ack(True)
    try:
        assert wait(lambda: pin(REQUEST) == "FALSE", 15), f"M6 T{tool} nie zwolniło żądania"
    finally:
        ack(False)
    assert wait(idle, 30), f"Program T{tool} nie zakończył się po potwierdzeniu"
    assert s.tool_in_spindle == tool and abs(s.tool_offset[2] - offset) < 1e-6

assert on and homed, "Plant niegotowy"
# Konfiguracja bez ekranu nie uruchamia POSTGUI_HALFILE z automatycznym potwierdzeniem.
# Zapis do wejścia jest możliwy wyłącznie przy braku sterującego wyjścia HAL.
ack(False)
assert pin(REQUEST) == "FALSE"
c.mode(linuxcnc.MODE_AUTO)
c.wait_complete()
s.poll()
assert s.tool_in_spindle == 0
run_to_request(1, 0, 0.0)
confirm(1, 75.0)

run_to_request(2, 1, 75.0)
c.abort()
assert wait(lambda: pin(REQUEST) == "FALSE" and s.interp_state == linuxcnc.INTERP_IDLE, 30)
assert pin(ACK) == "FALSE"
assert s.tool_in_spindle == 1
assert abs(s.tool_offset[2] - 75.0) < 1e-6
after_abort = s.tool_in_spindle

run_to_request(2, 1, 75.0)
confirm(2, 80.0)
print("RESULT " + json.dumps({"after_abort": after_abort, "tool": s.tool_in_spindle,
                              "offset_z": s.tool_offset[2]}), flush=True)
"""


@pytest.mark.linuxcnc
def test_manual_m6_waits_for_confirmation_and_can_be_cancelled_on_plant(tmp_path):
    result, _, _ = run_generated_plant(tmp_path, MACHINE, DRIVER, port=47746, timeout=420)
    assert result["after_abort"] == 1
    assert result["tool"] == 2
    assert result["offset_z"] == pytest.approx(80.0, abs=1e-6)
