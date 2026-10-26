"""Uruchomienie bramy: ``python -m linumert_webhmi --fake`` albo ``--linuxcnc``.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Claude
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys

from linumert.cnc import FakeMachine, Mode

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
    args = parser.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        print("Odmowa: adres inny niż loopback wymaga --allow-remote.", file=sys.stderr)
        return 2
    try:
        import uvicorn
    except ImportError:
        print("Brak uvicorn: pip install 'linumert[panel]'", file=sys.stderr)
        return 2
    token = args.token or secrets.token_urlsafe(24)
    backend = FakeBackend(_demo_machine()) if args.fake else LinuxCNCBackend()
    gateway = Gateway(backend)
    gateway.start()
    extra = (args.host,) if args.allow_remote else ()
    app = create_app(gateway, token, extra_hosts=extra)
    print(f"web-hmi: http://{args.host}:{args.port}/  token: {token}")
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        gateway.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
