"""Job material/load diagnostics using exact, executed LinuxCNC motion.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex

Invoked in a low-priority child by job_preflight. No CNC state or command APIs,
subset parser, current tool database or mutable drive-library lookup.
"""

import json
import math

from linumert import native
from linumert.machine.schema import MachineConfig
from linumert.programs.lnx import parse_lnx

from .engine import KC, Sample, SimEngine
from .job_collisions import sweep
from .job_model import frozen_cutters, frozen_machine
from .job_path import segments
from .placement import place_stock

STEP_MM = 0.25
DT = 0.05
CHORD_MM = 0.005
MAX_SAMPLES = 1_000_000


def diagnose(data):
    files = data["files"]
    config = MachineConfig.model_validate_json(files["machine.yaml"])
    model = frozen_machine(config, json.loads(files["drives.json"]))
    cutters = frozen_cutters(json.loads(files["tools.json"]))
    program = parse_lnx(json.loads(files["program.lnx"]))
    if program.stock is None:
        raise ValueError("Brak przygotówki w zadaniu")
    material = (program.stock.material or "").strip().lower()
    if material not in KC:
        raise ValueError("Wymagany jawny materiał ze znanym modelem oporu skrawania")
    setup = json.loads(files["setup.json"])
    stock = place_stock(program.stock, setup["origin_mm"], cell=0.25)
    engine = SimEngine(model)
    engine.set_stock(stock, material)
    engine.set_tools(cutters)
    volume0 = stock.volume()
    speeds = {axis.letter: axis.max_velocity for axis in config.axes}
    events, seen = [], set()
    time = length = 0.0
    count = motions = 0
    peak = {"power_w": 0.0, "torque_nm": 0.0, "force_n": 0.0,
            "spindle_ratio": 0.0, "axis_ratio": 0.0}

    def add(rows):
        for event in rows:
            key = (event["code"], tuple(event["pair"]), event["tool"])
            if key not in seen:
                seen.add(key)
                events.append(event)
                if len(events) > 1000:
                    raise ValueError("Przekroczono limit zdarzeń diagnostyki")

    for move in segments(data["trace"], data["start_mm"]):
        motions += 1
        cutter = cutters.get(move.tool)
        if (move.tool and cutter is None) or (not move.rapid and cutter is None):
            raise ValueError(f"linia {move.line}: brak geometrii wykonanego T{move.tool}")
        if abs(move.rpm) > model.spindle_max_rpm:
            raise ValueError(f"linia {move.line}: obroty ponad limit wrzeciona")
        # Nominal kinematic lower bound only: no acceleration, blending, manual
        # tool exchange or controller scheduling is simulated here.
        if move.rapid:
            seconds = max(abs(b - a) / speeds[axis]
                          for axis, a, b in zip("XYZ", move.start, move.end, strict=True))
        else:
            seconds = move.length / (move.feed / 60)
        samples = move.sample_count(seconds, step_mm=STEP_MM, dt=DT, chord_mm=CHORD_MM)
        count += samples
        if count > MAX_SAMPLES:
            raise ValueError("Przekroczono łączny limit próbek diagnostyki")
        kind = "rapid" if move.rapid else "feed"
        # Seed the incoming state at the SAME physical position. In particular,
        # a change G1→G0 or M3→M5 must not inherit the preceding segment's state.
        engine.begin_segment(Sample(time, move.start, move.tool, move.rpm, kind, move.line))
        previous = move.start
        for k in range(1, samples + 1):
            nose = move.point(k / samples)
            sample = Sample(time + seconds * k / samples, nose, move.tool,
                            move.rpm, kind, move.line)
            add(sweep(model, cutter, previous, nose, line=move.line, tool=move.tool,
                      inflation=CHORD_MM if move.center is not None else 0))
            add([event.to_dict() for event in engine.step(sample)])
            previous = nose
            load = engine.load
            peak["power_w"] = max(peak["power_w"], load.power)
            peak["torque_nm"] = max(peak["torque_nm"], load.torque)
            peak["force_n"] = max(peak["force_n"], load.force)
            if load.torque > 0:
                if load.torque_limit <= 0:
                    raise ValueError(f"linia {move.line}: obroty poza krzywą momentu wrzeciona")
                peak["spindle_ratio"] = max(peak["spindle_ratio"], load.torque / load.torque_limit)
            for force, limit in load.axis.values():
                peak["axis_ratio"] = max(peak["axis_ratio"], force / limit)
        time += seconds
        length += move.length
    if not all(math.isfinite(v) for v in (*peak.values(), time, length)):
        raise ValueError("Nieskończony wynik diagnostyki")
    return {"format": "linumert.job.material", "version": 1,
            "source": "linuxcnc.gcode", "motions": motions, "samples": count,
            "length_mm": round(length, 6), "time_lower_bound_s": round(time, 6),
            "removed_mm3": round(volume0 - stock.volume(), 6), "peak_load": peak,
            "events": events, "backend": "C" if native.library() is not None else "Python",
            "coverage": {"stock_cell_mm": stock.cell, "sample_step_mm": STEP_MM,
                "sample_dt_s": DT, "arc_chord_mm": CHORD_MM,
                "machine_bodies": [b.name for b in model.bodies],
                "machine_collisions": "conservative_continuous_envelopes",
                "tools": sorted(cutters), "material": material},
            "limitations": ["Materiał 2.5D i obciążenia są diagnostyką z siatką, "
                "nie funkcją bezpieczeństwa.",
                "Model obejmuje wyłącznie zadeklarowane bryły i strefy zakazane; "
                "brakujące mocowania nie są odgadywane.",
                "Konserwatywne obwiednie brył mogą zgłaszać możliwą kolizję "
                "przy zaokrąglonych narożach.",
                "Czas jest dolnym oszacowaniem bez przyspieszeń, wygładzania "
                "i ręcznej zmiany narzędzia.",
                "Tor nie obejmuje fizycznej obsługi ręcznej zmiany narzędzia. "
                "NIEZWERYFIKOWANE NA SPRZĘCIE."]}
