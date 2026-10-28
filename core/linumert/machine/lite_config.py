"""Portable sim/Plant export. SPDX-License-Identifier: GPL-2.0-or-later.

Model-Author: Codex
"""

from pathlib import Path

from .config_build import build as build_files
from .configgen import Options, render
from .schema import MachineConfig

RESOURCES = Path(__file__).with_name("resources")


def render_lite(cfg: MachineConfig, target: str, *, test_mode: bool = False) -> dict[str, str]:
    """Self contained sim/Plant export. Never generates a hardware target."""
    if target not in ("sim", "plant"):
        raise ValueError("Lite eksportuje wyłącznie konfiguracje sim i plant")
    opt = Options(hal_dir="hal", program_prefix="nc_files", tool_table="tool.tbl", postgui="")
    files = render(cfg, target, opt)
    name = f"{cfg.machine.name}.ini"
    if test_mode:
        files[name] = files[name].replace("HMI_ESTOP_BYPASS = 0", "HMI_ESTOP_BYPASS = 1")
    for source, target_name in (("linumert_hmi_estop.hal", "hal/linumert_hmi_estop.hal"),
                                ("linumert_pause_retract.hal", "hal/linumert_pause_retract.hal"),
                                ("lrt_m6.ngc", "macros/lrt_m6.ngc"), ("tool.tbl", "tool.tbl")):
        files[target_name] = (RESOURCES / source).read_text(encoding="utf-8")
    # Virtual tool exchange only; hardware generation is refused above.
    io = ("net linumert.io.tool-change iocontrol.0.tool-change => sim_toolchange.in\n"
          "net linumert.io.tool-changed sim_toolchange.out => iocontrol.0.tool-changed\n")
    main_hal = "linumert_plant.hal" if target == "plant" else "linumert_sim.hal"
    files[main_hal] += "\n# Lite: simulated tool exchange (no hardware).\n" + io
    files["nc_files/.keep"] = ""
    return files


def build(machine: Path, target: str, out: Path, *, write: bool = False,
          test_mode: bool = False) -> tuple[str, Path | None]:
    def renderer(cfg, dest, opt):
        files = render_lite(cfg, dest, test_mode=test_mode)
        # A starter table is generated only once. It is operator data afterwards.
        if (out / "tool.tbl").exists():
            files.pop("tool.tbl")
        return files

    return build_files(machine, target, out, write=write, renderer=renderer)
