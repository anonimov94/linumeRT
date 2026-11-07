"""Private LinuxCNC workspace for a verified job; never enables motion.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from linumert.machine.configgen import joint_drives
from linumert.machine.schema import MachineConfig
from linumert.programs import job, job_binding, job_execution

from .job_run import RunLog

FORMAT = "linumert.job.instance"
POSTGUI = """# WebHMI D35; Model-Author: Codex. No reset or enable command.
net linumert.hmi.button linumert.hmi-estop-ok => lrt_hmi_ok.in-00
net linumert.hmi.heartbeat linumert.hmi-heartbeat => watchdog.input-0
net linumert.hmi.wd-enable linumert.hmi-wd-enable => watchdog.enable-in
net linumert.hmi.ack linumert.hmi-ack => lrt_ack_edge.in
"""
PENDING = "Kontrola zgodności żywej instancji z zadaniem oczekuje. Start zadania zablokowany."


def _display(port, token):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Nieprawidłowy port WebHMI")
    if (not isinstance(token, str) or len(token) < 16
            or not all(c.isascii() and (c.isalnum() or c in "_-") for c in token)):
        raise ValueError("Token instancji: co najmniej 16 znaków ASCII, cyfr, _ lub -")
    return ("DISPLAY = linumert-webhmi --linuxcnc --hal --postgui instance_postgui.hal "
            f"--instance ../instance.json --port {port} --token={token}")


def prepare(source: Path, out: Path, *, port=8765, token=None) -> dict:
    """Exclusive private copy. Original evidence is never used as mutable CNC files."""
    source, out = source.resolve(), out.absolute()
    token = token or secrets.token_urlsafe(24)
    display_command = _display(port, token)
    if out.resolve().is_relative_to(source):
        raise ValueError("Instancję zapisz poza niezmienną konfiguracją zadania")
    manifest, files = job_execution.read(source)
    if manifest["test_mode"]:
        raise ValueError("Instancja WebHMI wymaga konfiguracji bez testowego bypassu HMI")
    out.mkdir(mode=0o700, parents=True, exist_ok=False)
    # No recursive cleanup on failure: leave any partial workspace for inspection.
    evidence, config = out / "evidence", out / "config"
    job_execution.publish({**files, "execution.json": job.json_text(manifest)}, evidence)
    config.mkdir(mode=0o700)
    for name, text in files.items():
        path = config / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    ini = config / manifest["ini"]
    text = ini.read_text(encoding="utf-8")
    display = "DISPLAY = linumert-headless"
    if text.count(display + "\n") != 1:
        raise ValueError("Nieznany DISPLAY konfiguracji zadania")
    text = text.replace(display + "\n", display_command + "\n", 1)
    ini.write_text(text, encoding="utf-8", newline="\n")
    (config / "instance_postgui.hal").write_text(POSTGUI, encoding="utf-8", newline="\n")
    (out / "home").mkdir(mode=0o700)
    record = {"format": FORMAT, "version": 1, "execution_id": manifest["execution_id"],
              "job_id": manifest["job_id"], "verification_id": manifest["verification_id"],
              "target": manifest["target"], "ini": manifest["ini"], "port": port, "token": token,
              "config_hashes": {p.relative_to(config).as_posix(): job.digest(p.read_bytes())
                                for p in sorted(config.rglob("*")) if p.is_file()}}
    (out / "instance.json").write_text(job.json_text(record), encoding="utf-8", newline="\n")
    return record


class Instance:
    """Bound identity and Start/resume conditions; Gateway owns command dispatch."""

    def __init__(self, path: Path, ini: Path, *, clock=time.monotonic):
        self.clock = clock
        self.run = None
        self._snapshot = None
        self._live = {}
        self._files_checked_at = None
        self.path = path.resolve()
        self.root = self.path.parent
        self.record = json.loads(self.path.read_text(encoding="utf-8"))
        record = self.record
        if record.get("format") != FORMAT or record.get("version") != 1:
            raise ValueError("Nieprawidłowy manifest instancji")
        original, files = job_execution.read(self.root / "evidence")
        self._files = files
        self._checks = {}
        self._evidence = {**files, "execution.json": job.json_text(original)}
        config_model = MachineConfig.model_validate_json(files["machine.yaml"])
        self._limits = {a.letter: list(a.soft_limits) for a in config_model.axes}
        self.hal_expectations = {"linumert.hmi.estop-ok": True, "lrt_hmi_bypass.in1": False,
                                 "motion.motion-enabled": True}
        for index, (_, name) in enumerate(joint_drives(config_model)):
            self.hal_expectations[f"joint.{index}.amp-enable-out"] = True
            if original["target"] == "plant":
                self.hal_expectations[f"lrt-cia402.{index}.enabled"] = True
                self.hal_expectations[f"lrt-net.0.axis.{index}.scale"] = float(
                    f"{original['joint_scales'][name]:.6f}")
            else:
                self.hal_expectations[f"sim_j{index}.gain"] = 1.0
        if original["target"] == "plant":
            self.hal_expectations.update({"lrt-net.0.connected": True,
                                          "lrt-net.0.plant-lost": False})
        if any(record.get(k) != original[k] for k in
               ("execution_id", "job_id", "verification_id", "target", "ini")):
            raise ValueError("Instancja nie odpowiada niezmiennej konfiguracji zadania")
        if original["test_mode"] or ini.resolve() != self.root / "config" / original["ini"]:
            raise ValueError("Obca konfiguracja LinuxCNC lub bypass HMI")
        config = self.root / "config"
        expected = {**files, "instance_postgui.hal": POSTGUI}
        expected[original["ini"]] = files[original["ini"]].replace(
            "DISPLAY = linumert-headless\n", _display(record["port"], record["token"]) + "\n", 1)
        self._expected_config = expected
        if record["config_hashes"] != {name: job.digest(text.encode())
                                       for name, text in expected.items()}:
            raise ValueError("Konfiguracja robocza nie odpowiada pakietowi zadania")
        for name, digest in record["config_hashes"].items():
            relative = job_execution._relative(name)
            if any((config / Path(*relative.parts[:i])).is_symlink()
                   for i in range(1, len(relative.parts) + 1)):
                raise ValueError("Dowiązanie w konfiguracji instancji")
            data = (config / name).read_bytes()
            # LinuxCNC rewrites the private parameter file before DISPLAY starts.
            # Its frozen initial bytes remain in evidence; live offsets/G92 must
            # be checked separately before any future Start authorization.
            if name != "linumert.var" and job.digest(data) != digest:
                raise ValueError(f"Zmieniona konfiguracja instancji: {name}")

    def observe(self, snapshot, live, *, hmi=False, alarms=()):
        self._snapshot, self._live = snapshot, live or {}
        self._checks = job_binding.inspect(snapshot, live,
            ini=self.root / "config" / self.record["ini"],
            program=self.root / "config/nc_files/program.ngc", table=self._files["tool.tbl"],
            setup=json.loads(self._files["job/setup.json"]),
            start=json.loads(self._files["verification.json"])["assumptions"]["start_mm"])
        live = live or {}
        hal = live.get("hal")
        matched = isinstance(hal, dict) and all(
            (type(hal.get(pin)) in (bool, int) and hal[pin] == wanted) if type(wanted) is bool
            else (isinstance(hal.get(pin), (int, float)) and not isinstance(hal[pin], bool)
                  and math.isfinite(hal[pin]) and abs(hal[pin] - wanted) <= 1e-6)
            for pin, wanted in self.hal_expectations.items())
        self._checks["hal"] = {"status": "unavailable" if hal is None else
                               "passed" if matched else "failed",
            "reason": "Wymagane gotowe napędy i łańcuch HMI/HAL oraz zgodne skale"}
        limits = set(snapshot.axis_names) == set(self._limits) and all(
            abs(a.soft_min - self._limits[a.name][0]) <= 1e-6
            and abs(a.soft_max - self._limits[a.name][1]) <= 1e-6 for a in snapshot.axes)
        self._checks["limits"] = {"status": "passed" if limits else "failed",
                                  "reason": "Limity sterowania zgodne z maszyną zadania"}
        self._checks["freshness"] = {"status": "passed" if snapshot.is_fresh(self.clock())
                                     else "failed", "reason": "Aktualny odczyt sterowania"}
        self._checks["hmi"] = {"status": "passed" if hmi and live.get("hmi_alive") is True
                              else "failed", "reason": "Wymagane żywe połączenie WebHMI i HAL"}
        self._checks["alarms"] = {"status": "failed" if alarms else "passed",
                                 "reason": "Brak aktywnych alarmów"}
        if self.run and self.run.active:
            self.run.sample(snapshot, self._live, alarms)

    def validate_files(self):
        """Compare approved bytes again before Start; no recompilation in the poll loop."""
        roots = (("evidence", self._evidence), ("config", self._expected_config))
        for directory, expected in roots:
            root = self.root / directory
            for name, text in expected.items():
                if directory == "config" and name == "linumert.var":
                    continue  # current offsets must pass the separate NML comparison
                parts = job_execution._relative(name).parts
                if root.is_symlink() or any((root / Path(*parts[:i])).is_symlink()
                                           for i in range(1, len(parts) + 1)):
                    raise ValueError("Zmieniona ścieżka pliku zadania")
                if (root / name).read_bytes() != text.encode():
                    raise ValueError(f"Zmieniony plik zadania: {directory}/{name}")
        if self.path.is_symlink() or self.path.read_bytes() != job.json_text(self.record).encode():
            raise ValueError("Zmieniony manifest instancji")
        self._files_checked_at = self.clock()

    def can_start(self):
        return (not (self.run and (self.run.active or self.run.needs_abort)) and bool(self._checks)
                and all(c["status"] == "passed" for c in self._checks.values()))

    def can_resume(self):
        if not self.run or self.run.phase != "paused" or self.run.resume_requested:
            return False
        snap, live = self._snapshot, self._live
        excluded = {"machine_ready", "start_position", "initial_tool"}
        return (not self.run.stop_requested and self.run.pause_context is not None
                and all(v["status"] == "passed" for k, v in self._checks.items()
                        if k not in excluded)
                and snap.task_state.value == "on" and snap.mode.value == "auto"
                and snap.interp_state.value == "paused" and snap.all_homed
                and live.get("inpos") is True
                and isinstance(live.get("current_vel"), (int, float))
                and abs(live["current_vel"]) < 1e-4
                and job_binding.same_context(self.run.pause_context, self.run.context(snap, live))
                and all(abs(a.following_error) < .001 for a in snap.axes))

    def begin(self, from_line):
        if from_line != 1:
            raise ValueError("Zadanie wymaga Start od pierwszej linii")
        if (self._files_checked_at is None or self.clock() - self._files_checked_at > .5
                or not self.can_start()):
            reasons = [v["reason"] for v in self._checks.values() if v["status"] != "passed"]
            raise ValueError("Start zablokowany: " + (reasons[0] if reasons else "brak gotowości"))
        self.run = RunLog(self.root, self.record, clock=self.clock)
        self._files_checked_at = None
        self.run.sample(self._snapshot, self._live, ())

    def command(self, name):
        if self.run and self.run.active:
            self.run.command(name)

    def fail(self, phase="fault"):
        if self.run and self.run.active:
            self.run.finish(phase)

    def status(self):
        ready, resume = self.can_start(), self.can_resume()
        reasons = [v["reason"] for v in self._checks.values() if v["status"] != "passed"]
        reason = ("Gotowe do Start zadania" if ready else
                  "Start zablokowany: " + (reasons[0] if reasons else PENDING))
        if self.run and self.run.active:
            reason = "Zadanie w toku; kolejny Start zablokowany."
        resume_reason = "Brak niezmienionego, ustalonego stanu wstrzymanego zadania"
        return {**{k: self.record[k] for k in ("execution_id", "job_id", "target")},
                "status": "instance_loaded", "can_start": ready, "can_resume": resume,
                "reason": reason, "resume_reason": resume_reason,
                "execution_authorization": False, "checks": self._checks,
                "run": self.run.status() if self.run else None}


def _stop(proc):
    """Let LinuxCNC's parent perform its shutdown; force only our own group."""
    if proc.poll() is None:
        try:
            proc.terminate()
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def _signal_owned(work: Path, sig, *, display_only=False):
    """Signal only inherited per-instance markers; pidfds prevent PID reuse races."""
    marker = os.fsencode(f"LINUMERT_JOB_WORKSPACE={work}")
    count = 0
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            if path.stat().st_uid != os.getuid():
                continue
            fd = os.pidfd_open(int(path.name))
        except (ProcessLookupError, FileNotFoundError, PermissionError):
            continue
        try:
            if marker not in (path / "environ").read_bytes().split(b"\0"):
                continue
            argv = (path / "cmdline").read_bytes().split(b"\0")
            if display_only and not any(Path(os.fsdecode(v)).name == "linumert-webhmi"
                                        for v in argv[:2]):
                continue
            signal.pidfd_send_signal(fd, sig)
            count += 1
        except (ProcessLookupError, FileNotFoundError, PermissionError):
            pass
        finally:
            os.close(fd)
    return count


