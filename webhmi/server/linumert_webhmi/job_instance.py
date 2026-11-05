"""Private LinuxCNC workspace for a verified job; never enables motion.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from linumert.programs import job, job_execution

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
            f"--instance ../instance.json --port {port} --token {token}")


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
    """Read-only identity shown by the operator screen. Live Start gate remains closed."""

    def __init__(self, path: Path, ini: Path):
        self.path = path.resolve()
        self.root = self.path.parent
        self.record = json.loads(self.path.read_text(encoding="utf-8"))
        record = self.record
        if record.get("format") != FORMAT or record.get("version") != 1:
            raise ValueError("Nieprawidłowy manifest instancji")
        original, files = job_execution.read(self.root / "evidence")
        if any(record.get(k) != original[k] for k in
               ("execution_id", "job_id", "verification_id", "target", "ini")):
            raise ValueError("Instancja nie odpowiada niezmiennej konfiguracji zadania")
        if original["test_mode"] or ini.resolve() != self.root / "config" / original["ini"]:
            raise ValueError("Obca konfiguracja LinuxCNC lub bypass HMI")
        config = self.root / "config"
        expected = {**files, "instance_postgui.hal": POSTGUI}
        expected[original["ini"]] = files[original["ini"]].replace(
            "DISPLAY = linumert-headless\n", _display(record["port"], record["token"]) + "\n", 1)
        if record["config_hashes"] != {name: job.digest(text.encode())
                                       for name, text in expected.items()}:
            raise ValueError("Konfiguracja robocza nie odpowiada pakietowi zadania")
        for name, digest in record["config_hashes"].items():
            relative = job_execution._relative(name)
            if any((config / Path(*relative.parts[:i])).is_symlink()
                   for i in range(1, len(relative.parts) + 1)):
                raise ValueError("Dowiązanie w konfiguracji instancji")
            if job.digest((config / name).read_bytes()) != digest:
                raise ValueError(f"Zmieniona konfiguracja instancji: {name}")

    def status(self):
        return {**{k: self.record[k] for k in ("execution_id", "job_id", "target")},
                "status": "instance_loaded", "can_start": False, "reason": PENDING,
                "execution_authorization": False}


def _stop(proc):
    """Only the process group created here; no global LinuxCNC cleanup."""
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="nowy prywatny katalog instancji")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    children, streams = [], []
    previous_term = None
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
            with socket.socket(socket.AF_INET, kind) as probe:
                probe.bind(("127.0.0.1", port))
        record = prepare(args.configuration, args.out, port=args.port)
        work = args.out.resolve()
        config = work / "config"
        env = {**os.environ, "HOME": str(work / "home")}
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
        print("Brak automatycznego Reset/ON/bazowania. Start zadania pozostaje zablokowany.",
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
        for proc in reversed(children):
            _stop(proc)
        for stream in streams:
            stream.close()
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)


if __name__ == "__main__":
    raise SystemExit(main())
