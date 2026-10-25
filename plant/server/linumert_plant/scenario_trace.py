"""Opt-in HAL samples at the end of the Plant servo thread (LEGACY-RUNTIME).

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex. LinuxCNC sampler/halsampler; never a second motion planner.
One HAL-cycle snapshot does not align the remote Plant or NML clocks.
"""

from __future__ import annotations

import json
import math
import shlex
import subprocess
import time
from pathlib import Path


def channels() -> list[tuple[str, str, str, str | None]]:
    """Name, HAL type, signal, optional previously unconnected output pin."""
    out = []
    for j in (0, 3):
        out += [(f"j{j}.{kind}", "f", f"linumert.j{j}.{kind}", None)
                for kind in ("pos-cmd", "pos-fb")]
        out += [(f"j{j}.{kind}", typ, f"trace.j{j}.{kind}", f"joint.{j}.{kind}")
                for kind, typ in (("f-error", "f"), ("f-error-lim", "f"), ("f-errored", "b"))]
        out += [(f"j{j}.drive-enabled", "b", f"trace.j{j}.drive-enabled",
                 f"lrt-cia402.{j}.enabled"),
                (f"j{j}.sw", "u", f"lrt.j{j}.sw", None),
                (f"j{j}.drive-ferror", "f", f"trace.j{j}.drive-ferror",
                 f"lrt-net.0.axis.{j}.ferror")]
    out += [(kind, "u", f"trace.{kind}", f"lrt-net.0.{kind}")
            for kind in ("sent", "received", "missed", "reply-age")]
    out.append(("connected", "b", "lrt.connected", None))
    return out


def prepare(ini: Path) -> None:
    """Append the sampler after every existing HALFILE; leave control nets intact."""
    pins = channels()
    if len(pins) > 21:  # LinuxCNC 2.9 HAL_STREAM_MAX_PINS
        raise ValueError("sampler supports at most 21 channels")
    lines = ["# Model-Author: Codex. Diagnostic inputs only; end of servo-thread.",
             f"loadrt sampler depth=65536 cfg={''.join(c[1] for c in pins)}"]
    for i, (_, _, signal, source) in enumerate(pins):
        lines.append(f"net {signal} " + (f"{source} " if source else "")
                     + f"=> sampler.0.pin.{i}")
    lines.append("addf sampler.0 servo-thread")
    (ini.parent / "servo_trace.hal").write_text("\n".join(lines) + "\n", encoding="utf-8")
    text = ini.read_text(encoding="utf-8").splitlines()
    last = max(i for i, line in enumerate(text) if line.strip().startswith("HALFILE ="))
    text.insert(last + 1, "HALFILE = servo_trace.hal")
    ini.write_text("\n".join(text) + "\n", encoding="utf-8")


def inspect_trace(path: Path) -> dict:
    """Reject missing rows, malformed columns, sampler overruns and sample-number gaps."""
    count, previous, gaps, malformed, overruns = 0, None, 0, 0, 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "overrun":
            overruns += 1
            continue
        words = line.split()
        try:
            if len(words) != len(channels()) + 1:
                raise ValueError("columns")
            number = int(words[0])
            for value in words[1:]:
                if not math.isfinite(float(value)):
                    raise ValueError("non-finite sample")
        except ValueError:
            malformed += 1
            continue
        if previous is not None and number != previous + 1:
            gaps += 1
        previous = number
        count += 1
    return {"samples": count, "gaps": gaps, "malformed": malformed, "overrun_markers": overruns,
            "continuous": count > 0 and not (gaps or malformed or overruns)}


class Recorder:
    def __init__(self, root: Path, ini: Path, work: Path, rip):
        self.root, self.ini, self.work, self.rip = root, ini, work, rip
        self.process = None
        self.output = self.errors = None
        prepare(ini)

    def start(self) -> None:
        self.output = (self.work / "servo_trace.txt").open("w", encoding="utf-8")
        self.errors = (self.work / "servo_trace.stderr").open("w", encoding="utf-8")
        cmd = f"source {shlex.quote(str(self.root / 'scripts/rip-environment'))} >/dev/null && "
        try:
            self.process = subprocess.Popen(["bash", "-c", cmd + "exec halsampler -t -c 0"],
                                            stdout=self.output, stderr=self.errors)
        except BaseException:
            self.output.close()
            self.errors.close()
            raise

    def stop(self) -> None:
        if self.process is None:
            return
        status = {"columns": ["sample", *[c[0] for c in channels()]],
                  "phase": "end of servo-thread; values retain producer update order"}
        try:
            disable = self.rip.rip_run(self.root, "halcmd setp sampler.0.enable false",
                                       self.ini.parent)
            status["disable_ok"] = disable.returncode == 0
            for _ in range(20):
                depth = self.rip.rip_run(self.root, "halcmd getp sampler.0.curr-depth",
                                         self.ini.parent)
                if depth.returncode or depth.stdout.strip() == "0":
                    break
                time.sleep(0.05)
            over = self.rip.rip_run(self.root, "halcmd getp sampler.0.overruns", self.ini.parent)
            status.update(remaining=depth.stdout.strip(), overruns=over.stdout.strip(),
                          counters_ok=depth.returncode == over.returncode == 0)
        finally:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
                status["forced_kill"] = True
            self.output.close()
            self.errors.close()
            status.update(inspect_trace(self.work / "servo_trace.txt"))
            status["collector_returncode"] = self.process.returncode
            status["valid"] = (status["continuous"] and status.get("disable_ok", False)
                               and status.get("counters_ok", False)
                               and status.get("remaining") == status.get("overruns") == "0"
                               and self.process.returncode == 0 and not status.get("forced_kill"))
            (self.work / "servo_trace.json").write_text(json.dumps(status, indent=2) + "\n",
                                                       encoding="utf-8")
