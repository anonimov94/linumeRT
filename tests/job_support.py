"""Fixture for a complete face/pocket/drill job, independent of any running machine.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from pathlib import Path

from linumert.machine.drives.machine_drives import load_machine_drives
from linumert.programs.lnx import parse_lnx, save_lnx
from linumert.tools.db import Tool, ToolDB

ROOT = Path(__file__).resolve().parents[1]


def program():
    return parse_lnx({"name": "Detal pionowy", "stock": {
        "shape": "BOX", "x": 60, "y": 40, "z": 10}, "steps": [
        {"generator": "header", "version": 1},
        {"generator": "tool_change", "version": 1, "params": {"tool": 1, "rpm": 6000}},
        {"generator": "face_mill", "version": 1, "params": {
            "x0": 5, "x1": 55, "y0": 5, "y1": 35, "depth": 1, "tool_d": 6}},
        {"generator": "pocket_rect", "version": 2, "params": {
            "cx": 30, "cy": 20, "width": 20, "height": 14,
            "z_top": -1, "depth": 2, "tool_d": 6}},
        {"generator": "tool_change", "version": 1, "params": {"tool": 2, "rpm": 3000}},
        {"generator": "drill_holes", "version": 1, "params": {
            "pattern": "list", "points": "15,10;45,30", "z_top": -1, "depth": 5}},
        {"generator": "program_end", "version": 1},
    ]})


def inputs():
    machine, resolved = load_machine_drives(ROOT / "config/machines/mill_servo_table.yaml")
    drives = {name: {"template": d.template_id, "parameters": d.params}
              for name, d in resolved.items()}
    tools = {
        1: Tool(1, 1, type="flat", description="Frez D6", offsets={"Z": 40},
                params={"d": 6, "l": 30, "flute_length": 20, "max_rpm": 8000}),
        2: Tool(2, 2, type="drill_118", description="Wiertło D5", offsets={"Z": 35},
                params={"d": 5, "l": 25, "flute_length": 15, "max_rpm": 5000}),
    }
    return program(), machine, drives, tools


def write_inputs(directory):
    directory.mkdir(parents=True, exist_ok=True)
    source = save_lnx(program(), directory / "detal.lnx")
    db = directory / "tools.db"
    with ToolDB(db) as database:
        for tool in inputs()[3].values():
            database.add(tool)
    return source, db, ROOT / "config/machines/mill_servo_table.yaml"
