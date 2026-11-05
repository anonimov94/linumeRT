"""Uruchomienie bramy: ``python -m linumert_webhmi --fake`` albo ``--linuxcnc``.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

from linumert.cnc import FakeMachine, Mode
from linumert.machine.schema import MachineConfigError
from linumert.programs.prepare import JobService

from .app import create_app
from .backend import FakeBackend, LinuxCNCBackend
from .gateway import Gateway

DEFAULT_PORT = 8765


def _demo_machine() -> FakeMachine:
    machine = FakeMachine(rapid_speed=200.0)
    machine.estop_reset()
    machine.power_on()
    machine.home()
    machine.run_until_idle()
    machine.set_mode(Mode.MANUAL)
    return machine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linumert-webhmi", description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fake", action="store_true", help="atrapa maszyny (bez LinuxCNC)")
    source.add_argument("--linuxcnc", action="store_true", help="działający LinuxCNC (RIP)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--token", default=os.environ.get("LINUMERT_WEBHMI_TOKEN"))
    parser.add_argument("--allow-remote", action="store_true",
                        help="pozwól na adres inny niż loopback (tylko zaufana sieć)")
    parser.add_argument("--programs", type=Path, default=None,
                        help="katalog programów (domyślnie [DISPLAY]PROGRAM_PREFIX z INI)")
    parser.add_argument("--hal", action="store_true",
                        help="piny HAL linumert.hmi-* (grzyb, sygnał życia, potwierdzenie E-STOP)")
    parser.add_argument("--job-sources", type=Path, help="katalog źródeł .lnx do przygotowania")
    parser.add_argument("--job-machine", type=Path, help="aktywne machine.yaml do przygotowania")
    parser.add_argument("--job-tools", type=Path, help="istniejąca baza narzędzi SQLite")
    parser.add_argument("--jobs-dir", type=Path, help="katalog nowych pakietów zadań")
    parser.add_argument("--drive-library", type=Path, help="biblioteka szablonów napędów")
    parser.add_argument("--postgui", type=Path, default=None,
                        help="plik HAL wykonany po utworzeniu pinów (np. "
                             "config/hal/linumert_webhmi_postgui.hal); wymaga --hal")
    args = parser.parse_args(argv)
    options = (args.job_sources, args.job_machine, args.job_tools, args.jobs_dir)
    if (any(options) and not all(options)) or (args.drive_library and not all(options)):
        print("Odmowa: podaj razem --job-sources, --job-machine, --job-tools i --jobs-dir.",
              file=sys.stderr)
        return 2
    jobs = None
    if all(options):
        try:
            jobs = JobService(*options, library_dir=args.drive_library)
            jobs.context()
        except (OSError, ValueError, MachineConfigError) as error:
            print(f"Odmowa konfiguracji zadań: {error}", file=sys.stderr)
            return 2
    if args.postgui and not args.hal:
        print("Odmowa: --postgui wymaga --hal.", file=sys.stderr)
        return 2
    if args.hal and args.fake:
        print("Odmowa: --hal tylko z --linuxcnc.", file=sys.stderr)
        return 2
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        print("Odmowa: adres inny niż loopback wymaga --allow-remote.", file=sys.stderr)
        return 2
    try:
        import uvicorn
    except ImportError:
        print("Brak uvicorn: pip install 'linumert[panel]'", file=sys.stderr)
        return 2
    token = args.token or secrets.token_urlsafe(24)
    backend = (FakeBackend(_demo_machine(), programs_dir=args.programs) if args.fake
               else LinuxCNCBackend(programs_dir=args.programs))
    pins = None
    if args.hal:
        from .hal_link import open_hal

        pins, _component = open_hal(time.monotonic())  # komponent żyje do końca procesu
        if args.postgui:
            done = subprocess.run(["halcmd", "-f", str(args.postgui)], check=False)
            if done.returncode:
                print(f"Odmowa: halcmd -f {args.postgui} zakończył się kodem "
                      f"{done.returncode}", file=sys.stderr)
                return 2
    gateway = Gateway(backend, hal_pins=pins)
    gateway.start()
    extra = (args.host,) if args.allow_remote else ()
    app = create_app(gateway, token, extra_hosts=extra, jobs=jobs)
    print(f"web-hmi: http://{args.host}:{args.port}/  token: {token}")
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning",
                    ws_max_size=8192)
    finally:
        gateway.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