def _check_port(port, kind):
    with socket.socket(socket.AF_INET, kind) as probe:
        if kind == socket.SOCK_STREAM:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("127.0.0.1", port))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="nowy prywatny katalog instancji")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default=os.environ.get("LINUMERT_WEBHMI_TOKEN"))
    args = parser.parse_args(argv)
    children, streams = [], []
    previous_term = None
    home_alias = None
    work = None
    try:
        if sys.platform != "linux":
            raise ValueError("Instancja LinuxCNC wymaga Linuksa")
        for command in ("linuxcnc", "halcmd", "linumert-webhmi"):
            if shutil.which(command) is None:
                raise ValueError(f"Brak programu w PATH: {command}")
        # LinuxCNC owns a global controller resource. Never stop an existing instance.
        found = subprocess.run(["pgrep", "-u", str(os.getuid()), "-x",
                                "linuxcnc|linuxcncsvr|milltask|io|iov2|halui|rtapi_app"],
                               capture_output=True, text=True, check=False)
        if found.returncode != 1 or Path("/tmp/linuxcnc.lock").exists():
            raise ValueError("LinuxCNC jest już aktywny lub pozostała jego blokada")
        manifest, _ = job_execution.read(args.configuration)
        plant = manifest["launch"]["plant"]
        for port, kind in [(args.port, socket.SOCK_STREAM), *(
                [(int(plant[-1]), socket.SOCK_DGRAM)] if plant else [])]:
            _check_port(port, kind)
        record = prepare(args.configuration, args.out, port=args.port, token=args.token)
        work = args.out.resolve()
        config = work / "config"
        # rtapi_app uses HOME in an AF_UNIX path (maximum108 bytes on Linux).
        # Keep the persistent private HOME, address it through a short owned alias.
        home_alias = tempfile.TemporaryDirectory(prefix="lrt-home-")
        short_home = Path(home_alias.name) / "h"
        short_home.symlink_to(work / "home", target_is_directory=True)
        env = {**os.environ, "HOME": str(short_home), "LINUMERT_JOB_WORKSPACE": str(work)}
        manifest, _ = job_execution.read(work / "evidence")
        plant = manifest["launch"]["plant"]
        def terminate(_signal, _frame):
            raise KeyboardInterrupt

        previous_term = signal.signal(signal.SIGTERM, terminate)
        commands = ([sys.executable, "-m", "linumert_plant", *plant[1:]],) if plant else ()
        commands += (["linuxcnc", "-r", str(config / record["ini"])],)
        for index, command in enumerate(commands):
            stream = (work / f"process-{index}.log").open("w", encoding="utf-8")
            streams.append(stream)
            children.append(subprocess.Popen(command, cwd=config, env=env, stdout=stream,
                                             stderr=subprocess.STDOUT, start_new_session=True))
        print(f"WebHMI: http://127.0.0.1:{args.port}/ · instancja {work}", flush=True)
        print(f"token: {record['token']}", flush=True)
        print("Brak automatycznego Reset/ON/bazowania. Start wymaga zgodnych kontroli i operatora.",
              flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(0.1)
        return next((p.returncode for p in children if p.returncode), 0)
    except (OSError, ValueError) as error:
        print(f"Odmowa instancji: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    finally:
        # bash waits for DISPLAY before running its Cleanup trap. Close that
        # owned process first, so LinuxCNC can stop its detached NML/RT daemons.
        if work is not None:
            _signal_owned(work, signal.SIGTERM, display_only=True)
        for proc in reversed(children):
            _stop(proc)
        if work is not None:
            deadline = time.monotonic() + 2
            while _signal_owned(work, signal.SIGTERM) and time.monotonic() < deadline:
                time.sleep(.05)
            for _ in range(20):
                if not _signal_owned(work, signal.SIGKILL):
                    break
                time.sleep(.05)
        for stream in streams:
            stream.close()
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
        if home_alias is not None:
            home_alias.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
