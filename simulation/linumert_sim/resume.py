"""Sprawdzenie podglądu D38 na kopii materiału; bez komend do maszyny.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex · 2026-10-21
"""

import copy
import math

from linumert.programs.resume import ResumeRefused, ResumeSettings, plan_reentry

from .engine import Sample, SimEngine


def preview_reentry(engine, path, tool_number, settings=None):
    settings = settings or ResumeSettings()
    cutter = engine.tools.get(tool_number)
    if engine.stock is None or cutter is None or cutter.substitute or cutter.kind != "flat":
        raise ResumeRefused("Wymagana przygotówka i zdefiniowany frez płaski z bazy narzędzi.")
    if any(axis not in engine.machine.travel for axis in "XYZ"):
        raise ResumeRefused("Brak zakresów XYZ w modelu maszyny.")
    reasons = []
    for side in (1, -1):
        for radius_scale in (0.4, 0.2):
            plan = plan_reentry(path, cutter.radius * 2, engine.stock.z_top, settings,
                                side=side, radius_scale=radius_scale)
            trial = SimEngine(copy.deepcopy(engine.machine))
            trial.set_stock(copy.deepcopy(engine.stock), engine.material)
            trial.set_tools({tool_number: cutter})
            before = trial.stock.volume()
            version = trial.stock.version
            rejected = None
            for k, point in enumerate(plan.points):
                x, y, z, motion = point
                nose = (x, y, z + cutter.gauge)
                if any(not lo < value < hi for value, (lo, hi) in zip(
                        nose, (engine.machine.travel[a] for a in "XYZ"), strict=True)):
                    rejected = "Powrót wykracza poza zakres osi."
                    break
                events = trial.step(Sample(k * 0.01, nose, tool_number,
                                           1000 * cutter.hand, motion))
                if any(event.kind == "collision" for event in events):
                    rejected = "Powrót koliduje z materiałem albo modelem maszyny."
                    break
                if trial.stock.version != version:
                    version = trial.stock.version
                    if not math.isclose(trial.stock.volume(), before, abs_tol=0.001):
                        rejected = "Powrót wchodzi w nieusunięty materiał."
                        break
            if rejected is None:
                return plan
            reasons.append(rejected)
    raise ResumeRefused("Nie znaleziono przejazdu w zebranym materiale. " + reasons[-1])
