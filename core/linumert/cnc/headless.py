"""Read-only LinuxCNC DISPLAY process; never enables motion or resets E-STOP.

SPDX-License-Identifier: GPL-2.0-or-later
Model-Author: Codex
"""

import argparse
import configparser
import signal
import sys
import threading


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-ini", "--ini", required=True)
    args = parser.parse_args(argv)
    try:
        config = configparser.ConfigParser(interpolation=None, strict=False)
        with open(args.ini, encoding="utf-8") as stream:
            config.read_file(stream)
        if config.get("LINUMERT", "MACHINE_PROFILE", fallback="") not in ("sim", "plant"):
            raise ValueError("lite DISPLAY obsługuje wyłącznie sim/plant")
        import linuxcnc

        state = linuxcnc.stat()
        stop = threading.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
        while not stop.wait(0.1):
            state.poll()
    except (ImportError, OSError, ValueError, configparser.Error) as exc:
        print(f"linumert-headless: {exc}", file=sys.stderr)
        return 2
    return 0
