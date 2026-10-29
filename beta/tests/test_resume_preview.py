"""D38: geometria i odmowa kolizyjnego podglądu; Model-Author: Codex.

SPDX-License-Identifier: GPL-2.0-or-later
"""

import configparser
import json
import math
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from linumert.programs.resume import ResumeRefused, ResumeSettings, plan_reentry
from linumert_sim.cutter import make_cutter
from linumert_sim.engine import SimEngine
from linumert_sim.machine import Body, Machine
from linumert_sim.resume import preview_reentry
from linumert_sim.zmap import StockMap


@pytest.mark.parametrize("side", [-1, 1])
def test_helix_is_continuous_tangent_and_overlaps_across_segments(side):
    path = [(10, 20, -2), (15, 20, -2), (20, 20, -2)]
    plan = plan_reentry(path, 8, 0, ResumeSettings(overlap=7), side=side)
    assert plan.entry == (13, 20, -2) and plan.overlap == 7
    assert plan.points[-1] == (20, 20, -2, "feed")
    assert max(p[2] for p in plan.points) == 1
    # Po przejazdach na górze schodzimy wyłącznie z ruchem XY.
    for a, b in zip(plan.points[2:], plan.points[3:], strict=False):
        if b[2] < a[2]:
            assert math.dist(a[:2], b[:2]) > 0
    entry_i = min(range(len(plan.points)), key=lambda i: math.dist(plan.points[i][:3], plan.entry))
    before = plan.points[entry_i - 1]
    delta = (plan.entry[0] - before[0], plan.entry[1] - before[1])
    assert delta[0] > 0 and abs(delta[1] / delta[0]) < 0.02


@pytest.mark.parametrize("path,settings", [
    ([(0, 0, 0)], ResumeSettings()),
    ([(0, 0, 0), (1, 0, 0)], ResumeSettings()),
    ([(0, 0, 0), (5, 0, -1)], ResumeSettings()),
    ([(0, 0, 0), (5, 0, 0)], ResumeSettings(pitch=0)),
    ([(0, 0, 0), (5, 0, 0)], ResumeSettings(pitch=0.000001)),
    ([(0, 0, 0), (math.nan, 0, 0)], ResumeSettings()),
])
def test_refuse_missing_or_unsupported_geometry(path, settings):
    with pytest.raises(ResumeRefused):
        plan_reentry(path, 8, 0, settings)


def _engine():
    engine = SimEngine(Machine(travel={"X": (-50, 50), "Y": (-50, 50), "Z": (-20, 100)}))
    engine.set_stock(StockMap("BOX", -25, -25, 25, 25, -10, 0, cell=0.5))
    engine.stock.h[:, :] = -2  # już zebrana kieszeń; narzędzie na jej dnie
    engine.set_tools({1: make_cutter(1, 40, 8, "flat",
                                    {"d": 8, "l": 30, "flute_length": 15})})
    return engine


def test_simulates_on_copy_without_altering_live_material():
    engine = _engine()
    before = engine.stock.h.copy()
    version = engine.stock.version
    plan = preview_reentry(engine, [(-5, 0, -2), (5, 0, -2)], 1)
    assert plan.entry == (3, 0, -2)
    assert np.array_equal(engine.stock.h, before) and engine.stock.version == version
    assert not engine.path and engine._prev is None


@pytest.mark.parametrize("fault", ["stock", "tool", "travel", "body", "uncut"])
def test_refuses_missing_model_or_collision(fault):
    engine = _engine()
    if fault == "stock":
        engine.stock = None
    elif fault == "tool":
        engine.tools.clear()
    elif fault == "travel":
        engine.machine.travel.clear()
    elif fault == "body":
        engine.machine.bodies.append(Body("imadlo", "box", "vise", (50, 50, 10), (0, 0, -1)))
    else:
        engine.stock.h[:, :] = 0
    with pytest.raises(ResumeRefused):
        preview_reentry(engine, [(-5, 0, -2), (5, 0, -2)], 1)


@pytest.mark.parametrize("state,codes,ok", [(3, [170, 400, 800], True),
                                          (2, [170], False), (3, [330], False)])
def test_live_preview_dispatch_has_no_command_channel(capsys, state, codes, ok):
    from linumert_sim.live import Live

    live = Live.__new__(Live)
    live.engine = _engine()
    live.to_mm = 1.0  # This fixture constructs a metric instance without __init__.
    live._resume_trace = [(-5, 0, -2), (5, 0, -2)]
    live.stat = SimpleNamespace(poll=Mock(), interp_state=state, gcodes=codes,
                                actual_position=(5, 0, 38), spindle=[], motion_type=2,
                                motion_line=10, current_line=10, tool_in_spindle=1)
    live.lc = SimpleNamespace(INTERP_IDLE=1, INTERP_PAUSED=3, command=Mock(
        side_effect=AssertionError("Nie wolno sterować CNC z symulacji")))
    live.ini = configparser.ConfigParser()
    live.command({"cmd": "resume_preview"})
    result = json.loads(capsys.readouterr().out.strip())
    assert result["ev"] == "resume_preview" and result["ok"] == ok
    live.lc.command.assert_not_called()


def test_resume_history_resets_on_tool_file_rapid_or_sampling_gap():
    from linumert_sim.engine import Sample
    from linumert_sim.live import Live

    live = Live.__new__(Live)
    live.engine, live.file = _engine(), "one.ngc"
    live._resume_trace, live._resume_key, live._resume_time = [], None, None
    live.record_resume_sample(Sample(0, (0, 0, 38), 1))
    live.record_resume_sample(Sample(0.1, (5, 0, 38), 1))
    assert len(live._resume_trace) == 2
    live.file = "two.ngc"
    live.record_resume_sample(Sample(0.2, (6, 0, 38), 1))
    assert live._resume_trace == [(6, 0, -2)]
    live.record_resume_sample(Sample(2, (7, 0, 38), 1))
    assert live._resume_trace == [(7, 0, -2)]
    live.record_resume_sample(Sample(2.1, (8, 0, 38), 1, motion="rapid"))
    assert live._resume_trace == []
    live.record_resume_sample(Sample(2.2, (9, 0, 38), 0))
    assert live._resume_trace == []

