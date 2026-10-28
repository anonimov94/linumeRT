"""Wyrocznia Plant: soft limits i strefy zakazane (REQ-VM-06, sesja 019).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude · sesja 019.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from linumert_plant.lrtnet import AxisCommand, Command
from linumert_plant.oracle import Box, Oracle

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "config" / "machines" / "mill_servo_table.yaml"


class FakeMachine:
    """Napęd X: położenie fizyczne 10 mm, 6064h = 0, 1000 imp/mm; narzędzie w `tip`."""

    def __init__(self, tip=(0.0, 0.0, 0.0)):
        self.tip = tip

    def drive_position(self, drive):
        return 10.0

    def position_actual(self, drive):
        return 0

    def tool_tip(self, workpiece=False):
        return self.tip


def _oracle(**kw) -> Oracle:
    return Oracle(soft_limits={"X": (1.0, 599.0)}, zones=[Box("magazyn", (500, 800, -120),
                                                             (600, 900, 0))],
                  drive_axis={"drv_x": "X"}, counts_per_unit={"drv_x": 1000.0}, **kw)


def _cmd(seq, target_mm, dout=1 << 31, mode=8):
    # target względem położenia 10 mm przy 6064h = 0
    return Command(seq=seq, time_ns=seq * 1_000_000, digital_out=dout,
                   axes=[AxisCommand(controlword=0x0F, mode=mode,
                                     target_pos=round((target_mm - 10.0) * 1000))])


def test_box_contains_interior_not_edge():  # REQ-VM-06
    box = Box("b", (0, 0, 0), (10, 10, 10))
    assert box.contains((5, 5, 5))
    assert not box.contains((10, 5, 5))  # krawędź: dotknięcie granicy nie jest wjazdem
    assert not box.contains((5, -0.1, 5))
    assert not box.contains((5, 5, 10.1))


def test_soft_limit_violation_edge_triggered():  # REQ-VM-06
    o, m = _oracle(), FakeMachine()
    assert o.check(m, _cmd(1, 300.0), ["drv_x"]) == []
    first = o.check(m, _cmd(2, 0.5), ["drv_x"])
    assert len(first) == 1 and first[0].kind == "soft_limit" and first[0].seq == 2
    assert first[0].name == "X:drv_x" and first[0].position == [pytest.approx(0.5)]
    assert o.check(m, _cmd(3, 0.4), ["drv_x"]) == []  # ten sam stan: bez nowego zdarzenia
    assert o.violations[0].cycles == 2
    o.check(m, _cmd(4, 5.0), ["drv_x"])
    assert len(o.check(m, _cmd(5, 600.0), ["drv_x"])) == 1  # nowe wejście, druga strona
    assert o.total == 2 and not o.passed and o.report()["result"] == "FAIL"


def test_tolerance_and_non_csp_ignored():  # REQ-VM-06
    o, m = _oracle(), FakeMachine()
    assert o.check(m, _cmd(1, 599.0005), ["drv_x"]) == []  # w tolerancji 1 µm
    assert o.check(m, _cmd(2, 700.0, mode=6), ["drv_x"]) == []  # bazowanie w napędzie
    assert o.passed


def test_zone_violation_from_tool_tip():  # REQ-VM-06
    o = _oracle()
    assert o.check(FakeMachine((550, 850, -50)), _cmd(1, 300.0), ["drv_x"])[0].name == "magazyn"
    assert o.check(FakeMachine((450, 850, -50)), _cmd(2, 300.0), ["drv_x"]) == []
    assert o.total == 1


def test_disarmed_until_master_bit():  # REQ-VM-06: bazowanie wyjeżdża za soft limits
    o, m = _oracle(arm_bit=31), FakeMachine()
    assert o.check(m, _cmd(1, 0.5, dout=0), ["drv_x"]) == []
    assert o.checked == 0
    assert len(o.check(m, _cmd(2, 0.5), ["drv_x"])) == 1
    always = _oracle(arm_bit=None)
    assert len(always.check(m, _cmd(1, 0.5, dout=0), ["drv_x"])) == 1


@pytest.fixture(scope="module")
def core():
    from linumert_plant import core_binding

    try:
        core_binding.load_library()
    except core_binding.PlantCoreUnavailable as exc:
        pytest.skip(str(exc))
    return core_binding


def test_server_oracle_with_real_model(core):  # REQ-VM-06
    from linumert_plant.build_machine import build_machine
    from linumert_plant.server import PlantConfig, PlantServer
    sys.path.insert(0, str(ROOT / "plant" / "server"))
    from test_master import Master

    server = PlantServer(core.PlantMachine(build_machine(MACHINE)), PlantConfig())
    # strefa na całą przestrzeń (bez walidacji machine.yaml): narzędzie zawsze w środku
    server.oracle.zones = [Box("magazyn", (-1e4, -1e4, -1e4), (1e4, 1e4, 1e4))]
    master = Master(len(server.drives), transport=server.handle)
    master.enable()
    assert server.oracle.checked == 0  # nieuzbrojona (bit 31 = 0)
    x = server.drives.index("drv_x")
    before = server.machine.drive_position("drv_x")
    master.digital_out = 1 << 31
    master.move(x, 10 * 13107, 100_000.0, 1_000_000.0)  # +10 mm
    for _ in range(300):
        master.exchange()
    after = server.machine.drive_position("drv_x")
    assert after - before == pytest.approx(10.0, abs=0.01)  # znak i skala przeliczenia
    target = server.oracle.target_position(server.machine, "drv_x", master.axes[x].target_pos)
    assert target == pytest.approx(after, abs=0.01)
    report = server.report()["oracle"]
    assert report["result"] == "FAIL" and report["violations"][0]["name"] == "magazyn"
    json.dumps(server.report())  # raport serializowalny
