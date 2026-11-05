"""Full precision LinuxCNC callbacks, with private tools and no parser fallback.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from ._interpreter_process import InterpreterOutputLimit, run_bounded
from .linuxcnc_check import InterpreterUnavailable, find_linuxcnc

DEFAULT_LIBRARY = (Path(__file__).resolve().parents[3] / "core/native/build"
                   / "liblinumert_tooldata.so")


def capture(program: str, table: str, origin_mm, offset: str, start_mm, *,
            root=None, library: Path | str | None = None, timeout=20.0) -> dict:
    """Invoke the actual interpreter in a disposable process, never the live CNC.

    Caller validates/regenerates the job first. The original program is unmodified;
    initcodes establish the assumed start and work offset only in the interpreter.
    """
    from .job import OFFSETS

    if offset not in OFFSETS:
        raise ValueError("Nieobsługiwany układ detalu")
    if any(len(v) != 3 or any(isinstance(x, bool) or not math.isfinite(x) for x in v)
           for v in (origin_mm, start_mm)):
        raise ValueError("Początek i zero detalu wymagają trzech skończonych współrzędnych mm")
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise ValueError("Limit dokładnego interpretera musi mieścić się w (0, 60] s")
    library = Path(library or os.environ.get("LINUMERT_TOOL_DATA_LIB", DEFAULT_LIBRARY))
    if not library.is_file():
        raise InterpreterUnavailable("Brak adaptera dokładnej tabeli LinuxCNC "
                                     "(make -C core/native linuxcnc-tooldata LINUXCNC_DIR=...)")
    library = library.resolve()
    prefix, _ = find_linuxcnc(root)
    with tempfile.TemporaryDirectory(prefix="linumert-job-trace-") as temporary:
        private = Path(temporary)
        path = private / "program.ngc"
        path.write_text(program, encoding="utf-8")
        tool_table = private / "tool.tbl"
        tool_table.write_text(table, encoding="utf-8")
        parameters = private / "trace.var"
        parameters.touch()
        def xyz(values):
            return " ".join(f"{a}{v:.17g}" for a, v in zip("XYZ", values, strict=True))
        data = {"program": str(path), "table": str(tool_table), "library": str(library),
                "parameters": str(parameters), "timeout": timeout,
                "initcodes": ["G21 G94 F0", "G90 G49 G92.1",
                              f"G10 L2 P{OFFSETS.index(offset) + 1} {xyz(origin_mm)}",
                              offset, "G53 G0 " + xyz(start_mm)]}
        config = private / "input.json"
        config.write_text(json.dumps(data, allow_nan=False), encoding="utf-8")
        env = os.environ.copy()
        env.update(HOME=temporary, TMPDIR=temporary)
        env.pop("INI_FILE_NAME", None)
        env["PYTHONPATH"] = os.pathsep.join(filter(None, [
            str(Path(__file__).resolve().parents[2]), env.get("PYTHONPATH")]))
        command = " ".join(prefix + ["exec " + shlex.join([
            sys.executable, "-P", "-m", "linumert.programs._job_trace_worker", str(config)])])
        try:
            run = run_bounded(["bash", "-c", command], cwd=temporary, env=env, timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise ValueError("Przekroczono czas dokładnego interpretera") from error
        except InterpreterOutputLimit as error:
            raise ValueError(str(error)) from error
        if run.returncode:
            raise ValueError(f"Dokładny interpreter zakończył się kodem {run.returncode}: "
                             + run.stderr[-1500:])
        trace = json.loads(run.stdout)
        if (trace.get("format") != "linumert.job.trace" or trace.get("version") != 1
                or trace.get("completed") is not True):
            raise ValueError("Niekompletny wynik dokładnego interpretera")
        return trace
